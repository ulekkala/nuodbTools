
from paramiko import SSHClient, SFTPClient
import inspect, json, os, socket, string, subprocess, sys, tempfile, time

class Host:
  def __init__(self, 
               name, 
               advertiseAlt = False, 
               agentPort = 48004, 
               altAddr = "",
               autoconsole_port = "8888",
               domain ="domain", 
               domainPassword ="bird", 
               enableAutomation = False,
               enableAutomationBootstrap = False,
               isBroker = False, 
               portRange = 48005, 
               peers = [],
               ssh_user = None, # User to ssh in as 
               ssh_keyfile = None, # The private key on the local file system
               region = "default",
               web_console_port = "8080"):
    args, _, _, values = inspect.getargvalues(inspect.currentframe())
    for i in args:
      setattr(self, i, values[i])
    if self.ssh_user == None:
      self.localMachine = True
      self.hostname = self.execute_command("hostname")[1]
    else:
      self.hostname = name
      self.localMachine = False
    self.exists = True      

  def agent_action(self, action):
    command = "sudo service nuoagent " + action
    (rc, stdout, stderr) = self.execute_command(command)
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
        self.copy(f.name, "/tmp/license.file")
        f.close()
        for command in [" ".join(["/opt/nuodb/bin/nuodbmgr --broker localhost --password", self.domainPassword, "--command \"apply domain license licenseFile /tmp/license.file\""])]:
            if self.execute_command(command)[0] != 0:
                sys.exit("Failed ssh execute on command " + command)
        
  def console_action(self, action):
    command = "sudo service nuoautoconsole " + action
    if self.execute_command(command)[0] != 0:
      return "Failed ssh execute on command " + command
  
  def copy(self, local_file, remote_file):  
    if self.localMachine:
      command = "cp %s %s" % (local_file, remote_file)
      return self.execute_command(command)
    else:  
      if not hasattr(self, 'ssh_connection'):
        self.__get_ssh_connection()
      sftp = SFTPClient.from_transport(self.ssh_connection.get_transport())
      obj = sftp.put(local_file, remote_file)
      return (0, "Copied to %s" % obj.__str__(), "")
        
  def execute_command(self, command, nbytes = "99999"):
    if self.localMachine:
      p = subprocess.Popen([command], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      stdout, stderr = p.communicate()
      exit_code = p.returncode
    else:
      if not hasattr(self, 'ssh_connection'):
        self.__get_ssh_connection()
      channel = self.ssh_connection.get_transport().open_session()
      channel.get_pty()
      channel.exec_command(command)
      exit_code = channel.recv_exit_status()
      stdout = channel.recv(nbytes)
      stderr = channel.recv_stderr(nbytes)
    return (exit_code, stdout, stderr)
    
  def get_directory_target(self, dir):
    #resolves symlinks to find the actual directory
    rc, stdout, stderr = self.execute_command("sudo readlink -f " + dir)
    if rc != 0:
      raise Error("Could not find directory %s: %s" %(dir, stderr))
    return stdout.rstrip()
    
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
    return self.execute_command("sudo service nuoagent status")[0]
      
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
    rc, stdout, stderr = self.execute_command("test -%s %s" % (test, path))
    if rc == 0:
      return True
    else:
      return False
    
  def provision(self, peers=[], enableAutomation=False, enableAutomationBootstrap=False, templateFiles=["default.properties", "nuodb-frontend-api.yml", "webapp.properties"]):
        if len(peers) > 0:
            self.peers = peers
        if enableAutomation != self.enableAutomation:
            self.enableAutomation = enableAutomation
        if enableAutomationBootstrap != self.enableAutomationBootstrap:
            self.enableAutomationBootstrap = enableAutomationBootstrap
        self.update_data()
        self.copy(local_file="./templates/yum/nuodb.repo", remote_file="/tmp/nuodb.repo")
        for command in [ 'sudo hostname ' + self.name, 'sudo mv /tmp/nuodb.repo /etc/yum.repos.d/', 'sudo yum -y install nuodb']:
            if self.execute_command(command)[0] != 0:
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
            self.copy(f.name, "/tmp/" + templateFile)
            f.close()
            command = "sudo mv /tmp/" + templateFile + " /opt/nuodb/etc/" + templateFile
            if self.execute_command(command)[0] != 0:
                return "Failed ssh execute on command " + command
        return "OK"      
      
  def status(self):
    if self.exists:
      self.update_data()
      return self.instance.state
    else:
      return "Host does not exist"
          
  def terminate(self):
    return (False, "Not supported")
          
  def update_data(self):
    good = False
    count = 0
    while not good and count < 5:
      try:
        self.instance.update()
        self.id = self.instance.id
        self.ext_ip = self.instance.ip_address
        self.int_ip = self.instance.private_ip_address
        return True
      except:
        time.sleep(5)
        count += 1
    return False
  
  @property
  def volume_mounts(self):
    cmd = "mount"
    (r, mount_output, stderr) = self.execute_command(cmd)
    if r != 0:
      raise Error("Unable to determine file volume mount info through command %s: %s" % (cmd, stderr))
    mount_lines = mount_output.split("\n")
    mounts = {}
    infra_devices = {}
    aliases = {}
    device_alias_list = self.execute_command("find /dev -maxdepth 1 -type l -exec ls -lah {} \;")[1].split("\r\n")
    for device_alias_line in device_alias_list:
      device_alias_fields = device_alias_line.split(" ")
      if len(device_alias_fields) > 1:
        if device_alias_fields[10][0] != "/":
          target = "/".join(["/dev", device_alias_fields[10]])
        else:
          target = device_alias_fields[10]
        aliases[device_alias_fields[8]] = target
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
    return mounts
  
  def webconsole_action(self, action):
    command = "sudo service nuowebconsole " + action
    (rc, stdout, stderr) = self.execute_command(command)
    if rc != 0:
      return "Failed to %s nuowebconsole with command %s: %s" % (action, command, stderr)
        
class Error(Exception):
  pass        

class TemporaryAddPolicy:
    def missing_host_key(self, client, hostname, key):
        pass
