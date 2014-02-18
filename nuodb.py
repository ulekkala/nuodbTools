#!/usr/bin/python

import nuodbaws
import nuodbcluster
import json
import os
import time
import urllib2

config_file = "./config.json"
params = {
            "action" : {
                        "default": "C",
                        "prompt": "What action do you want to perform? (C)reate a cluster or (T)erminate one?"
                        },
            "cluster_name": {
                              "default" : "mycluster",
                              "prompt" : "What is the name of your cluster?"
                              },
            "aws_access_key": {
                                "default" : "",
                                "prompt" : "What is your AWS access key?"
                                },
            "aws_secret": {
                            "default" : "",
                            "prompt" : "What is your AWS secret?"
                            },
            "dns_domain": {
                           "default" : "myroute53domain.net",
                           "prompt" : "Enter a Route53 domain under your account: "
                           },
            "domain_name": {
                          "default": "domain",
                          "prompt": "What is the name of your NuoDB domain?"
                          },
            "domain_password": {
                          "default": "password",
                          "prompt": "What is the admin password of your NuoDB domain?"
                          },
            "license": {
                          "default": "",
                          "prompt": "Please enter your NuoDB license- or leave empty for development version:"
                         },
            "ssh_key": {
                          "default": "",
                          "prompt": "Enter your ssh keypair name that exists in all the regions you want to start instances:"
                         },
            "alert_email" : {
                           "default" : "",
                           "prompt" : "What email address would you like health alerts sent to?"
                           },
            "brokers_per_zone": {
                                 "default" : 2,
                                 "prompt": "How many brokers do you want in each region?"
                                 }
          }
rpm = None


################################
#### Gather all the data we need
################################

def user_prompt(prompt, valid_choices = []):
  val = raw_input(prompt)
  if len(valid_choices) == 0:
    return val
  for choice in valid_choices:
    if val == str(choice):
      return choice
  valid_strings = []
  #Handle integer inputs
  for choice in valid_choices:
    valid_strings.append(str(choice))
  print "Invalid choice. Your choices are: [" + ",".join(valid_strings) + "]"
  return user_prompt(prompt, valid_choices)
  
def choose_from_list(params = [], suggested = None):
  # returns index of the list you gave me
  i = 0
  options = []
  while i < len(params):
    if suggested != None and suggested == i:
      suggest_prompt = "<----- SUGGESTED"
    else:
      suggest_prompt = ""
    print "%s)  %s %s" % (i+1, params[i], suggest_prompt)
    i += 1
    options.append(i)
  return user_prompt("Choose one:", options) - 1

def choose_multiple_from_list(params = []):
  # returns list of indicies from parameters sent
  tally = []
  while True:
    list_to_send = []
    for idx, param in enumerate(params):
      if idx not in tally:
        list_to_send.append(param)
    if len(list_to_send) == 0:
      return tally
    else:
      list_to_send.append("DONE CHOOSING")
      result = choose_from_list(list_to_send)
      if result == len(list_to_send) - 1:
        return tally
      else:
        choice = list_to_send[result]
        for idx, param in enumerate(params):
          if choice == param:
            tally.append(idx)

def get_instance_type():
  url = "https://raw2.github.com/garnaat/missingcloud/master/aws.json"
  obj = json.loads(urllib2.urlopen(url).read())
  instance_types = sorted(obj['services']['Elastic Compute Cloud']['instance_types'].keys())
  suggested = None
  for idx, type in enumerate(instance_types):
    if type == "m1.xlarge":
      suggested = idx
  result = choose_from_list(instance_types, suggested)
  return instance_types[result]
  
