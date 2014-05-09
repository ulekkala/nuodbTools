import boto.ec2
import boto.vpc
import traceback

class Zone:
    def __init__(self, name, vpc_id = None):
        self.name = name
        self.vpc_id = vpc_id
        
    def connect(self, aws_access_key, aws_secret):
      self.aws_access_key = aws_access_key
      self.aws_secret = aws_secret
      self.connection = boto.ec2.connect_to_region(self.name, aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret)
      return self.connection
      
    def edit_security_group(self, name, description="EMPTY", rules=[], vpc_id = None):
        errorstr = ""
        exists = False
        
        if vpc_id != None:
          vpc_ids = [vpc_id]
        elif vpc_id == "all":
          vpc_ids = []
          for subnet in self.get_subnets():
            if subnet['vpc_id'] not in vpc_ids:
              vpc_ids.append['vpc_id']
        else:
          vpc_ids = [self.vpc_id]
        
        for vpc_id in vpc_ids:
          for security_group in self.connection.get_all_security_groups():
              if security_group.name == name and security_group.vpc_id == vpc_id:
                  securityGroup = security_group
                  exists = True
          if not exists:
            securityGroup = self.connection.create_security_group(name, description, vpc_id=vpc_id)
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
      vpc_conn = boto.vpc.VPCConnection(aws_access_key_id=self.aws_access_key, aws_secret_access_key=self.aws_secret, region=boto.ec2.get_region(self.name))
      for subnet in vpc_conn.get_all_subnets():
        subnets[subnet.id] = subnet.__dict__
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
    def instance_types(self):
      return self.connection.get_all_instance_types()
    
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