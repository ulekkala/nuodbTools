'''
Created on Jan 28, 2014

@author: rkourtz
'''

import boto.route53
import nuodbaws
import inspect, json, os, random, string, sys, time

class NuoDBCluster:
    
    def __init__(self, 
                 alert_email = "alert@example.com",
                 aws_access_key = "", 
                 aws_secret = "", 
                 brokers_per_zone = 2,
                 cluster_name = "default",
                 data_dir = "/".join([os.path.dirname(os.path.abspath(inspect.stack()[-1][1])), "data"]), 
                 dns_domain="", 
                 domain_name="domain", 
                 domain_password="bird", 
                 enable_monitoring = True,
                 instance_type = "m1.large", 
                 nuodb_license = "", 
                 ssh_key = "", 
                 ssh_keyfile = None):
      self.route53 = boto.route53.connection.Route53Connection(aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret)
      args, _, _, values = inspect.getargvalues(inspect.currentframe())
      for i in args:
        setattr(self, i, values[i])
        
      if ssh_keyfile != None and ssh_keyfile != "":
        if not os.path.exists(ssh_keyfile):
          raise Error("Can not find ssh private key %s" % self.ssh_keyfile)
      if dns_domain == None or dns_domain == "None" or dns_domain == "":
        self.dns_domain = "nuoDB"
        self.dns_emulate = True
      else:
        self.dns_emulate = False
        
      self.db = {}
      self.zones = {} #store our zone connections
    
    def add_host(self, name, zone, ami = "", security_group_ids=[], subnets = [], agentPort = 48004 , subPortRange = 48005, nuodb_rpm_url = None):
      if zone not in self.zones:
        raise Error("You must connect to a zone first before you can add a host in that zone")
      if len(subnets) == 0:
        raise Error("You must specify the target subnets in an array")
      # make sure ami is valid
      valid_amis = []
      for each_ami in self.zones[zone].amis:
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
      host = ".".join([basename, self.cluster_name, zone, self.dns_domain])
      if host not in stub:
        stub[host] = {}
      # Generate data for chef... is it a broker? peers?
      agent_addr = host
      if "zones" not in self.db['customers'][self.cluster_name]:
        self.db['customers'][self.cluster_name]['zones'] = {}
      if zone not in self.db['customers'][self.cluster_name]['zones']:
        self.db['customers'][self.cluster_name]['zones'][zone] = {"brokers": []}
      if "chef_data" not in stub[host]:
        if len(self.db['customers'][self.cluster_name]['zones'][zone]['brokers']) < 1:
          isBroker = True
          chef_data = {"nuodb": {"is_broker": True, "enableAutomation": True, "enableAutomationBootstrap": True, "autoconsole": {"brokers": ["localhost"]}, "webconsole": {"brokers": ["localhost"]}}}
          #self.db['customers'][self.cluster_name]['brokers'] = [agent_addr]
          self.db['customers'][self.cluster_name]['zones'][zone]['brokers'] =[agent_addr]
        elif len(self.db['customers'][self.cluster_name]['zones'][zone]['brokers']) < int(self.brokers_per_zone):
          isBroker = True
          chef_data = {"nuodb": {"is_broker": True, "enableAutomation": False, "enableAutomationBootstrap": False, "autoconsole": {"brokers": ["localhost"]}, "webconsole": {"brokers": ["localhost"]}}}
          #self.db['customers'][self.cluster_name]['brokers'].append(agent_addr)
          self.db['customers'][self.cluster_name]['zones'][zone]['brokers'].append(agent_addr)
        else:
          isBroker = False
          chef_data = {"nuodb": {"is_broker": False, "enableAutomation": False, "enableAutomationBootstrap": False}}
        #common Chef information
        chef_data["run_list"] = ["recipe[nuodb]"] 
        chef_data['nuodb']["port"] = agentPort
        chef_data['nuodb']["portRange"] = subPortRange
        chef_data["nuodb"]['automationTemplate'] = "Minimally Redundant"
        chef_data["nuodb"]['altAddr'] = "" # Populate this at boot time
        chef_data["nuodb"]['region'] = zone
        chef_data["nuodb"]['monitoring'] = {"enable": True, "alert_email": self.alert_email}
        chef_data['nuodb']['license'] = self.nuodb_license
        chef_data["nuodb"]['domain_name'] = self.domain_name
        chef_data["nuodb"]['domain_password'] = self.domain_password
        if nuodb_rpm_url != None:
          chef_data["nuodb"]["download_url"] = nuodb_rpm_url
        stub[host]['chef_data'] = chef_data
      else:
        isBroker = stub[host]['chef_data']['nuodb']['is_broker']
      stub[host]['ami'] = ami
      stub[host]['security_group_ids'] = security_group_ids
      stub[host]['subnet'] = subnets[len(stub) % len(subnets)]
      stub[host]['obj'] = nuodbaws.Host(host, ec2Connection=self.zones[zone].connection, 
                                             Route53Connection=self.route53, dns_domain=self.dns_domain, 
                                             domain = self.domain_name, domainPassword = self.domain_password, 
                                             advertiseAlt = True, region = zone,
                                             agentPort = agentPort, portRange = subPortRange,
                                             isBroker = isBroker, ssh_key = self.ssh_key, ssh_keyfile = self.ssh_keyfile)
      return host

    def __boot_host(self, host, zone, instance_type = None, wait_for_health = False):
      if instance_type == None:
        instance_type = self.instance_type
      stub = self.db['customers'][self.cluster_name]['zones'][zone]['hosts'][host]
      template_vars = dict(
                          hostname = host,
                          chef_json = json.dumps(stub['chef_data'])
                          )
      f = open("/".join([os.path.dirname(os.path.abspath(inspect.stack()[0][1])), "templates", "init.py"]))
      template = string.Template(f.read())
      f.close()
      userdata = template.substitute(template_vars)
      obj = stub['obj'].create(ami=stub['ami'], instance_type=instance_type, security_group_ids=stub['security_group_ids'], subnet = stub['subnet'], getPublicAddress = True, userdata = userdata)
      print ("Waiting for %s to start" % obj.name),
      if obj.status() != "running":
        print("."),
        time.sleep(30) #Wait 30 seconds in between node starts
      print
      obj.update_data()
      if not self.dns_emulate:
        print "Setting DNS for %s " % obj.name
        obj.dns_set()
      if wait_for_health:
        healthy = False
        count = 0
        tries = 60
        wait = 10
        print "Waiting for agent on %s " % obj.name
        while not healthy or count == tries:
          if obj.agent_running():
            healthy = True
          else:
            print("."),
            time.sleep(wait)
          count += 1
        if not healthy:
          print "Cannot reach agent on %s after %s seconds. Check firewalls and the host for errors." % (obj.name, str(tries * wait))
          exit(1)
        print
      else:
        print "Not waiting for agent on %s, node will come up asynchronously." % obj.name
      return obj
             
    def connect_zone(self, zone):
      self.zones[zone] = nuodbaws.NuoDBzone(zone)
      self.zones[zone].connect(aws_access_key=self.aws_access_key, aws_secret=self.aws_secret)
      if "customers" not in self.db:
        self.db['customers'] = {}
      if self.cluster_name not in self.db['customers']:
        self.db['customers'][self.cluster_name] = {"zones": {}, "brokers": []}
      if zone not in self.db['customers'][self.cluster_name]['zones']:
        self.db['customers'][self.cluster_name]['zones'][zone] = {"hosts": {}, "brokers": []}
        
    def create_cluster(self):
      for host in self.get_hosts():
        obj = self.get_host(host)
        zone = obj.region
        wait_for_health = False
        if obj.isBroker == True:
          # If this node is a broker, then pair it with brokers outside its region if you can
          wait_for_health = True
          brokers = []
          for idx, azone in enumerate(self.get_zones()):
            if azone != zone:
              for broker in self.db['customers'][self.cluster_name]['zones'][azone]['brokers']:
                brokers.append(broker)
          if len(brokers) == 0:
          # There are no other brokers in other regions found. Add another peer in this region if there is one
              brokers = self.db['customers'][self.cluster_name]['zones'][zone]['brokers']
        else:
          #If this node isn't a broker pair it with local zone brokers
          brokers = self.db['customers'][self.cluster_name]['zones'][zone]['brokers']
        print "%s: Setting peers to [%s]" % (host, ",".join(brokers))
        self.db['customers'][self.cluster_name]['zones'][zone]['hosts'][host]['chef_data']['nuodb']['brokers'] = brokers
        self.__boot_host(host, zone, wait_for_health = wait_for_health)
      if self.dns_emulate:
        self.set_dns_emulation()

      
    def delete_db(self):
      self.exit()
      if os.path.exists(self.database_file):
        os.remove(self.database_file)
    
    def delete_dns(self, zone = None):
      if zone == None:
        zones = self.get_zones()
      else:
        zones = [zone]
      for zone in zones:
        hosts = self.get_hosts(zone=zone)
        for host in hosts:
          host_obj = self.get_host(host)
          host_obj.dns_delete()
      
    def dump_db(self):
      return self.db
    
    def get_brokers(self):
      try:
        brokers = []
        for zone in self.get_zones():
          for broker in self.db['customers'][self.cluster_name]['zones'][zone]['brokers']:
            brokers.append(broker)
        return brokers
      except:
        return []
    
    def get_host(self, host_id):
      split= host_id.split(".")
      customer = split[1]
      zone = split[2]
      if host_id in self.db['customers'][customer]['zones'][zone]['hosts']:
        return self.db['customers'][customer]['zones'][zone]['hosts'][host_id]['obj']
      else:
        raise Error("No host found with id of '%s'" % host_id)
    
    def get_host_address(self, host_id):
      split= host_id.split(".")
      customer = split[1]
      zone = split[2]
      if host_id in self.db['customers'][customer]['zones'][zone]['hosts']:
        if self.dns_emulate:
          return self.db['customers'][customer]['zones'][zone]['hosts'][host_id]['obj'].ext_ip
        else:
          return self.db['customers'][customer]['zones'][zone]['hosts'][host_id]['obj'].name
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
    
    def set_dns_emulation(self):
      host_list = []
      for host_id in self.get_hosts():
        host = self.get_host(host_id)
        host.update_data()
        print("Waiting for an IP for %s" % host.name),
        while len(host.ext_ip) == 0:
          print ("."),
          time.sleep(5)
          host.update_data()
        print("got %s" % host.ext_ip)
        host_list.append([host.name, host.ext_ip])
      for host_id in self.get_hosts():
        host = self.get_host(host_id)
        print ("Waiting for ssh on %s." % host.name),
        while not host.is_port_available(22):
          print ("."),
          time.sleep(5)
        print
        for line in host_list:
          hostname = line[0]
          ip = line[1]
          command = "sudo awk -v s=\"%s    %s\" '/%s/{f=1;$0=s}7;END{if(!f)print s}' /etc/hosts > /tmp/hosts && sudo chown root:root /tmp/hosts && sudo chmod 644 /tmp/hosts && sudo mv /tmp/hosts /etc/hosts" % (ip, hostname, hostname)
          (rc, stdout, stderr) = host.ssh_execute(command)
          if rc != 0:
            print "Unable to set DNS emulation for %s: %s" % (host.name, stderr)
        host.agent_action(action = "restart")
        host.webconsole_action(action = "restart")
      
    def terminate_hosts(self, zone = None):
      if zone == None:
        zones = self.get_zones()
      else:
        zones = [zone]
      for zone in zones:
        hosts = self.get_hosts(zone=zone)
        for host in hosts:
          host_obj = self.get_host(host)
          if host_obj.exists:
            print "Terminating %s" % host
            host_obj.terminate()
            del self.db['customers'][self.cluster_name]['zones'][zone]['hosts'][host_obj.name]
            for idx, broker in enumerate(self.db['customers'][self.cluster_name]['brokers']):
              if zone in broker:
                del self.db['customers'][self.cluster_name]['brokers'][idx]
     
class Error(Exception):
  pass 
        
