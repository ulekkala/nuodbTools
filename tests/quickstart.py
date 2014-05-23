import json
import nuodbTools
import tempfile
import time
import unittest
import uuid
from nuodb_aws_quickstart import cluster 

config_file = "../config.json"
domain_name = str(uuid.uuid4())
with open(config_file) as f:
  read_config = json.loads(f.read())
  f.close()
read_config['domain_name'] = domain_name        
unittest_config_handle = tempfile.NamedTemporaryFile(delete = False)
unittest_config_handle.write(json.dumps(read_config, indent=2))
unittest_config_file = unittest_config_handle.name
unittest_config_handle.close()


class nuodbQuickstartTest(unittest.TestCase):
  @classmethod  
  def setUpClass(cls):
    cluster(action="create", config_file=unittest_config_file)

  @classmethod
  def tearDownClass(cls):
    cluster(action="terminate", config_file=unittest_config_file)

  @property
  def cluster_members(self):
    cluster_members = {}
    zones = self.config['zones']
    cluster_name = self.config['domain_name']
    for zone in zones:
      cluster_members[zone] = []
      for i in range(0, self.config['zones'][zone]['servers']):
        cluster_members[zone].append("db%s.%s.%s.nuoDB" % (str(i), cluster_name, zone))
    return cluster_members
  
  @property
  def config(self):
    if hasattr(self, "config_cache"):
      return self.config_cache
    else:
      with open(unittest_config_file) as f:
        read_config = json.loads(f.read())
        f.close()
      read_config['domain_name'] = domain_name
      self.config_cache = read_config
      return read_config 
  
  @property
  def hosts(self):
    if not hasattr(self, "hosts_cache"):
      self.hosts_cache = {}
      for zone in self.cluster_members:
        conn = nuodbTools.aws.Zone(zone).connect(self.config['aws_access_key'], self.config['aws_secret'])
        for host in self.cluster_members[zone]:
          self.hosts_cache[host] = nuodbTools.aws.Host(
                                 name = host,
                                 ec2Connection = conn,
                                 ssh_user = self.config['ssh_key'],
                                 ssh_keyfile = self.config['ssh_keyfile']
                                 )
    return self.hosts_cache
    
  def test_config(self):
    print "Using config:"
    print json.dumps(self.config, indent=2)
    
  def test_membership(self, wait_time = 300):
    for host in self.hosts:
      try:
        print "Node %s: %s (%s)" % (host, self.hosts[host].instance.id, self.hosts[host].ext_ip)
      except:
        self.fail("Node %s does not have an instance id. This probably means it was not created." % host)
      #SSH check
      countdown = wait_time
      while countdown > 0 and not self.hosts[host].is_port_available(22):
        time.sleep(5)
        countdown -= 5
      if countdown <= 0:
        self.fail("Waited for ssh on %s for %s seconds, not available. Exiting" % (host, wait_time))
      print " -- ssh ok"
      # Agent check
      countdown = wait_time
      while countdown > 0 and not self.hosts[host].agent_running():
        print self.hosts[host].agent_running()
        time.sleep(5)
        countdown -= 5
      if countdown <= 0:
        self.fail("Waited for agent on %s for %s seconds, not available. Exiting" % (host, wait_time))
      print " -- agent ok"
    self.assertTrue(True)   

if __name__ == "__main__":
  unittest.main()