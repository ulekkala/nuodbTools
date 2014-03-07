#!/usr/bin/python

import nuodbTools.cluster
import json
import os
import sys
import time
import urllib2

def user_prompt(prompt, valid_choices = [], default = None):
  if default != None:
    prompt = "%s [%s] " % (prompt, str(default))
  val = raw_input(prompt)
  if len(valid_choices) == 0:
    if default == None:
      return val
    else:
      return default
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
    #print "%s)  %s %s" % (i+1, params[i], suggest_prompt)
    print '{:2d}) {:25} {}'.format(i+1, params[i], suggest_prompt)
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
  print "What type of instance do you want to use?"
  url = "https://raw2.github.com/garnaat/missingcloud/master/aws.json"
  obj = json.loads(urllib2.urlopen(url).read())
  instance_types = sorted(obj['services']['Elastic Compute Cloud']['instance_types'].keys())
  suggested = None
  for idx, itype in enumerate(instance_types):
    if itype == "m1.xlarge":
      suggested = idx
  result = choose_from_list(instance_types, suggested)
  return instance_types[result]
  
def get_zone_info(c):
  # Find our how many regions
  r = {}
  zone_count = user_prompt("How many AWS regions? (1-7)? ", range(1,8))
  # open a Boto connection to get metadata
  aws_conn = nuodbTools.aws.Zone("us-east-1").connect(c["aws_access_key"], c["aws_secret"])
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
  # amazon has a ton of amis named the same thing. Choose the latest one. Only reliable way I can find is to scrape their wiki. Cache this.
  page_cache = urllib2.urlopen("http://aws.amazon.com/amazon-linux-ami/").read()
  for region in r:
    # Server count 
    r[region]["servers"] = user_prompt(region + " --- How many servers? (1-20) ", range(1,20))
    zone_obj = nuodbTools.aws.Zone(region)
    zone_conn = zone_obj.connect(c["aws_access_key"], c["aws_secret"])
    
    # Validate SSH Key
    
    keypairs = zone_conn.get_all_key_pairs()
    key_exists = False
    for keypair in keypairs:
      if c['ssh_key'] == keypair.name:
        key_exists = True
    if not key_exists:
      print "Key %s does not exist in region %s. Please fix this and rerun this script" % (c['ssh_key'], region)
      exit(2)
    
    # Choose AMI
    print
    print region + " --- Choose the AMI (Loading...) "
    amis = zone_obj.amis
    ami_dict = {}
    suggested = None
   
    for ami in amis:
      if ami.architecture == "x86_64" and ami.description != None and len(ami.description) > 0 and "ami-" in ami.id and ami.platform != "windows":
        if ami.owner_alias == "amazon" and ami.id in page_cache:
          ami_dict["  ".join([ami.id, ami.description])] = {"id": ami.id, "location": ami.location}
        elif ami.owner_alias != "amazon": 
          ami_dict["  ".join([ami.id, ami.description])] = {"id": ami.id, "location": ami.location}
    ami_descriptions = sorted(ami_dict.keys()) 
    ami_descriptions.append("NONE OF THE ABOVE")
    for idx, desc in enumerate(ami_descriptions):
      if "Amazon Linux AMI x86_64 PV EBS" in desc:
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
    print
    print region + " --- Choose the subnets: "
    subnets = zone_obj.get_subnets()
    subnet_descs = []
    subnet_ids = []
    for key in sorted(subnets.keys()):
      subnet_descs.append("{:10}\t{:12}\t{:15}\t{}".format(subnets[key]['availability_zone'], subnets[key]['vpc_id'], subnets[key]['private_ip_address'], subnets[key]['description']))
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
    print
    print region + " --- Choose the security groups: "
    print region + " --- YOU MUST CHOOSE AT LEAST ONE SECURITY GROUP WITH SSH OPEN TO YOUR CURRENT LOCATION"
    r[region]['security_group_ids'] = []
    security_groups = zone_obj.get_security_groups()
    default_group_exists = False
    for group in security_groups:
      if group.name == "NuoDB_default_ports":
        default_group_exists = True
    if not default_group_exists:
      res = user_prompt("Do you want to create a default security group for this zone? It would open the default NuoDB ports to the world. (y/n)", ["y", "n"], "n")
      if res =="y":
        zone_obj.edit_security_group("NuoDB_default_ports", "These are the default NuoDB ports, open to the world. Autogenerated by nuodb.py", [{"protocol": "tcp", "from_port": 48004, "to_port": 48020, "cidr_ip": "0.0.0.0/0"}, {"protocol": "tcp", "from_port": 8888, "to_port": 8889, "cidr_ip": "0.0.0.0/0"}, {"protocol": "tcp", "from_port": 8080, "to_port": 8080, "cidr_ip": "0.0.0.0/0"}])
        security_groups = zone_obj.get_security_groups()
    sg_descs = []
    sg_ids = []
    for group in security_groups:
      if group.vpc_id in r[region]['vpcs']:
        sg_descs.append("{:20}    {}".format(group.name, group.description))
        sg_ids.append(group.id)
    sg_choices = choose_multiple_from_list(sg_descs)
    for choice in sg_choices:
      r[region]['security_group_ids'].append(sg_ids[choice])
        
  return r 

