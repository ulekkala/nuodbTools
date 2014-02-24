import boto.ec2
import boto.route53
from paramiko import SSHClient, SFTPClient
import base64, inspect, json, os, socket, string, sys, tempfile, time

class Host:
  def __init__(self, 
               name, 
               EC2Connection = None, 
               Route53Connection = None, 
               dns_domain = None,
               advertiseAlt = False, 
               agentPort = 48004, 
               altAddr = "",
               autoconsole_port = "8888",
               domain ="domain", 
               domainPassword ="bird", 
               enableAutomation = False,
               enableAutomationBootstrap = False,
               hostname = None,
               isBroker = False, 
               portRange = 48005, 
               peers = [],
               ssh_user ="ec2-user", # User to ssh in as 
               ssh_key = None, # Name of AWS Keypair
               ssh_keyfile = None, # The private key on the local file system
               region = "default",
               web_console_port = "8080"):
    args, _, _, values = inspect.getargvalues(inspect.currentframe())
    for i in args:
      setattr(self, i, values[i])
    self.exists = False
    if self.dns_domain not in self.name:
      self.name = ".".join([self.name, self.dns_domain])

    for reservation in self.EC2Connection.get_all_reservations():
      for instance in reservation.instances:
        if "Name" in instance.__dict__['tags'] and instance.__dict__['tags']['Name'] == name and instance.state == 'running':
          self.exists = True
          self.instance = instance
          self.update_data()
          self.__get_amazon_data()
          self.__get_mounts()           

  def agent_action(self, action):
    command = "sudo service nuoagent " + action
    (rc, stdout, stderr) = self.ssh_execute(command)
    if rc != 0:
      return "Failed to %s nuoagent with command %s: %s" % (action, command, stderr)
    
  def agent_running(self, ip = None):
    while ip == None:
      time.sleep(1)
      self.update_data()
      ip = self.ext_ip 
    port = self.agentPort
    return self.is_port_available(port, ip)
    
    
  def apply_license(self, nuodblicense):
        if not self.isBroker:
            return "Can only apply a license to a node that is a Broker"
        f = tempfile.NamedTemporaryFile()
        f.write(nuodblicense)
        f.seek(0)
        self.scp(f.name, "/tmp/license.file")
        f.close()
        for command in [" ".join(["/opt/nuodb/bin/nuodbmgr --broker localhost --password", self.domainPassword, "--command \"apply domain license licenseFile /tmp/license.file\""])]:
            if self.ssh_execute(command)[0] != 0:
                sys.exit("Failed ssh execute on command " + command)
                
  def attach_volume(self, size, mount_point):
        if not self.exists:
            return("Node " + self.name + " doesn't exist")
        device = ""
        # find suitable device
        for letter in list(string.ascii_lowercase):
            if len(device) == 0:
                command = "ls /dev | grep sd" + letter
                if self.ssh_execute(command)[0] > 0:
                    device = "/".join(["", "dev", "sd" + letter])
                    print "Found " + device
        if len(device) == 0:
            sys.exit("Could not find a suitable device for mounting")
        volume = self.EC2Connection.create_volume(size, self.region)
        while volume.status != "available":
            volume.update()
            time.sleep(1)
        self.EC2Connection.attach_volume(volume.id, self.instance.id, device)
        while volume.attachment_state() != "attached":
            volume.update()
            time.sleep(1)
        for command in ["sudo mkdir -p " + mount_point, " ".join(["sudo", "mkfs", "-t ext4", device]), " ".join(["sudo", "mount", device, mount_point])]:
            print command
            self.ssh_execute(command)
        return self.ssh_execute("mount | grep " + mount_point)[0]
        
  def console_action(self, action):
        command = "sudo service nuoautoconsole " + action
        if self.ssh_execute(command)[0] != 0:
                return "Failed ssh execute on command " + command
            
  def create(self, ami, instance_type, getPublicAddress=False, security_groups=None, security_group_ids=None, subnet=None, userdata = None):
        if not self.exists:
            if userdata != None:
              self.userdata = userdata
            interface = boto.ec2.networkinterface.NetworkInterfaceSpecification(subnet_id=subnet, groups=security_group_ids, associate_public_ip_address=getPublicAddress)
            interface_collection = boto.ec2.networkinterface.NetworkInterfaceCollection(interface)
            reservation = self.EC2Connection.run_instances(ami, key_name=self.ssh_key, instance_type=instance_type, user_data=userdata, network_interfaces=interface_collection) 
            self.exists = True
            for instance in reservation.instances:
                self.instance = instance
                self.update_data()
                instance.add_tag("Name", self.name)
            return self
        else:
            print("Node " + self.name + " already exists. Not starting again.")
            self.update_data()
            return self
    
  def dns_delete(self):
        zone = self.Route53Connection.get_zone(self.dns_domain)
        for fqdn in [self.name]:
            if zone.find_records(fqdn, "A") != None:
                zone.delete_a(fqdn)
  
  def dns_set(self, type = "A", record = None, value = None):
        zone = self.Route53Connection.get_zone(self.dns_domain)
        if record != None:
          records = {record: value}
        else:
          while len(self.int_ip) == 0 or len(self.ext_ip) == 0:
            self.update_data()
            print "Waiting for IPs..."
            time.sleep(5)
          records = {self.name: self.ext_ip}.iteritems()
        for fqdn, value in records:
          if type == "TXT":
            pass
          else:
            if zone.find_records(fqdn, "A") != None:
                zone.update_a(fqdn, value=value, ttl=60)
            else:
                zone.add_a(fqdn, value=value)
                
  def __get_amazon_data(self):
    metadata_cmd = "curl http://169.254.169.254/latest/meta-data/"
    (return_code, null, stderr) = self.ssh_execute(metadata_cmd)
    if return_code != 0:
      raise Error("Unable to determine AWS instance data through command %s: %s" % (metadata_cmd, stderr))
    amazon_data = self.__get_amazon_field("/", metadata_cmd = metadata_cmd)
    self.amazon_data = amazon_data
    return amazon_data
    
  def __get_amazon_field(self, key, metadata_cmd):
    if len(key) == 0:
      raise Error("Key length of zero! Should not be here")
    cmd = metadata_cmd + key
    if key[-1] != "/":
      data = self.ssh_execute(cmd)[1]
      data_array = data.split("\r\n")
      if len(data_array) > 1:
        return data_array
      else:
        return data
    else:
      subkeys = self.ssh_execute(cmd)[1].split("\r\n")
      dataset = {}
      for subkey in subkeys:
        if len(subkey) > 0:
          if subkey[-1] == "/":
            keyname = subkey[0:len(subkey[0:-1])]
          else:
            keyname = subkey
          dataset[keyname] = self.__get_amazon_field(key = "".join([key, subkey]), metadata_cmd = metadata_cmd)
      return dataset
    
  def get_directory_target(self, dir):
    #resolves symlinks to find the actual directory
    rc, stdout, stderr = self.ssh_execute("sudo readlink -f " + dir)
    if rc != 0:
      raise Error("Could not find directory %s: %s" %(dir, stderr))
    return stdout.rstrip()
  
  def __get_mounts(self):
    cmd = "mount"
    (r, mount_output, stderr) = self.ssh_execute(cmd)
    if r != 0:
      raise Error("Unable to determine file volume mount info through command %s: %s" % (cmd, stderr))
    mount_lines = mount_output.split("\n")
    mounts = {}
    infra_devices = {}
    aliases = {}
    device_alias_list = self.ssh_execute("find /dev -maxdepth 1 -type l -exec ls -lah {} \;")[1].split("\r\n")
    for device_alias_line in device_alias_list:
      device_alias_fields = device_alias_line.split(" ")
      if len(device_alias_fields) > 1:
        if device_alias_fields[10][0] != "/":
          target = "/".join(["/dev", device_alias_fields[10]])
        else:
          target = device_alias_fields[10]
        aliases[device_alias_fields[8]] = target
    if self.EC2Connection != None:
      volumes = self.EC2Connection.get_all_volumes()
      for volume in volumes:
        v = volume.attach_data
        if v.status == "attached" and v.instance_id== self.amazon_data['instance-id']:
          infra_devices[v.device] = v.id
    for line in mount_lines:
      if len(line) > 0:
        fields = line.split(" ")
        device = fields[0]
        mounts[fields[2]] = {"dev": device, "type": fields[4]}
        if device in infra_devices:
          mounts[fields[2]]['ebs_volume'] = infra_devices[device]
        else:
          for link in aliases:
            if aliases[link] == device and link in infra_devices:
              mounts[fields[2]]['ebs_volume'] = infra_devices[link]
    self.volume_mounts = mounts
    
  def __get_ssh_connection(self):
        try:
            host = socket.gethostbyname(self.name)
        except:
            host = self.ext_ip
        self.ssh_connection = SSHClient()
        self.ssh_connection.set_missing_host_key_policy(TemporaryAddPolicy())
        # self.ssh_connection.load_system_host_keys()
        if self.ssh_keyfile != None:
          self.ssh_connection.connect(host, username=self.ssh_user, key_filename = self.ssh_keyfile)
        else:
          self.ssh_connection.connect(host, username=self.ssh_user)
 
  def health(self):
    return self.ssh_execute("sudo service nuoagent status")[0]
      
  def is_port_available(self, port, ip = None):
    if ip == None:
      ip = self.ext_ip
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    #print "Testing " + ip + ":" + str(port)
    result = s.connect_ex((ip, port))
    #print result
    s.close()
    if result == 0:
      return True
    else:
      return False
  
  def path_exists(self, path, test = "d"):
    rc, stdout, stderr = self.ssh_execute("test -%s %s" % (test, path))
    if rc == 0:
      return True
    else:
      return False
    
  def provision(self, peers=[], enableAutomation=False, enableAutomationBootstrap=False, templateFiles=["default.properties", "nuodb-rest-api.yml", "webapp.properties"]):
        if len(peers) > 0:
            self.peers = peers
        if enableAutomation != self.enableAutomation:
            self.enableAutomation = enableAutomation
        if enableAutomationBootstrap != self.enableAutomationBootstrap:
            self.enableAutomationBootstrap = enableAutomationBootstrap
        self.update_data()
        self.scp(local_file="./templates/yum/nuodb.repo", remote_file="/tmp/nuodb.repo")
        for command in [ 'sudo hostname ' + self.name, 'sudo mv /tmp/nuodb.repo /etc/yum.repos.d/', 'sudo yum -y install nuodb']:
            if self.ssh_execute(command)[0] != 0:
                return "Failed ssh execute on command " + command
        properties = dict(
            advertiseAlt=str(self.advertiseAlt).lower(),
            agentPort=self.agentPort,
            # altAddr=str(self.ext_fqdn),
            altAddr=str(self.ext_ip),
            domain=self.domain,
            domainPassword=self.domainPassword,
            enableAutomation=str(self.enableAutomation).lower(),
            enableAutomationBootstrap=str(self.enableAutomationBootstrap).lower(),
            isBroker=str(self.isBroker).lower(),
            peers=",".join(self.peers),
            portRange=self.portRange,
            region=self.region
            )
        for templateFile in templateFiles:
            templateContentFile = open("./templates/" + templateFile, "r")
            props = string.Template(templateContentFile.read())
            output = props.substitute(properties)
            f = tempfile.NamedTemporaryFile()
            f.write(str(output))
            templateContentFile.close()
            f.seek(0)
            self.scp(f.name, "/tmp/" + templateFile)
            f.close()
            command = "sudo mv /tmp/" + templateFile + " /opt/nuodb/etc/" + templateFile
            if self.ssh_execute(command)[0] != 0:
                return "Failed ssh execute on command " + command
        return "OK"      

  def scp(self, local_file, remote_file):    
        if not hasattr(self, 'ssh_connection'):
            self.__get_ssh_connection()
        sftp = SFTPClient.from_transport(self.ssh_connection.get_transport())
        sftp.put(local_file, remote_file)

  def ssh_execute(self, command, nbytes = "99999"):
    if not hasattr(self, 'ssh_connection'):
      self.__get_ssh_connection()
    channel = self.ssh_connection.get_transport().open_session()
    channel.get_pty()
    channel.exec_command(command)
    exit_code = channel.recv_exit_status()
    stdout = channel.recv(nbytes)
    stderr = channel.recv_stderr(nbytes)
    return (exit_code, stdout, stderr)
      
  def status(self):
    if self.exists:
      self.update_data()
      return self.instance.state
    else:
      return "Host does not exist"
          
  def terminate(self):
    if self.exists:
      # self.dns_delete()
      self.EC2Connection.terminate_instances(self.id)
      self.exists = False
      return("Terminated " + self.name)
    else:
      return("Cannot terminate " + self.name + " as node does not exist.")
          
  def update_data(self):
    self.instance.update()
    self.id = self.instance.id
    self.ext_ip = self.instance.ip_address
    self.int_ip = self.instance.private_ip_address
  
  def webconsole_action(self, action):
    command = "sudo service nuowebconsole " + action
    (rc, stdout, stderr) = self.ssh_execute(command)
    if rc != 0:
      return "Failed to %s nuowebconsole with command %s: %s" % (action, command, stderr)
        
class Error(Exception):
  pass        

class TemporaryAddPolicy:
    def missing_host_key(self, client, hostname, key):
        pass
