'''
Created on Feb 7, 2014

@author: rkourtz
'''
# requests module available at http://docs.python-requests.org/en/latest/
import boto.ec2
import nuodbTools.aws
import nuodbTools.cluster
import nuodbTools.physical
import inspect, json, random, time

class Backup():
  def __init__(self, 
               database = None, host = None, 
               aws_access_key = None, aws_secret = None, aws_region = None, 
               domainConnection = None, ec2Connection = None, 
               rest_username=None, rest_password=None, rest_url=None, 
               ssh_username=None, ssh_keyfile=None, 
               tarball_destination = None, backup_type = "auto"):
    args, _, _, values = inspect.getargvalues(inspect.currentframe())
    for i in args:
      setattr(self, i, values[i])
      
    if backup_type == "tarball" and tarball_destination == None:
      raise Error("Tarball nuodb_backup must have a destination")
    if not hasattr(self, 'domainConnection') or self.domainConnection == None:
      self.domainConnection = nuodbTools.cluster.Domain(rest_url=rest_url, rest_username=rest_username, rest_password=rest_password)
    if self.ec2Connection == None:
      if aws_region == None or aws_access_key == None or aws_secret == None:
        raise Error("aws_region, aws_access_key & aws_secret parameters must be defined for AWS")
      self.ec2Connection = boto.ec2.connect_to_region(aws_region, aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret)
    if database not in self.domainConnection.get_databases():
      raise Error("Can not find database %s in domain provided")
    self.db = nuodbTools.cluster.Database(name=self.database, domain = self.domainConnection)
    self.backup()
  
  def backup(self):
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
      raise Error("Can't determine mount points for %s and %s" % (archive['dir'], journal['dir']))
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
        name = self.__backup_ebs(archive['volume']['ebs_volume'], self.backuphost)
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
        notification = self.__offline_backup(host = self.backuphost, storage_manager = mysm, archive = archive, journal = None)
    else:
      notification = self.__offline_backup(host = self.backuphost, storage_manager = mysm, archive = archive, journal = journal)
    print notification
    print "Exiting..."
  
  def __offline_backup(self, host = None, storage_manager = None, archive = None, journal = None):
    # If we are here we are going to take down the SM, take a nuodb_backup, and start the process
    print "No online nuodb_backup method available"
    if len(self.db.get_processes(type="SM")) < 2:
      print "Not enough storage managers to take nuodb_backup. Need 2, have %s " % len(self.db.get_processes(type="SM")) 
      print "Please start another and wait for it to synchronize"
      exit(1)
    else:
      print "Have enough storage managers to proceed." 
    print "Stop SM process..."
    self.stop_process(process_id = storage_manager['uid'])
    print "Take snapshot..."
    notification = ""
    timestamp = time.strftime("%d%b%Y %H:%M:%S GMT", time.gmtime())
    for dir in [archive, journal]:
      if dir != None and "volume" in dir:
        if "ebs_volume" in dir['volume'] and self.backup_type in ["ebs", "auto", None]:
          # This is an amazon EBS volume
          name = self.__backup_ebs(dir['volume']['ebs_volume'], host, backup_type = dir['type'], timestamp = timestamp)
          notification += "Created an EBS nuodb_backup of %s:%s with snapshot id %s" % (self.database, dir['type'], name) + "\n"
        elif "type" in dir['volume'] and dir['volume']['type'] == "zfs" and self.backup_type in ["zfs", "auto", None]:
          backup = self.__backup_zfs(directory = dir['dir'], device = dir['volume']['dev'], host = host, backup_type = dir['type'], timestamp = timestamp)
          if backup[0]:
            notification +=  backup[1]+ "\n"
          else:
            Error(backup[1])
        else:
          notification += self.__backup_tarball(
                                               source = dir['dir'], destination = self.tarball_destination,
                                               host = host, backup_type = dir['type'],
                                               timestamp = timestamp
                                               ) + "\n"
    print "Start SM..."
    if journal == None or journal['dir'] == None:
      journal_dir = None
    else:
      journal_dir = journal['dir']
    self.start_process(type = "SM", archive_dir = archive['dir'], journal_dir = journal_dir)
    return notification
  
  def __backup_ebs(self, vol_id, host, backup_type = "", timestamp = time.strftime("%d%b%Y %H:%M:%S GMT", time.gmtime())):
    print "Doing AWS EBS snapshot of %s" % vol_id
    if backup_type != "":
      dbname = ":".join([backup_type, self.database])
    else:
      dbname = self.database
    description = "NuoDB Backup of %s from %s on %s" % (dbname, host.name, timestamp)
    snapshot = self.ec2Connection.create_snapshot(volume_id = vol_id, description = description[0:255])
    snapshot.update()
    return (True, snapshot.id)
    
  def __backup_zfs(self, directory, device, host, backup_type = "", timestamp = time.strftime("%d%b%Y %H:%M:%S GMT", time.gmtime())):
    if backup_type != "":
      dbname = ":".join([backup_type, self.database])
    else:
      dbname = self.database
    description = "NuoDB Backup of %s from %s on %s" % (dbname, host.hostname, timestamp)
    command = "sudo zfs snapshot %s@\"%s\"" % (device, description)
    rc, stdout, stderr = host.execute_command(command)
    if  rc != 0:
      returnmessage = "Command %s failed to execute: %s" % (command, stderr)
      return (False, returnmessage)
    return (True, host.execute_command("sudo zfs list -t snapshot")[1])
    
  def __backup_tarball(self, source, destination, host, backup_type = "", timestamp = time.strftime("%d%b%Y %H:%M:%S GMT", time.gmtime())):
    if backup_type != "":
      dbname = ":".join([backup_type, self.database])
    else:
      dbname = self.database
    filename = "NuoDB_backup_%s_%s_%s.tgz" % (dbname, host.hostname, timestamp.replace(" ", "_"))
    print filename
    command = """
              src=`sudo du -s %s | awk '{print $1}'`;
              dest=`sudo df %s | awk '{print $4}' | tail -n 1`;
              if [ $src -gt $dest ];
              then
                echo "Insufficient space on destination drive. Have $dest available, need $src";
                exit 2;
              else 
                echo "Space check OK. Source: $src Dest: $dest";
              fi
              """ % (source, destination)
    print host.execute_command(command)
    return "Tarball nuodb_backup is yet to be implemented"
    
  def dump_data(self):
    return self.__dict__
  
  def start_process(self, type="SM", archive_dir= None, journal_dir = None):
    self.db.start_process(type = type, host = self.backuphost.name, archive = archive_dir, journal = journal_dir)
    
  def stop_process(self, process_id, force=False):
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
        raise Error("Only one process available of type %s in database %s and no force flag given- will not kill the process" % (process_type, self.database))
      else:
        print "Stopping %s" % process_id
        self.db.stop_process(process_id)
    else:
      raise Error("Process %s does not exist in this database" % process_id)
    
class Error(Exception):
  pass

class TemporaryAddPolicy:
  def missing_host_key(self, client, hostname, key):
    pass