#### Create a cluster

def help():
  print "%s create" % sys.argv[0]
  print "%s terminate" % sys.argv[0]
  
def __main__(action = None):
  config_file = "./config.json"
  params = {
            "cluster_name": { "default" : "mycluster", "prompt" : "What is the name of your cluster?"},
            "aws_access_key": {"default" : "", "prompt" : "What is your AWS access key?"},
            "aws_secret": {"default" : "", "prompt" : "What is your AWS secret?"},
            "dns_domain": {"default" : "None", "prompt" : "Enter a Route53 domain under your account. If you don't have one enter \"None\":"},
            "domain_name": {"default": "domain", "prompt": "What is the name of your NuoDB domain?"},
            "domain_password": {"default": "bird", "prompt": "What is the admin password of your NuoDB domain?"},
            "license": {"default": "", "prompt": "Please enter your NuoDB license- or leave empty for development version:"},
            "ssh_key": {"default": "", "prompt": "Enter your ssh keypair name that exists in all the regions you want to start instances:"},
            "ssh_keyfile": {"default": "/home/USER/.ssh/id_rsa", "prompt": "Enter the location of the private key used for ssh. Please use the absolute path: "},
            "alert_email" : {"default" : "","prompt" : "What email address would you like health alerts sent to?"},
            "brokers_per_zone": {"default" : 2, "prompt": "How many brokers do you want in each region?"},
            "custom_rpm" : {"default" : "", "prompt": "Use alternative installation package? Empty for default: "}
          }
  if action == "create":
    #### Gather all the data we need
    c = {}
    if os.path.exists(config_file):
      with open(config_file) as f:
        static_config = json.loads(f.read())
        f.close()
    else:
      static_config = {}
      
    for key in static_config:
      if key in params:
        params[key]['default'] = static_config[key]
    
    for key in sorted(params.keys()):
      if len(str(params[key]['default'])) > 30:
        default = str(params[key]['default'])[0:27] + "..."
      else:
        default = str(params[key]['default'])
      val = raw_input("%s [%s] " % (params[key]['prompt'], default))
      if len(val) == 0:
        c[key] = params[key]['default']
      else:
        c[key] = val
        
    #### test for ssh key
    if not os.path.exists(c['ssh_keyfile']):
      print "Cannot find ssh private key %s. Please check and run again." % c['ssh_keyfile']
      exit(2)

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
        print "{}    {:12}    {}    {}    {}".format(zone, s["ami"], str(s["servers"]) + " servers", ",".join(s["subnets"]), ",".join(s["security_group_ids"]))
      res = user_prompt("Use this configuration? (y/n) ", ["y", "n"])
      if res == "y":
        c['zones'] = static_config["zones"]
      else:
        while res != "y":
          c["zones"] = get_zone_info(c)
          for zone in sorted(c["zones"].keys()):
            s = c["zones"][zone]
            print "{}    {:12}    {}    {}    {}".format(zone, s["ami"], str(s["servers"]) + " servers", ",".join(s["subnets"]), ",".join(s["security_group_ids"]))
          res = user_prompt("Use this configuration? (y/n) ", ["y", "n"])
    else:
      res = "n"
      while res != "y":
        c["zones"] = get_zone_info(c)
        print "Here is your zone info:"
        for zone in sorted(c["zones"].keys()):
          s = c["zones"][zone]
          print "{}    {:12}    {}    {}    {}".format(zone, s["ami"], str(s["servers"]) + " servers", ",".join(s["subnets"]), ",".join(s["security_group_ids"]))
        res = user_prompt("Use this configuration? (y/n) ", ["y", "n"])
      
    # Write out the config
    with open(config_file, 'wt') as f:
      f.write(json.dumps(c, indent=4, sort_keys=True))
    
    #######################################
    #### Actually do some work
    #######################################
    
    mycluster =  nuodbTools.cluster.Cluster(
                                           alert_email = c['alert_email'], ssh_key = c['ssh_key'], ssh_keyfile = c['ssh_keyfile'],
                                           aws_access_key = c['aws_access_key'], aws_secret = c['aws_secret'], 
                                           brokers_per_zone = c['brokers_per_zone'], cluster_name = c['cluster_name'],
                                           dns_domain = c['dns_domain'], domain_name = c['domain_name'],
                                           domain_password = c['domain_password'], instance_type = c['instance_type'], 
                                           nuodb_license = c['license'])
    print "Creating the cluster."
    for zone in c['zones']:
      mycluster.connect_zone(zone)
      z = c['zones'][zone]
      for i in range(0,z['servers']):
        root_name = "db" + str(i)
        myserver = mycluster.add_host(name=root_name, zone=zone, ami=z['ami'], subnets=z['subnets'], security_group_ids = z['security_group_ids'], nuodb_rpm_url = c['custom_rpm']) # Mark the number of nodes to be created
        print "Added %s" % myserver
    
    print "Booting the cluster"
    mycluster.create_cluster() # Actually spins up the nodes.
    print "Cluster has started up. Here are your brokers:"
    for broker in mycluster.get_brokers():
      print broker
    print
    hosts = mycluster.get_hosts()
    
    print("Waiting for an available web console")
    healthy = False
    i=0
    wait = 600 #seconds
    good_host = None
    while i < wait:
      if not healthy:
        for host_id in hosts:
          obj = mycluster.get_host(host_id)
          host = mycluster.get_host_address(host_id)
          url = "http://%s:%s" % (host, obj.web_console_port)
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
      print "Other nodes may still be booting and will join the cluster eventually."
    
  ########################
  #### Terminate a cluster
  ########################
  elif action == "terminate":
    if os.path.exists(config_file):
      with open(config_file) as f:
        c = json.loads(f.read())
        f.close()
      mycluster =  nuodbTools.cluster.Cluster(
                                             alert_email = c['alert_email'], ssh_key = c['ssh_key'], ssh_keyfile = c['ssh_keyfile'],
                                             aws_access_key = c['aws_access_key'], aws_secret = c['aws_secret'], 
                                             brokers_per_zone = c['brokers_per_zone'], cluster_name = c['cluster_name'],
                                             dns_domain = c['dns_domain'], domain_name = c['domain_name'],
                                             domain_password = c['domain_password'], instance_type = c['instance_type'], 
                                             nuodb_license = c['license'])
      
      for zone in c['zones']:
        mycluster.connect_zone(zone)
        z = c['zones'][zone]
        for i in range(0,z['servers']):
          root_name = "db" + str(i)
          myserver = mycluster.add_host(name=root_name, zone=zone, ami=z['ami'], subnets=z['subnets'], security_group_ids = z['security_group_ids'], nuodb_rpm_url = c['custom_rpm']) # Mark the number of nodes to be created
      mycluster.terminate_hosts()
      if not mycluster.dns_emulate:
        res = user_prompt("Delete DNS records too? Do not do this if you will be restarting the cluster soon. (y/n): ", ["y","n"])
        if res == "y":
          mycluster.delete_dns()
    else:
      print "Can't find a previous config file to auto-terminate. If you can't find the file then you will have to destroy the cluster by hand."
      exit(2)
  else:
    help()

args = sys.argv
if len(args) < 2:
  res = user_prompt("What action do you want to take on the cluster? (create/terminate): ", ["create", "terminate"])
  __main__(action=res)
else:
  __main__(action=args[1])