'''
Created on Jan 28, 2014

@author: rkourtz
'''

import boto.route53
import nuodbaws
import inspect, json, os, random, shelve, time

class NuoDBCluster:
    
    def __init__(self, aws_access_key = "", aws_secret = "", cluster_name = "default", 
                 dns_domain="", domain_name="domain", domain_password="bird", 
                 instance_type = "m1.large", nuodb_license = "", ssh_key = "",  
                 data_dir = "/".join([os.path.dirname(os.path.abspath(inspect.stack()[-1][1])), "data"]), 
                 brokers_per_zone = 2, enable_monitoring = True, alert_email = "alert@example.com"):
      self.route53 = boto.route53.connection.Route53Connection(aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret)
      database_file = "/".join([data_dir, cluster_name + ".shelf"])
      args, _, _, values = inspect.getargvalues(inspect.currentframe())
      for i in args:
        setattr(self, i, values[i])
      
      self.db = shelve.open(database_file, writeback = True)
      self.zones = {} #store our zone connections
      #self.db.close()
    
    def add_host(self, name, zone, ami = "", security_group_ids=[], subnets = []):
      if zone not in self.zones:
        raise Error("You must connect to a zone first before you can add a host in that zone")
      if len(subnets) == 0:
        raise Error("You must specify the target subnets in an array")
      # make sure ami is valid
      valid_amis = []
      for each_ami in self.zones[zone].get_amis():
        valid_amis.append(each_ami.id)
      if ami not in valid_amis:
        raise Error("ami '%s' is not valid" % (ami))
      stub = self.db['customers'][self.cluster_name]['zones'][zone]['hosts'] 
      if name == None:
        increment = len(stub)
        basename = "db"+str(increment)
      else:
        basename = name
        increment = random.randrange(0,len(subnets))
      host = ".".join([basename, self.cluster_name, zone])
      fqdn = ".".join([host, self.dns_domain])
      if host not in stub:
        stub[host] = {}
      # Generate data for chef... is it a broker? peers?
      if "brokers" not in self.db['customers'][self.cluster_name] or len(self.db['customers'][self.cluster_name]['brokers']) < 1:
        chef_data = {"nuodb": {"is_broker": True, "enableAutomation": True, "enableAutomationBootstrap": True}}
        self.db['customers'][self.cluster_name]['brokers'] = [fqdn]
        self.db['customers'][self.cluster_name]['zones'][zone]['brokers'] += 1
      elif self.db['customers'][self.cluster_name]['zones'][zone]['brokers'] < self.brokers_per_zone:
        chef_data = {"nuodb": {"is_broker": True, "enableAutomation": False, "enableAutomationBootstrap": False}}
        self.db['customers'][self.cluster_name]['brokers'].append(fqdn)
        self.db['customers'][self.cluster_name]['zones'][zone]['brokers'] += 1
      else:
        chef_data = {"nuodb": {"is_broker": False, "enableAutomation": False, "enableAutomationBootstrap": False}}
      #common Chef information
      chef_data["run_list"] = "recipe[nuodb]" 
      chef_data["nuodb"]['automationTemplate'] = "Minimally Redundant"
      chef_data["nuodb"]['altAddr'] = "" # Populate this at boot time
      chef_data["nuodb"]['region'] = zone
      chef_data["nuodb"]['monitoring'] = {"enable": True, "alert_email": self.alert_email}
      chef_data['nuodb']['license'] = self.nuodb_license
      chef_data["nuodb"]['domain_name'] = self.domain_name
      chef_data["nuodb"]['domain_password'] = self.domain_password
      stub[host]['chef_data'] = chef_data
      stub[host]["fqdn"] = fqdn
      stub[host]['ami'] = ami
      stub[host]['security_group_ids'] = security_group_ids
      stub[host]['subnet'] = subnets[len(stub) % len(subnets)]
      stub[host]['obj'] = nuodbaws.NuoDBhost(host, EC2Connection=self.zones[zone].connection, Route53Connection=self.route53, dns_domain=self.dns_domain, domain = self.domain_name, domainPassword = self.domain_password, advertiseAlt = True, region = zone)
      return host

    def connect_zone(self, zone):
      self.zones[zone] = nuodbaws.NuoDBzone(zone)
      self.zones[zone].connect(aws_access_key=self.aws_access_key, aws_secret=self.aws_secret)
      if "customers" not in self.db:
        self.db['customers'] = {}
      if self.cluster_name not in self.db['customers']:
        self.db['customers'][self.cluster_name] = {"zones": {}, "brokers": []}
      if zone not in self.db['customers'][self.cluster_name]['zones']:
        self.db['customers'][self.cluster_name]['zones'][zone] = {"hosts": {}, "brokers": 0}
        
    def create_cluster(self):
      for zone in self.zones:
        stub = self.db['customers'][self.cluster_name]['zones'][zone]['hosts']
        for host in sorted(stub):
          # Now that all processes are known we can populate each node with a list of brokers
          stub[host]['chef_data']['nuodb']['brokers'] = self.db['customers'][self.cluster_name]['brokers']
          obj = stub[host]['obj'].create(ami=stub[host]['ami'], key_name=self.ssh_key, instance_type=self.instance_type, security_group_ids=stub[host]['security_group_ids'], subnet = stub[host]['subnet'], getPublicAddress = True, ChefUserData = stub[host]['chef_data'])
          if obj.status() != "running":
            time.sleep(30) #Wait 30 seconds in between node starts
 
    def dump_db(self):
      return self.db
    
    def exit(self):
      self.db.close()
    
    def get_brokers(self):
      try:
        return self.db['customers'][self.cluster_name]['brokers']
      except:
        return []
      
    def get_host(self, host_id):
      name, customer, zone = host_id.split(".")
      if host_id in self.db['customers'][customer]['zones'][zone]['hosts']:
        return self.db['customers'][customer]['zones'][zone]['hosts'][host_id]['obj']
      else:
        raise Error("No host found with id of '%s'" % host_id)
    
    def get_hosts(self, zone = None):
      hosts = []
      if zone == None:
        zones = self.get_zones()
      else:
        zones=[zone]
      for zone in zones:
        for host in self.db['customers'][self.cluster_name]['zones'][zone]['hosts']:
          hosts.append(host)
      return sorted(hosts)
    
    def get_zones(self):
      zones = []
      for zone in self.db['customers'][self.cluster_name]['zones']:
        zones.append(zone)
      return sorted(zones)
    
    def terminate_hosts(self, zone = None):
      if zone == None:
        zones = self.get_zones()
      else:
        zones = [zone]
      for zone in zones:
        hosts = self.get_hosts(zone=zone)
        for host in hosts:
          host_obj = self.get_host(host)
          host_obj.terminate()
          del self.db['customers'][self.cluster_name]['zones'][zone]['hosts'][host_obj.name]
          for idx, broker in enumerate(self.db['customers'][self.cluster_name]['brokers']):
            if host_obj.ext_fqdn == broker:
              del self.db['customers'][self.cluster_name]['brokers'][idx]
        self.db['customers'][self.cluster_name]['zones'][zone]['brokers'] = 0
     
class Error(Exception):
  pass 
        
