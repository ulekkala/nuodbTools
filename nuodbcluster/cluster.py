'''
Created on Jan 28, 2014

@author: rkourtz
'''
import boto.route53
import nuodbaws
import chef, inspect, json, os, random, shelve

class NuoDBCluster:
    def __init__(self, aws_access_key = "", aws_secret = "", cluster_name = "default", 
                 dns_domain="", domain_name="domain", domain_password="bird", 
                 instance_type = "m1.large", nuodb_license = "", ssh_key = "",  
                 data_dir = "/".join([os.path.dirname(inspect.stack()[-1][1]), "data"])):
      self.route53 = boto.route53.connection.Route53Connection(aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret)
      database_file = "/".join([data_dir, cluster_name + ".shelf"])
      args, _, _, values = inspect.getargvalues(inspect.currentframe())
      for i in args:
        setattr(self, i, values[i])
      
      self.db = shelve.open(database_file, writeback = True)
      self.zones = {} #store our zone connections
      #self.db.close()
    def connect_zone(self, zone):
      self.zones[zone] = nuodbaws.NuoDBzone(zone)
      self.zones[zone].connect(aws_access_key=self.aws_access_key, aws_secret=self.aws_secret)
      if "customers" not in self.db:
        self.db['customers'] = {}
      if self.cluster_name not in self.db['customers']:
        self.db['customers'][self.cluster_name] = {}
      if zone not in self.db['customers'][self.cluster_name]:
        self.db['customers'][self.cluster_name][zone] = {"hosts": {}, "brokers": []}
    def create_host(self, name, zone, ami = "", security_group_ids=[], subnets = []):
      if zone not in self.zones:
        raise Error("You must connect to a zone first before you can create a host in that zone")
      if len(subnets) == 0:
        raise Error("You must specify the target subnets in an array")
      # make sure ami is valid
      valid_amis = []
      for each_ami in self.zones[zone].get_amis():
        valid_amis.append(each_ami.id)
      if ami not in valid_amis:
        raise Error("ami '%s' is not valid" % (ami))
      stub = self.db['customers'][self.cluster_name][zone]['hosts']
      if name == None:
        increment = len(stub)
        basename = "db"+str(increment)
      else:
        basename = name
        increment = random.randrange(0,len(subnets))
      host = ".".join([basename, self.cluster_name, zone])
      fqdn = ".".join([host, self.dns_domain])
      # Generate data for chef... is it a broker? peers?
      if len(self.db['customers'][self.cluster_name][zone]['brokers']) < 1:
        chef_data = {"run_list": "recipe[nuodb]", "nuodb": {"is_broker": True, "enableAutomation": True, "enableAutomationBootstrap": True, "automationTemplate": "Minimally Redundant", "altAddr": "", "brokers": []}}
        self.db['customers'][self.cluster_name][zone]['brokers'].append(fqdn)
      else:
        if len(self.db['customers'][self.cluster_name][zone]['brokers']) < 2:
          chef_data = {"run_list": "recipe[nuodb]", "nuodb": {"is_broker": True, "enableAutomation": False, "enableAutomationBootstrap": False, "automationTemplate": "Minimally Redundant", "altAddr": "", "brokers": self.db['customers'][self.cluster_name][zone]['brokers']}}
          self.db['customers'][self.cluster_name][zone]['brokers'].append(fqdn)
        else:
          chef_data = {"run_list": "recipe[nuodb]", "nuodb": {"is_broker": False, "enableAutomation": False, "enableAutomationBootstrap": False, "automationTemplate": "Minimally Redundant", "altAddr": "", "brokers": self.db['customers'][self.cluster_name][zone]['brokers']}}
      stub[host] = {"fqdn": fqdn}
      stub[host]['chef_data'] = chef_data
      stub[host]['obj'] = nuodbaws.NuoDBhost(host, EC2Connection=self.zones[zone].connection, Route53Connection=self.route53, dns_domain=self.dns_domain, domain = self.domain_name, domainPassword = self.domain_password, advertiseAlt = True)
      stub[host]['obj'].create(ami=ami, key_name=self.ssh_key, instance_type=self.instance_type, security_group_ids=security_group_ids, subnet = subnets[increment % len(subnets)], getPublicAddress = True, ChefUserData = chef_data)
      return host
    def dump_db(self):
      return self.db
    def exit(self):
      self.db.close()
    def get_host(self, host_id):
      name, customer, zone = host_id.split(".")
      if host_id in self.db['customers'][customer][zone]['hosts']:
        return self.db['customers'][customer][zone]['hosts'][host_id]['obj']
      else:
        raise Error("No host found with id of '%s'" % host_id)
    def get_hosts(self):
      hosts = [];
      for customer in self.db['customers']:
        for zone in self.db['customers'][customer]:
          for host in self.db['customers'][customer][zone]['hosts']:
            hosts.append(host)
      return sorted(hosts)
    def terminate_all_hosts(self):
      hosts = []
      for customer in self.db['customers']:
        for zone in self.db['customers'][customer]:
          for host in self.db['customers'][customer][zone]['hosts']:
            hosts.append(self.db['customers'][customer][zone]['hosts'][host]['obj'])
      for host in hosts:
        host.terminate()
        del self.db['customers'][customer][zone]['hosts'][host.name]
     
class Error(Exception):
  pass 
        