def get_zone_info(c):
  # Find our how many regions
  r = {}
  zone_count = user_prompt("How many AWS regions? (1-7)? ", range(1,8))
  # open a Boto connection to get metadata
  aws_conn = nuodbaws.NuoDBzone("us-east-1").connect(c["aws_access_key"], c["aws_secret"])
  available_zones = aws_conn.get_all_regions()
  if zone_count == "7":
    for zone in available_zones:
      r[zone] = {}
  else:
    i = 0
    while i < int(zone_count):
      regionlist = []
      for zone_obj in available_zones:
        zone = zone_obj.name
        if zone not in r:
          regionlist.append(zone)
      get = int(choose_from_list(regionlist))
      r[regionlist[get]] = {}
      i += 1
  for region in r:
    
    # Server count 
    r[region]["servers"] = user_prompt(region + " --- How many servers? (1-20) ", range(1,20))
    zone_obj = nuodbaws.NuoDBzone(region)
    zone_obj.connect(c["aws_access_key"], c["aws_secret"])
    
    # Choose AMI
    
    print region + " --- Choose the AMI (Loading...) "
    amis = zone_obj.get_amis()
    ami_dict = {}
    suggested = None
    for ami in amis:
      if ami.architecture == "x86_64" and ami.description != None and "ami-" in ami.id and ami.platform != "windows":
        description = ami.description
        # amazon has a ton of amis named the same thing. Choose the latest one.
        if description not in ami_dict:
          ami_dict[description] = {"id": ami.id, "location": ami.location}
        elif ami.location > ami_dict[description]['location']:  
          ami_dict[description]['id'] = ami.id
    ami_descriptions = sorted(ami_dict.keys()) 
    ami_descriptions.append("NONE OF THE ABOVE")
    for idx, desc in enumerate(ami_descriptions):
      if desc == "Amazon Linux AMI x86_64 EBS":
        suggested = idx
    ami_choice = choose_from_list(ami_descriptions, suggested)
    if ami_choice == len(ami_descriptions) - 1:
      ami_enter = ""
      while "ami-" not in ami_enter:
        ami_enter = user_prompt("Enter the AMI you want to use (ami-xxxxxxxx): ")
      r[region]["ami"] = ami_enter
    else:
      r[region]["ami"] =  ami_dict[ami_descriptions[ami_choice]]['id']
    
    #What subnets to use?
    
    print region + " --- Choose the subnets: "
    subnets = zone_obj.get_subnets()
    subnet_descs = []
    subnet_ids = []
    for key in sorted(subnets.keys()):
      subnet_descs.append("\t".join([subnets[key]['availability_zone'], subnets[key]['vpc_id'], subnets[key]['private_ip_address'], subnets[key]['description']]))
      subnet_ids.append(subnets[key]['subnet_id'])
    subnet_choices = choose_multiple_from_list(subnet_descs) 
    r[region]['subnets'] = []
    r[region]['vpcs'] = []
    for choice in subnet_choices:
      r[region]['subnets'].append(subnet_ids[choice])
      vpc = subnets[subnet_ids[choice]]['vpc_id']
      if vpc not in r[region]['vpcs']:
        r[region]['vpcs'].append(vpc)
    if len(subnet_choices) == 0:
      print "--- YOU MUST CHOOSE AT LEAST ONE SUBNET"
      exit()
    
    #What security groups to use?
    
    r[region]['security_group_ids'] = []
    security_groups = zone_obj.get_security_groups()
    sg_descs = []
    sg_ids = []
    for group in security_groups:
      if group.vpc_id in r[region]['vpcs']:
        sg_descs.append("\t".join([group.name, group.description]))
        sg_ids.append(group.id)
    sg_choices = choose_multiple_from_list(sg_descs)
    for choice in sg_choices:
      r[region]['security_group_ids'].append(sg_ids[choice])
        
  return r 

c = {}
with open(config_file) as f:
  static_config = json.loads(f.read())
  f.close()
for key in static_config:
  if key in params:
    params[key]['default'] = static_config[key]

for key in sorted(params.keys()):
  if len(str(params[key]['default'])) > 20:
    default = str(params[key]['default'])[0:17] + "..."
  else:
    default = str(params[key]['default'])
  val = raw_input("%s [%s] " % (params[key]['prompt'], default))
  if len(val) == 0:
    c[key] = params[key]['default']
  else:
    c[key] = val
    
