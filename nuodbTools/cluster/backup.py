'''
Created on Feb 7, 2014

@author: rkourtz
'''
# requests module available at http://docs.python-requests.org/en/latest/
import base64
import boto.ec2
import nuodbTools.aws
import nuodbTools.cluster
import nuodbTools.physical
import inspect, json, random, time
import os.path
import re
import socket
import sys
import tempfile
import uuid
import zlib

class Backup():
  def __init__(self, 
               database = None, host = None, 
               aws_access_key = None, aws_secret = None, aws_region = None, 
               domainConnection = None, ec2Connection = None, 
               rest_username=None, rest_password=None, rest_url=None, 
               ssh_username=None, ssh_keyfile=None, 
               tarball_destination = None, backup_type = None):
    args, _, _, values = inspect.getargvalues(inspect.currentframe())
    for i in args:
      setattr(self, i, values[i])
      
    if backup_type == None:
      raise nuodbTools.Error("You must specify a --backup-type: ebs, zfs, tarball.")
    if backup_type == "tarball" and tarball_destination == None:
      raise nuodbTools.Error("Tarball nuodb_backup must have a destination")
    if not hasattr(self, 'domainConnection') or self.domainConnection == None:
      self.domainConnection = nuodbTools.cluster.Domain(rest_url=rest_url, rest_username=rest_username, rest_password=rest_password)
    if backup_type == "tarball" or tarball_destination != None:
      self.tarball_destination = tarball_destination
    if self.ec2Connection == None and backup_type.lower() == "ebs":
      if aws_region == None or aws_access_key == None or aws_secret == None:
        raise nuodbTools.Error("aws_region, aws_access_key & aws_secret parameters must be defined for AWS")
      self.ec2Connection = boto.ec2.connect_to_region(aws_region, aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret)
    self.db = nuodbTools.cluster.Database(name=self.database, domain = self.domainConnection)
    
  def backup(self, comment = None):
    # Helper functions
    def __find_common_root_dir(dir1, dir2):
      common = []
      d1 = dir1.split("/")
      d2 = dir2.split("/")
      d1l = len(d1)
      d2l = len(d2)
      if d1l > d2l:
        c = d2l
      elif d2l > d1l:
        c = d1l
      else:
        c = d1l
      i=0
      while i < c:
        if d1[i] == d2[i]:
          common.append(d1[i])
        i += 1
      if len(common) == 1:
        return "/"
      else:
        return "/".join(common)
    if self.database not in self.domainConnection.get_databases():
      raise nuodbTools.Error("Can not find database %s in domain provided" % self.database)
    sm_processes = self.db.get_processes(type="SM")
    if self.host != None:
      exists = False
      for process in sm_processes:
        if process['hostname'] == self.host:
          exists = True
          mysm = process
      if not exists:
        print "Unable to find a running Storage Manager on host %s" % self.host
        print "Cannot continue."
        exit(2)
    else:
      sm_count = len(sm_processes)
      mysm = sm_processes[random.randrange(0, sm_count)]
    uid = mysm['uid']
    hostname = mysm['hostname']
    print "Working on %s..." % hostname
    print self.ec2Connection
    if self.ec2Connection != None:
      self.backuphost = nuodbTools.aws.Host(ec2Connection = self.ec2Connection, name = mysm['hostname'], ssh_user = self.ssh_username, ssh_keyfile = self.ssh_keyfile)
    else:
      self.backuphost = nuodbTools.physical.Host(name = mysm['hostname'], ssh_user = self.ssh_username, ssh_keyfile = self.ssh_keyfile)
    print "Figure out what volume(s) to back up..."
    process_detail = self.domainConnection.rest_req(path="/".join(["processes",uid,"query"]))
    archive = {"dir": process_detail['configuration']['configuration']['archive'], "type": "archive"}
    checklink = self.backuphost.get_directory_target(archive['dir'])
    if checklink != archive['dir']:
      archive['dir'] = checklink
    # Journal directory is an optional parameter
    if "journal-dir" in process_detail['configuration']['configuration']:
      journal = {"dir": process_detail['configuration']['configuration']['journal-dir'], "type": "journal"}
      checklink = self.backuphost.get_directory_target(journal['dir'])
      if checklink != journal['dir']:
        journal['dir'] = checklink
    else:
      journal = {"dir": archive['dir'], "type": "journal"}
    archive['mount'] = None
    for mount in self.backuphost.volume_mounts:
      root_dir = __find_common_root_dir(mount, archive['dir'])
      if archive['mount'] == None or len(root_dir) > len(archive['mount']):
        archive['mount'] = root_dir
    journal['mount'] = None
    for mount in self.backuphost.volume_mounts:
      root_dir = __find_common_root_dir(mount, journal['dir'])
      if journal['mount'] == None or len(root_dir) > len(journal['mount']):
        journal['mount'] = root_dir
    if archive['mount'] == None or journal['mount'] == None:
      raise nuodbTools.Error("Can't determine mount points for %s and %s" % (archive['dir'], journal['dir']))
    archive['volume'] = self.backuphost.volume_mounts[archive['mount']]
    journal['volume'] = self.backuphost.volume_mounts[journal['mount']]
    print "Archive on %s of type %s" % (archive['mount'], archive['volume']['type'])
    print "Journal on %s of type %s" % (journal['mount'], journal['volume']['type'])
    # We have 2 kinds of backups, online and offline.
    # Online can be done when the mounts are the same and the mount supports file system snapshotting
    notification = "Nada"
    if archive['mount'] == journal['mount']:
      print "Common nuodb_backup device is %s" % archive['mount']

      # AWS EBS supports snapshotting
      if "ebs_volume" in archive['volume'] and self.backup_type in ["ebs", "auto", None]:
        # This is an amazon EBS volume
        vol = archive
        vol['journal_dir'] = journal['dir']
        vol['backup_type'] = "full"
        name = self.__backup_ebs(
                                 vol = vol, 
                                 host = self.backuphost, 
                                 comment = comment
                                 )
        notification = "Created an EBS nuodb_backup of %s with snapshot id %s" % (self.database, name[1])
      # So does a zfs volume
      elif archive['volume']['type'] == "zfs" and self.backup_type in ["zfs", "auto", None]:
        backup = self.__backup_zfs(directory = archive['dir'], device = archive['volume']['dev'], host = self.backuphost)
        if backup[0]:
          notification =  backup[1]+ "\n"
        else:
          Error(backup[1])
      # Anything else we need offline nuodb_backup
      else:
        notification = self.__offline_backup(host = self.backuphost, storage_manager = mysm, archive = archive, journal = journal)
    else:
      notification = self.__offline_backup(host = self.backuphost, storage_manager = mysm, archive = archive, journal = journal)
    print notification
    print "Exiting..."
  
  def __offline_backup(self, host = None, storage_manager = None, archive = None, journal = None, comment = None):
    # If we are here we are going to take down the SM, take a nuodb_backup, and start the process
    print "No online nuodb_backup method available"
    if len(self.db.get_processes(type="SM")) < 2:
      print "Not enough storage managers to take nuodb_backup. Need 2, have %s " % len(self.db.get_processes(type="SM")) 
      print "Please start another and wait for it to synchronize"
      exit(1)
    else:
      print "Have enough storage managers to proceed." 
    print "Stop SM process..."
    self.stop_process(database = self.db, process_id = storage_manager['uid'])
    print "Take snapshot..."
    notification = ""
    timestamp = time.time()
    archive['backup_type'] = "archive"
    if journal != None:
      journal['backup_type'] = "journal"

    for dir in [archive, journal]:
      if dir != None and "volume" in dir:
        if "ebs_volume" in dir['volume'] and self.backup_type in ["ebs", "auto", None]:
          # This is an amazon EBS volume
          name = self.__backup_ebs(dir, host, timestamp = timestamp, comment = comment)
          notification += "Created an EBS nuodb_backup of %s:%s with snapshot id %s" % (self.database, dir['type'], name[1]) + "\n"
        elif "type" in dir['volume'] and dir['volume']['type'] == "zfs" and self.backup_type in ["zfs", "auto", None]:
          backup = self.__backup_zfs(dir, host, timestamp = timestamp, comment = comment)
          if backup[0]:
            notification +=  backup[1]+ "\n"
          else:
            raise nuodbTools.Error(backup[1])
        else:
          self.__backup_tarball(
                           archive = archive, journal = journal,
                           destination = self.tarball_destination,
                           host = host,
                           timestamp = timestamp
                           )
    print "Start SM..."
    if journal == None or journal['dir'] == None:
      journal_dir = None
    else:
      journal_dir = journal['dir']
    self.start_process(database = self.db, processtype = "SM", host = self.backuphost, archive_dir = archive['dir'], journal_dir = journal_dir)
    return notification
  
  def __backup_ebs(self, vol, host, timestamp = time.time(), comment = None):
    mount = vol['mount']
    backup_type = vol['backup_type']
    time_formatted = time.strftime("%d%b%Y %H:%M:%S GMT", time.gmtime(timestamp))
    print "Doing AWS EBS snapshot of %s" % vol['volume']['ebs_volume']
    dbname = ":".join([backup_type, self.database])
    if backup_type != "full":
      if backup_type == "journal":
        metadata = {"t": timestamp, "db": self.database, "b": backup_type, "m": mount, "jd": vol['dir']}
      else:
        metadata = {"t": timestamp, "db": self.database, "b": backup_type, "m": mount, "ad": vol['dir']}
    else:
      metadata = {"t": timestamp, "db": self.database, "b": backup_type, "m": mount, "ad": vol['dir'], "jd": vol['journal_dir']}
    name = "%s@%s" % (dbname, time_formatted)
    
    if comment == None:
      metadata['c'] = 0
      comment = "NuoDB backup of %s from %s" % (self.database, host.name)
    else:
      metadata['c'] = 1
    metadata_json = json.dumps(metadata)
    z = base64.b64encode(zlib.compress(metadata_json))
    if len(z) > 254:
      raise nuodbTools.Error("Metadata for a backup is limited to 255 characters compressed. Got %s after using zlib and base64: %s" % (len(z), metadata_json))
    snapshot = self.ec2Connection.create_snapshot(volume_id = vol['volume']['ebs_volume'], description = comment[0:254])
    snapshot.update()
    snapshot.add_tag("Name", name)
    snapshot.add_tag("NuoDB", z)
    return (True, snapshot.id)
    
  def __backup_zfs(self, vol, host, timestamp = time.time(), comment = None):
    print vol
    mount = vol['mount']
    backup_type = vol['backup_type']
    time_formatted = time.strftime("%d%b%Y %H:%M:%S GMT", time.gmtime(timestamp))
    dbname = ":".join([backup_type, self.database])
    if backup_type != "full":
      if backup_type == "journal":
        metadata = {"t": timestamp, "db": self.database, "b": backup_type, "m": mount, "jd": vol['dir']}
      else:
        metadata = {"t": timestamp, "db": self.database, "b": backup_type, "m": mount, "ad": vol['dir']}
    else:
      metadata = {"t": timestamp, "db": self.database, "b": backup_type, "m": mount, "ad": vol['dir'], "jd": vol['journal_dir']}
    name = "%s@%s" % (dbname, time_formatted)
    
    if comment == None:
      metadata['c'] = 0
      comment = "NuoDB backup of %s from %s" % (self.database, host.name)
    else:
      metadata['c'] = 1
    time_formatted = time.strftime("%d%b%Y %H:%M:%S GMT", time.gmtime(timestamp))
    metadata_json = json.dumps(metadata)
    # ZFS snapshots can only contain alphanumeric characters, space "-", "_", "." and ":". Sanitize the name
    z = base64.b64encode(zlib.compress(metadata_json)).__str__().replace("=", "_").replace("/", ".").replace("+", ":")
    description = "-".join(["nuo", z])
    command = "sudo zfs snapshot %s@%s" % (vol['volume']['dev'], description)
    rc, stdout, stderr = host.execute_command(command)
    if  rc != 0:
      returnmessage = "Command %s failed to execute: %s" % (command, stderr)
      return (False, returnmessage)
    return (True, host.execute_command("sudo zfs list -t snapshot")[1])
    
  def __backup_tarball(self, archive, journal, destination, host, timestamp = time.time(), comment = None):
    def sanitize(data):
      if data == None:
        return data
      else:
        return data.replace("_", "-").replace(" ", "_")
    if comment != None:
      filename = "NuoDB_backup_%s_%s.tgz" % (sanitize(self.database), sanitize(comment))
    else:
      filename = "NuoDB_backup_%s_%s.tgz" % (sanitize(self.database), str(int(timestamp)))
    metadata = {"t": timestamp, "db": self.database, "b": "full", "m": None, "ad": archive['dir'], "jd": journal['dir']}
    metadata_file = tempfile.NamedTemporaryFile(suffix=".metadata", delete=False)
    metadata_file.write(json.dumps(metadata))
    metadata_file.close()
    
    # Find out if there is enough space for the tarball
    command = """
              arch=`sudo du -s %s | awk '{print $1}'`;
              jrnl=`sudo du -s %s | awk '{print $1}'`;
              dest=`sudo df %s | awk '{print $4}' | tail -n 1`;
              src=$((arch+jrnl))
              if [ $src -gt $dest ];
              then
                echo "Insufficient space on destination drive. Have $dest available, need $src";
                exit 2;
              else 
                echo "Space check OK. Source: $src Dest: $dest";
              fi
              """ % (archive['dir'], journal['dir'], destination)
    r = host.execute_command(command)
    if r[0] != 0:
      raise nuodbTools.Error(r[2])
    host.copy(metadata_file.name, "/".join([destination, os.path.basename(metadata_file.name)]))
    command = "cd %s; sudo tar -czf %s %s %s %s" % (destination, "/".join([self.tarball_destination, filename]), os.path.basename(metadata_file.name), archive['dir'], journal['dir'])
    print command
    print host.execute_command(command)
    return (False, "", "Tarball nuodb_backup is yet to be implemented")
    
  def dump_data(self):
    return self.__dict__
  
  @property
  def backups(self):
    def reverse_numeric(x, y):
      return int(y - x)
    ret = []
    if self.ec2Connection != None:
      backups = {}
      l = self.ec2Connection.get_all_snapshots(owner = "self")
      for s in l:
        dict = s.__dict__
        if "tags" in dict and "NuoDB" in dict['tags'] and s.status == "completed":
          try:
            data = json.loads(zlib.decompress(base64.b64decode(dict['tags']['NuoDB'])))
            if data['db'] == self.database:
              t = data['t']
              if "c" in data and data['c'] == 1:
                c = " ".join([s.description, time.strftime("(%d%b%Y %H:%M:%S GMT)", time.gmtime(t))])
              else:
                c = " ".join([data['db'], time.strftime("(%d%b%Y %H:%M:%S GMT)", time.gmtime(t))])
              if t not in backups:
                backups[t] = {"c": c, "s":[s.id]}
              else:
                backups[t]["s"].append(s.id)
              backups[t]["d"] = data
          except Error, e:
            print e
      for t in sorted(backups.keys(), cmp=reverse_numeric):
        ret.append([backups[t]["c"], backups[t]["s"], "ebs", backups[t]["d"]])
    if self.tarball_destination != None:
      self.host_obj = nuodbTools.physical.Host(name = self.host, ssh_user = self.ssh_username, ssh_keyfile = self.ssh_keyfile)
      command = "ls -lrn %s/NuoDB_backup* | awk '{print $9}'" % self.tarball_destination
      r = self.host_obj.execute_command(command)
      if r[0] != 0:
        raise nuodbTools.Error("Can't find backups in %s: %s" % self.tarball_destination, r[2]) 
      else:
        files = r[1].split("\n")
        for f in files:
          if len(f.rstrip()) > 0:
            parts = f.rstrip().replace(".tgz", "").replace("-", " ").split("_")
            desc = parts[-1]
            if parts[2].replace(" ", "_") == self.database:
              try:
                desc = time.strftime("%d%b%Y %H:%M:%S GMT", time.gmtime(int(desc)))
              except:
                pass
              ret.append((desc, f.rstrip(), "tar"))
    self.host_obj = nuodbTools.physical.Host(name = self.host, ssh_user = self.ssh_username, ssh_keyfile = self.ssh_keyfile)
    if self.host_obj.execute_command("which zfs")[0] == 0:
      backups = {}
      # zfs is installed, see if we have any backups
      command = "sudo zfs list -t snapshot | awk '{print $1}' | grep nuo-"
      snapshots =  self.host_obj.execute_command(command)
      for snapshot in snapshots[1].split("\n"):
        if "nuo-" in snapshot:
          unpack = snapshot.split("nuo-")
          unpack[1] = unpack[1].rstrip().replace("_","=").replace(".","/").replace(":","+")
          data = json.loads(zlib.decompress(base64.b64decode(unpack[1])))
          if data['db'] == self.database:
            t = data['t']
            if "c" in data and data['c'] == 1:
              c = " ".join([s.description, time.strftime("(%d%b%Y %H:%M:%S GMT)", time.gmtime(t))])
            else:
              c = " ".join([data['db'], time.strftime("(%d%b%Y %H:%M:%S GMT)", time.gmtime(t))])
            if t not in backups:
                backups[t] = {"c": c, "s":[snapshot.rstrip()]}
            else:
              backups[t]["s"].append(snapshot.rstrip())
      for t in sorted(backups.keys(), cmp=reverse_numeric):
        ret.append([backups[t]["c"], backups[t]["s"], "zfs", data])
    return ret
  
  def restore_ebs(self, db_user = None, db_password = None, snapshots = []):
    hosts = self.domainConnection.get_hosts()
    journal_dir = None
    archive_dir = None
    mounts = []
    if db_user == None or db_password == None:
      raise nuodbTools.Error("You must specify db-user and db-password for the new database to restore it.")
    for host in hosts:
      if host['hostname'] == self.host:
        self.restorehost_id = host['id']
        if self.ec2Connection != None:
          self.restorehost = nuodbTools.aws.Host(ec2Connection = self.ec2Connection, name = self.host, ssh_user = self.ssh_username, ssh_keyfile = self.ssh_keyfile)
        else:
          raise nuodbTools.Error("A valid ec2 connection cannot be found.")
          #self.restorehost = nuodbTools.physical.Host(name = self.host, ssh_user = self.ssh_username, ssh_keyfile = self.ssh_keyfile)
    if not hasattr(self, "restorehost"):
      raise nuodbTools.Error("No member of the domain found at %s" % self.host)
    list = self.ec2Connection.get_all_snapshots(snapshot_ids = snapshots)
    dbname = ""
    for snapshot in list:
      if "tags" not in snapshot.__dict__ or not "NuoDB" in snapshot.__dict__['tags']:
        raise nuodbTools.Error("Can't find necessary NuoDB metadata from 'tags' of %s. Cannot continue." % snapshot.id)
      data = json.loads(zlib.decompress(base64.b64decode(snapshot.__dict__['tags']['NuoDB'])))
      mount_point = data['m'] + "_%s" % str(int(data['t']))
      dbname = data['db']+ "_%s" % str(int(data['t']))
      mounts.append({"mount": mount_point, "size": snapshot.volume_size, "snap": snapshot.id, "db": data['db'], "time": data['t']})
      if data['b'] == "full":
        journal_dir = re.sub(data['m'], mount_point, data['jd'])
        archive_dir = re.sub(data['m'], mount_point, data['ad'])
      elif data['b'] == "archive":
        archive_dir = re.sub(data['m'], mount_point, data['ad'])
      elif data['b'] == "journal":
        journal_dir = re.sub(data['m'], mount_point, data['jd'])
    self.restoredb = nuodbTools.cluster.Database(name=dbname, domain = self.domainConnection)
    if self.restoredb.exists:
      raise nuodbTools.Error("Database %s already exists in the domain. Cannot restore an already running database." % dbname)
    for mount in mounts:
      print "Mounting %s" % mount['mount']
      try:
        r = self.restorehost.attach_volume(size= mount['size'], mount_point = mount['mount'], snapshot = mount['snap'])
        if r[0] != True:
          raise nuodbTools.Error("Error trying to attach volume on %s from snapshot %s: %s" % (mount['mount'], mount['snap'], r[2]))
      except nuodbTools.cluster.backup.Error, e:
       print e
    
    print "Starting SM..."
    self.start_process(database = self.restoredb, processtype = "SM", host = self.restorehost, archive_dir = archive_dir, journal_dir = journal_dir)
    print "Starting TE..."
    self.start_process(database = self.restoredb, processtype = "TE", host = self.restorehost, user = db_user, password = db_password)
    print "Restored database to \"%s\" on %s" % (dbname, self.restorehost.name)
      
  def restore_tarball(self, db_user = None, db_password = None, tarball = None):
    hosts = self.domainConnection.get_hosts()
    if db_user == None or db_password == None:
      raise nuodbTools.Error("You must specify db-user and db-password for the new database to restore it.")
    for host in hosts:
      if host['hostname'] == self.host:
        self.restorehost_id = host['id']
        if socket.gethostname() != self.host and ( self.ssh_username == None or self.ssh_keyfile == None): 
          raise nuodbTools.Error("When restoring to a host that is not local you must provide ssh credentials")
        self.restorehost = nuodbTools.physical.Host(name = self.host, ssh_user = self.ssh_username, ssh_keyfile = self.ssh_keyfile)
    if not hasattr(self, "restorehost"):
      raise nuodbTools.Error("No member of the domain found at %s" % self.host)
    tempdir = "/".join([self.tarball_destination, "tmp", uuid.uuid4().__str__()])
    commands = ["mkdir -p %s" % tempdir]
    commands.append("tar -C %s -xvf %s" % (tempdir, tarball))
    commands.append("cat %s/*.metadata" % tempdir)
    print "Extracting %s to %s..." % (tarball, tempdir)
    for command in commands:
      r = self.restorehost.execute_command(command)
      if r[0] != 0:
        raise nuodbTools.Error("Got non-zero response when executing command %s: %s" % (command, " ".join([r[1], r[2]])))
    metadata = json.loads(r[1])
    dbname = "_".join([self.database, str(int(metadata['t']))])
    self.restoredb = nuodbTools.cluster.Database(name=dbname, domain = self.domainConnection)
    if self.restoredb.exists:
      raise nuodbTools.Error("Database %s already exists in the domain. Cannot restore an already running database." % dbname)
    archive_dir = "_".join([metadata['ad'], str(int(metadata['t']))])
    journal_dir = "_".join([metadata['jd'], str(int(metadata['t']))])
    # Need to find out what user is running nuodb to make the directories sane.
    command = "ps aux | grep nuoagent.jar | head -n 1 | awk '{print $1}'"
    nuo_user = self.restorehost.execute_command(command)[1].rstrip()
    commands = []
    print "Moving %s to %s" % ("/".join([tempdir, metadata['ad']]), archive_dir)
    print "Moving %s to %s" % ("/".join([tempdir, metadata['jd']]), journal_dir)
    commands.append("if [ -d %s ]; then sudo rm -rf %s; fi;" % (archive_dir, archive_dir))
    commands.append("mv %s %s" % ("/".join([tempdir, metadata['ad']]), archive_dir))
    commands.append("sudo chown -R %s %s" % (nuo_user, archive_dir))
    commands.append("if [ -d %s ]; then rm -rf %s; fi;" % (journal_dir, journal_dir))
    commands.append("mv %s %s" % ("/".join([tempdir, metadata['jd']]), journal_dir))
    commands.append("sudo chown -R %s %s" % (nuo_user, journal_dir))
    for command in commands:
      r = self.restorehost.execute_command(command)
      if r[0] != 0:
        raise nuodbTools.Error("Got non-zero response when executing command %s: %s" % (command, " ".join([r[1], r[2]])))
    print "Starting SM..."
    self.start_process(database = self.restoredb, processtype = "SM", host = self.restorehost_id, archive_dir = archive_dir, journal_dir = journal_dir)
    print "Starting TE..."
    self.start_process(database = self.restoredb, processtype = "TE", host = self.restorehost_id, user = db_user, password = db_password)
    print "Restored database to \"%s\" on %s" % (dbname, self.restorehost.name)
  
  def restore_zfs(self, db_user = None, db_password = None, snapshots = []):
    hosts = self.domainConnection.get_hosts()
    if db_user == None or db_password == None:
      raise nuodbTools.Error("You must specify db-user and db-password for the new database to restore it.")
    for host in hosts:
      if host['hostname'] == self.host:
        self.restorehost_id = host['id']
        if socket.gethostname() != self.host and ( self.ssh_username == None or self.ssh_keyfile == None): 
          raise nuodbTools.Error("When restoring to a host that is not local you must provide ssh credentials")
        self.restorehost = nuodbTools.physical.Host(name = self.host, ssh_user = self.ssh_username, ssh_keyfile = self.ssh_keyfile)
    if not hasattr(self, "restorehost"):
      raise nuodbTools.Error("No member of the domain found at %s" % self.host)
    commands = []
    dbname = ""
    restore_data = {}
    for snapshot in snapshots:
      unpack = snapshot.split("nuo-")
      unpack[1] = unpack[1].rstrip().replace("_","=").replace(".","/").replace(":","+")
      data = json.loads(zlib.decompress(base64.b64decode(unpack[1])))
      dbname = "_".join([data['db'], str(int(data['t']))])
      if "jd" in data:
        self.restoredb = "_".join([data['db'], str(int(data['t']))])
        dir = "_".join([data['jd'], str(int(data['t']))])
        commands.append("zfs clone %s %s" % (snapshot, re.sub(r'^/', '', dir)))
        restore_data['journal_dir'] = dir
      if "ad" in data:
        self.restoredb = "_".join([data['db'], str(int(data['t']))])
        dir = "_".join([data['ad'], str(int(data['t']))])
        commands.append("zfs clone %s %s" % (snapshot, re.sub(r'^/', '', dir)))
        restore_data['archive_dir'] = dir
    for command in commands:
      r = self.restorehost.execute_command(command)
      if r[0] != 0:
        raise nuodbTools.Error("Got non-zero response when executing command %s: %s" % (command, " ".join([r[1], r[2]])))
    self.restoredb = nuodbTools.cluster.Database(name=dbname, domain = self.domainConnection)
    print "Starting SM..."
    self.start_process(database = self.restoredb, processtype = "SM", host = self.restorehost_id, archive_dir = restore_data['archive_dir'], journal_dir = restore_data['journal_dir'])
    print "Starting TE..."
    self.start_process(database = self.restoredb, processtype = "TE", host = self.restorehost_id, user = db_user, password = db_password)
    print "Restored database to \"%s\" on %s" % (dbname, self.restorehost.name)

  def start_process(self, database, processtype="SM", host = None, archive_dir= None, journal_dir = None, user = None, password = None):
    if isinstance(host, nuodbTools.aws.Host):
      host_id = self.domainConnection.get_host_id(host.name)
    elif isinstance(host, nuodbTools.physical.Host):
      host_id = self.domainConnection.get_host_id(host.name)
    else:
      host_id = host
    return database.start_process(processtype = processtype, host_id = host_id, archive = archive_dir, journal = journal_dir, user = user, password = password)
    
  def stop_process(self, database, process_id, force=False):
    process_exists = False
    process_type = None
    for process in self.db.get_processes():
      if process['uid'] == process_id:
        process_exists = True
        if "transactional" in process:
          if process['transactional']:
            process_type = "TE"
          else:
            process_type = "SM"
        else:
          process_type = process['type']
    if process_exists:
      if len(self.db.get_processes(type=process_type)) <= 1 and not force:
        raise nuodbTools.Error("Only one process available of type %s in database %s and no force flag given- will not kill the process" % (process_type, self.database))
      else:
        print "Stopping %s" % process_id
        self.db.stop_process(process_id)
        time.sleep(10)
    else:
      raise nuodbTools.Error("Process %s does not exist in this database" % process_id)
    
class Error(Exception):
  pass

class TemporaryAddPolicy:
  def missing_host_key(self, client, hostname, key):
    pass