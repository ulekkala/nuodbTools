import boto.ec2
import json
import nuodbTools.aws
import nuodbTools.exception
import os
import random
import tempfile
import time
import unittest
import uuid

config_file = "../../../config.json"
if not os.path.exists(config_file):
  raise nuodbTools.Error("Can't find required config file %s" % config_file)
with open(config_file) as f:
  read_config = json.loads(f.read())
  f.close()
aws_access_key = read_config['aws_access_key']
aws_secret = read_config['aws_secret']
aws_region = sorted(read_config['zones'].keys())[0] 
aws_vpc_id = read_config['zones'][aws_region]['vpcs'][0]
aws_ami = read_config['zones'][aws_region]['ami']
aws_instance_type = read_config['instance_type']
aws_private_key = read_config['ssh_keyfile']
aws_ssh_key_id = read_config['ssh_key']
aws_security_groups = read_config['zones'][aws_region]['security_group_ids']
name = "unittest_%s" % str(uuid.uuid4())


class Base(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    # Create the host
    cls._zone = nuodbTools.aws.Zone(name=aws_region, vpc_id=aws_vpc_id)
    cls._ec2Connection = cls._zone.connect(aws_access_key = aws_access_key, aws_secret=aws_secret)
    subnets = cls._zone.get_subnets(vpc_id = aws_vpc_id)
    subnet = subnets.keys()[random.randrange(0,len(subnets.keys()))]
    
    cls._host = nuodbTools.aws.Host(
                        name = name,
                        ec2Connection = cls._ec2Connection,
                        ssh_key = aws_ssh_key_id,
                        ssh_keyfile = aws_private_key)
    cls._host.create(ami= aws_ami, instance_type=aws_instance_type, getPublicAddress = True, security_group_ids = aws_security_groups, subnet = subnet)
    wait_seconds = 300
    while wait_seconds > 0 and not cls._host.is_port_available(22):
      time.sleep(5)
      wait_seconds -= 5
      cls._host.update_data()
    if wait_seconds <= 0:
      cls.fail("Instance %s did not have SSH available after 300 seconds")
    else:
      print "started ec2 instance"
  
  @classmethod
  def tearDownClass(cls):
    cls._host.terminate()

  def test_ephemeral_disk(self):
    if aws_instance_type != "t1.micro":
      self.assertEqual(self._host.execute_command("ls /dev | grep xvdb")[0], 0)
  
  def test_mounts(self):
    print self._host.volume_mounts
    self.assertTrue(True)
    
  def test_scp_file(self):
    f = tempfile.NamedTemporaryFile(delete=False)
    i=0
    while i < 100:
      f.write(str(uuid.uuid4()))
      i += 1
    f.close()
    self.assertTrue(self._host.copy(f.name, "/tmp/myfile"))
    os.remove(f.name)
      
  def test_ssh_execute(self):
    self.assertEqual(self._host.execute_command("hostname")[0], 0)
    
  def test_ssh_sudo_execute(self):
    self.assertEqual(self._host.execute_command("sudo hostname")[0], 0)
  
  def test_add_subtract_volume(self):
    self._host.attach_volume(1, "/mount/unittest")
    self.assertTrue(self._host.detach_volume("/mount/unittest", delete=True))
  
  
    
if __name__ == "__main__":
  unittest.main()