#### Get Instance type
if "instance_type" not in static_config:
  c['instance_type'] = get_instance_type()
else:
  res = user_prompt("Use the instance type of %s? (y/n) " % static_config['instance_type'], ["y", "n"])
  if res != "y":
    c['instance_type'] = get_instance_type()
  else:
    c['instance_type'] = static_config['instance_type']

### Populate zone data

if "zones" in static_config:
  print "Found this zone info:"
  for zone in sorted(static_config["zones"].keys()):
    s = static_config["zones"][zone]
    print "%s\t%s\t%s\t%s\t%s" % (zone, s["ami"], str(s["servers"]) + " servers", ",".join(s["subnets"]), ",".join(s["security_group_ids"]))
  res = user_prompt("Use this configuration? (y/n) ", ["y", "n"])
  if res != "y":
    c["zones"] = get_zone_info(c)
  else:
    c['zones'] = static_config["zones"]
else:
  res = "n"
  while res != "y":
    c["zones"] = get_zone_info(c)
    print "Here is your zone info:"
    for zone in sorted(c["zones"].keys()):
      s = c["zones"][zone]
      print "%s\t%s\t%s\t%s\t%s" % (zone, s["ami"], str(s["servers"]) + " servers", ",".join(s["subnets"]), ",".join(s["security_group_ids"]))
    res = user_prompt("Use this configuration? (y/n) ", ["y", "n"])
  
# Write out the config
if os.path.exists(config_file):
  newfile = ".".join([config_file, "backup", str(int(time.time()))])
  print "Backing up old config %s file to %s" % (config_file, newfile)
  os.rename(config_file, newfile)
with open(config_file, 'wt') as f:
  f.write(json.dumps(c, indent=4, sort_keys=True))

#######################################
#### Actually do some work
#######################################

mycluster =  nuodbcluster.NuoDBCluster(
                                       alert_email = c['alert_email'], ssh_key = c['ssh_key'],
                                       aws_access_key = c['aws_access_key'], aws_secret = c['aws_secret'], 
                                       brokers_per_zone = c['brokers_per_zone'], cluster_name = c['cluster_name'],
                                       dns_domain = c['dns_domain'], domain_name = c['domain_name'],
                                       domain_password = c['domain_password'], instance_type = c['instance_type'], 
                                       nuodb_license = c['license'])
#### Create a cluster
if c['action'] == "C":
  print "Creating the cluster."
  for zone in c['zones']:
    mycluster.connect_zone(zone)
    z = c['zones'][zone]
    for i in range(0,z['servers']):
      root_name = "db" + str(i)
      myserver = mycluster.add_host(name=root_name, zone=zone, ami=z['ami'], subnets=z['subnets'], security_group_ids = z['security_group_ids'], nuodb_rpm_url = rpm) # Mark the number of nodes to be created
      print "Added %s" % myserver
  
  print "Booting the cluster"
  
  mycluster.create_cluster() # Actually spins up the nodes.
  print "Cluster has started up. Here are your brokers:"
  for broker in mycluster.get_brokers():
    print broker
  print
  print("Waiting for an available web console")
  healthy = False
  i=0
  wait = 600 #seconds
  good_host = None
  while i < wait:
    if not healthy:
      for host in mycluster.get_brokers():
        url = "http://%s:8888" % host
        if not healthy:
          try:
            urllib2.urlopen(url, None, 2)
            good_host = url
            healthy = True
          except:
            pass
      time.sleep(1)
    i += 1
  if not healthy:
    print "Gave up trying after %s seconds. Check the server" % str(wait)
  else:
    print "You can now access the console at %s " % str(good_host)
    
#### Terminate a cluster
elif c['action'] == "T":
  mycluster.terminate_hosts()
  mycluster.delete_db()
else:
  print "Invalid command %s for a nuodb cluster. Please refer to documentation at %s" % (c['action'], "someurltobenamed.com")
mycluster.exit()