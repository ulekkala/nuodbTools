import boto.ec2
import traceback

class Zone:
    def __init__(self, name):
        self.name = name
    def connect(self, aws_access_key, aws_secret):
        self.connection = boto.ec2.connect_to_region(self.name, aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret)
        return self.connection
    def edit_security_group(self, name, description="EMPTY", rules=[]):
        errorstr = ""
        exists = False
        
        for security_group in self.connection.get_all_security_groups():
            if security_group.name == name:
                securityGroup = security_group
                exists = True
        if not exists:
            securityGroup = self.connection.create_security_group(name, description)
        for rule in rules:
          try:
            if rule['cidr_ip'] == "self":
              self.__add_security_group_rule(securityGroup=securityGroup, protocol=rule['protocol'], from_port=rule['from_port'], to_port=rule['to_port'], src_group=securityGroup)
            else:
              self.__add_security_group_rule(securityGroup=securityGroup, protocol=rule['protocol'], from_port=rule['from_port'], to_port=rule['to_port'], cidr_ip=rule['cidr_ip'])
          except:
            pass
        return securityGroup
    def __add_security_group_rule(self, securityGroup, protocol, from_port, to_port, cidr_ip = None, src_group=None, dry_run=None):
      if src_group != None:
        securityGroup.authorize(ip_protocol=protocol, from_port=from_port, to_port=to_port, src_group = src_group)
      else:
        securityGroup.authorize(ip_protocol=protocol, from_port=from_port, to_port=to_port, cidr_ip=cidr_ip)
    @property
    def amis(self):
      if not hasattr(self, 'amis_cached'):
        self.amis_cached = self.connection.get_all_images(owners=["self", "802164393885", "amazon"])
      return self.amis_cached
    def get_keys(self):
      return self.connection.get_all_key_pairs()
    def get_security_groups(self):
      return self.connection.get_all_security_groups()
    def get_subnets(self):
      subnets = {}
      networkinterfaces = self.connection.get_all_network_interfaces()
      for networkinterface in networkinterfaces:
        id = networkinterface.subnet_id
        subnets[id] = {}
        for arg in networkinterface.__dict__:
          subnets[id][arg] = networkinterface.__dict__[arg]
      return subnets
    @property
    def instances(self):
      instances = []
      for reservation in self.connection.get_all_reservations():
        for instance in reservation.instances:
          i = instance.__dict__
          if "Name" in instance.__dict__['tags']:
            i['name'] = instance.__dict__['tags']['Name']
          else:
            i['name'] = ""
          instances.append(i)
      return instances
    @property
    def security_groups(self):
      return self.connection.get_security_groups()
    @property
    def snapshots(self):
      return self.connection.get_all_snapshots(owner="self")
    @property
    def volumes(self):
      return self.connection.get_all_volumes()
          
          
          

class Error(Exception):
  pass