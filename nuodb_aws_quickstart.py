#!/usr/bin/python

description = """
NuoDB AWS cluster quickstart\n
============================\n
This script creates a multiregion sandbox cluster of a given number of nodes in AWS EC2.
It is intended for creating a testing platform.
"""

import argparse
import nuodbTools.aws
import nuodbTools.cluster
import json
import os
import re
import sys
import time
import unicodedata
import urllib2

def user_prompt(prompt, valid_choices=[], default=None):
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
  # Handle integer inputs
  for choice in valid_choices:
    valid_strings.append(str(choice))
  print "Invalid choice. Your choices are: [" + ",".join(valid_strings) + "]"
  return user_prompt(prompt, valid_choices)
  
def choose_from_list(params=[], suggested=None):
  # returns index of the list you gave me
  i = 0
  options = []
  while i < len(params):
    if suggested != None and suggested == i:
      suggest_prompt = "<----- SUGGESTED"
    else:
      suggest_prompt = ""
    # print "%s)  %s %s" % (i+1, params[i], suggest_prompt)
    print '{:2d}) {:25} {}'.format(i + 1, params[i], suggest_prompt)
    i += 1
    options.append(i)
  return user_prompt("Choose one:", options) - 1

def choose_multiple_from_list(params=[]):
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
  print "What type of instance do you want to use? (Loading...)"
  url = "https://raw2.github.com/garnaat/missingcloud/master/aws.json"
  obj = json.loads(urllib2.urlopen(url).read())
  instance_types = sorted(obj['services']['Elastic Compute Cloud']['instance_types'].keys())
  filtered_instance_types = []
  for t in instance_types:
    if t[0] == "m" or t[0] == "t":
      filtered_instance_types.append(t)
  suggested = None
  for idx, itype in enumerate(filtered_instance_types):
    if itype == "m3.xlarge":
      suggested = idx
  result = choose_from_list(filtered_instance_types, suggested)
  return filtered_instance_types[result]
  
def get_zone_info(c):
  # Find our how many regions
  r = {}
  
  # open a Boto connection to get metadata
  aws_conn = nuodbTools.aws.Zone("us-east-1").connect(c["aws_access_key"], c["aws_secret"])
  available_zones = aws_conn.get_all_regions()
  if len(c['license']) != 0:
    # No license, limited to 2 nodes. Limit customer to one region.
    zone_count = user_prompt("How many AWS regions? (1-%s)? " % len(available_zones), range(1, len(available_zones) + 1))
  else:
    zone_count = 1
    print "Choose your region:"
  
  if zone_count == len(available_zones):
    for zone in available_zones:
      r[zone.name] = {}
  else:
    i = 0
    while i < int(zone_count):
      regionlist = []
      for zone_obj in available_zones:
        zone = zone_obj.name
        if zone not in r:
          regionlist.append(zone)
      get = int(choose_from_list(sorted(regionlist)))
      r[sorted(regionlist)[get]] = {}
      i += 1
  # amazon has a ton of amis named the same thing. Choose the latest one. Only reliable way I can find is to scrape their wiki. Cache this.
  page_cache = unicodedata.normalize("NFKD", unicode(urllib2.urlopen("http://aws.amazon.com/amazon-linux-ami/").read(), "utf-8"))
  
  # Region specific choices
  for region in r:
    # Server count 
    r[region]["servers"] = user_prompt(region + " --- How many servers? (1-20) ", range(1, 20))
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
    
    print
    # Choose AMI
    print region + " --- Choose the AMI (Loading...) "
    amis = zone_obj.amis
    ami_dict = {}
    suggested = None
    
    for ami in amis:
      if ami.architecture == "x86_64" and ami.description != None and len(ami.description) > 0 and "ami-" in ami.id and ami.platform != "windows":
        if ami.owner_alias != None and ami.owner_alias.encode('utf-8') == u"amazon" and ami.id in page_cache:
          ami_dict["  ".join([ami.id.encode('utf-8'), ami.name.encode('utf-8')])] = {"id": ami.id, "location": ami.location, "name": ami.name}
        elif ami.owner_alias != None and ami.owner_alias.encode('utf8') != u"amazon": 
          ami_dict["  ".join([ami.id.encode('utf-8'), ami.name.encode('utf-8')])] = {"id": ami.id, "location": ami.location, "name": ami.name}
        elif ami.owner_id == u'802164393885' and "Quickstart" in ami.name.encode('utf-8'): 
          ami_dict["  ".join([ami.id.encode('utf-8'), ami.name.encode('utf-8')])] = {"id": ami.id, "location": ami.location, "name": ami.name}
    ami_descriptions = sorted(ami_dict.keys()) 
    ami_descriptions.append("NONE OF THE ABOVE")
    for idx, desc in enumerate(ami_descriptions):
      if "NuoDB" in desc and "Quickstart" in desc:
        suggested = idx
    ami_choice = choose_from_list(ami_descriptions, suggested)
    if ami_choice == len(ami_descriptions) - 1:
      ami_enter = ""
      while "ami-" not in ami_enter:
        ami_enter = user_prompt("Enter the AMI you want to use (ami-xxxxxxxx): ")
      r[region]["ami"] = ami_enter
    else:
      r[region]["ami"] = ami_dict[ami_descriptions[ami_choice]]['id']
    
    
    # What subnets to use?
    print
    print region + " --- Choose the subnets: "
    subnets = zone_obj.get_subnets()
    subnet_descs = []
    subnet_ids = []
    for key in sorted(subnets.keys()):
      subnet_descs.append("{:10}\t{:12}\t{:15}".format(subnets[key]['availability_zone'], subnets[key]['vpc_id'], subnets[key]['cidr_block']))
      subnet_ids.append(key)
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
    
    # What security groups to use?
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
      res = user_prompt("Do you want to create a default security group for this zone? It would open the default NuoDB ports to the world and SSH from this machine. (y/n)", ["y", "n"])
      if res == "y":
        my_public_ip = urllib2.urlopen('http://checkip.dyndns.org').read().strip().split("Current IP Address: ")[1].replace("</body></html>", "").strip()
        zone_obj.edit_security_group("NuoDB_default_ports", "These are the default NuoDB ports, open to the world. Autogenerated by nuodb_aws_quickstart.py", [{"protocol": "tcp", "from_port": 48004, "to_port": 48020, "cidr_ip": "0.0.0.0/0"}, {"protocol": "tcp", "from_port": 8888, "to_port": 8889, "cidr_ip": "0.0.0.0/0"}, {"protocol": "tcp", "from_port": 8080, "to_port": 8080, "cidr_ip": "0.0.0.0/0"}, {"protocol": "tcp", "from_port": 22, "to_port": 22, "cidr_ip": "%s/32" % my_public_ip}], vpc_id="all")
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

def get_zone_info_automatic(c):
  r= {}
  # open a Boto connection to get metadata
  aws_conn = nuodbTools.aws.Zone("us-east-1").connect(c["aws_access_key"], c["aws_secret"])
  available_zones = aws_conn.get_all_regions()
  if len(c['license']) != 0:
    # No license, limited to 2 nodes. Limit customer to one region.
    zone_count = user_prompt("How many AWS regions? (1-%s)? " % len(available_zones), range(1, len(available_zones) + 1))
  else:
    zone_count = 1
    print "Choose your region:"

  if zone_count == len(available_zones):
    for zone in available_zones:
      r[zone.name] = {}
  else:
    i = 0
    while i < int(zone_count):
      regionlist = []
      for zone_obj in available_zones:
        zone = zone_obj.name
        if zone not in r:
          regionlist.append(zone)
      get = int(choose_from_list(sorted(regionlist)))
      r[sorted(regionlist)[get]] = {}
      i += 1
  # amazon has a ton of amis named the same thing. Choose the latest one. Only reliable way I can find is to scrape their wiki. Cache this.
  page_cache = unicodedata.normalize("NFKD", unicode(urllib2.urlopen("http://aws.amazon.com/amazon-linux-ami/").read(), "utf-8"))
  
  for region in r:
    zone_obj = nuodbTools.aws.Zone(region)
    zone_conn = zone_obj.connect(c["aws_access_key"], c["aws_secret"])
    keypairs = zone_conn.get_all_key_pairs()
    key_exists = False
    for keypair in keypairs:
      if c['ssh_key'] == keypair.name:
        key_exists = True
    if not key_exists:
      print "Key %s does not exist in region %s. Please fix this and rerun this script" % (c['ssh_key'], region)
      exit(2)
      
    #set servers
    r[region]["servers"] = 2
    
    amis = zone_obj.amis
    for ami in amis:
      if ami.owner_id == u'802164393885' and "Quickstart" in ami.name.encode('utf-8') and ami.architecture == "x86_64" and "ami-" in ami.id and ami.platform != "windows":
        r[region]["ami"] = ami.id
    # Couldn't find a quickstart ami, use amazon base
    if "ami" not in r[region]:
      for ami in amis:
        if ami.owner_alias != None and ami.owner_alias.encode('utf-8') == u"amazon" and ami.id in page_cache and "amzn-ami-pv" in ami.name and "ebs" in ami.name and ami.architecture == "x86_64" and ami.platform != "windows":
          r[region]["ami"] = ami.id
    print "%s: Using %s" % (region, r[region]['ami'])
    
    subnets = zone_obj.get_subnets()
    for subnet in subnets:
      found_subnet = False
      if subnets[subnet]['state'] == 'available' and subnets[subnet]['defaultForAz'] and not found_subnet: 
        r[region]['subnets'] = [subnets[subnet]['id']]
        r[region]['vpcs'] = [subnets[subnet]['vpc_id']]
    if "subnets" not in r[region]:
      r[region]['subnets'] = [None]
      r[region]['vpcs'] = [None]
    else:
      print "%s: Using %s" % (region, ",".join(r[region]['subnets']))
    
    security_groups = zone_obj.get_security_groups()
    default_group_exists = False
    for group in security_groups:
      if group.name == "NuoDB_default_ports" and group.vpc_id in r[region]['vpcs']:
        r[region]['security_group_ids'] = [group.id]
        default_group_exists = True
    if not default_group_exists:
      my_public_ip = urllib2.urlopen('http://checkip.dyndns.org').read().strip().split("Current IP Address: ")[1].replace("</body></html>", "").strip()
      for vpc_id in r[region]['vpcs']: 
        group = zone_obj.edit_security_group("NuoDB_default_ports", "These are the default NuoDB ports, open to the world. Autogenerated by nuodb_aws_quickstart.py", [{"protocol": "tcp", "from_port": 48004, "to_port": 48020, "cidr_ip": "0.0.0.0/0"}, {"protocol": "tcp", "from_port": 8888, "to_port": 8889, "cidr_ip": "%s/32" % my_public_ip}, {"protocol": "tcp", "from_port": 8080, "to_port": 8080, "cidr_ip": "%s/32" % my_public_ip}, {"protocol": "tcp", "from_port": 22, "to_port": 22, "cidr_ip": "%s/32" % my_public_ip}], vpc_id=vpc_id)
        r[region]['security_group_ids'] = [group.id]
  return r

  
def cluster(action=None, config_file=None, debug=False, ebs_optimized=False, advanced_mode = False, no_prompt=False):
  params = {
            "aws_access_key": {"default" : "", "prompt" : "What is your AWS access key?", "accept": "^[A-Za-z0-9]*$", "input_error": "Please check your AWS Access key"},
            "aws_secret": {"default" : "", "prompt" : "What is your AWS secret?"},
            "license_file": {"default": "", "prompt": "Please enter a file containing your NuoDB license (No license limits NuoDB to 2 hosts):"},
            "ssh_key": {"default": "", "prompt": "Enter your ssh keypair name that exists in Amazon in all the regions you want to start instances:"},
            "ssh_keyfile": {"default": "%s/.ssh/id_rsa" % os.environ['HOME'], "prompt": "Enter the location on this local machine of the private key used for ssh. Please use the absolute path: "},
            "alert_email" : {"default" : "", "prompt" : "What email address would you like health alerts sent to?", "accept": "^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}$", "input_error": "Please enter a valid email address"}
          }
  verbose_params = {
            "dns_domain": {"default" : "None", "prompt" : "Enter a Route53 domain under your account. If you don't have one enter \"None\":"},
            "domain_name": {"default": "nuodb", "prompt": "What is the name of your NuoDB domain?", "accept": "^[a-zA-Z1-9]*$", "input_error": "Acceptable domain names contain only letters and numbers"},
            "domain_password": {"default": "bird", "prompt": "What is the admin password of your NuoDB domain?"},
            "host_prefix": {"default": "host", "prompt": "What string should preface the number of each host? (ex. {host}0.mycluster.region.nuoDB)", "accept": "^[A-Za-z]$", "input_error": "Please enter a series of only letters and numbers"},
            "load_drivers": {"default" : 0, "prompt": "How many extra hosts (that do not join the cluster) do you want in each region for load driving?", "accept": "^[1-9]$", "input_error": "Please enter a number between 1 and 9"},
            "brokers_per_zone": {"default" : 1, "prompt": "How many brokers do you want in each region?", "accept": "^[1-9]$", "input_error": "Please enter a number between 1 and 9"},
            "custom_rpm" : {"default" : "", "prompt": "Use alternative installation package? Empty for default: "}
          }
  if action == "create":
    #### Gather all the data we need
    c = {}
    static_config = {}
    if config_file == None:
      if os.path.exists("./config.json"): 
        with open("./config.json") as f:
          static_config = json.loads(f.read())
        f.close()
    elif os.path.exists(config_file):
      print "Using configuration from %s" % config_file
      with open(config_file) as f:
        static_config = json.loads(f.read())
        f.close()
      
    for key in static_config:
      if key in params:
        params[key]['default'] = static_config[key]
      if key in verbose_params:
        verbose_params[key]['default'] = static_config[key]
    
    if config_file == None:
      # If the customer doesn't give us a config file prompt for everything
      for key in sorted(params.keys()):
        default = str(params[key]['default'])
        val = raw_input("%s [%s] " % (params[key]['prompt'], default))
        if len(val) == 0:
          c[key] = params[key]['default']
        elif len(val.strip()) == 0:
          c[key] = None
        else:
          if "accept" in params[key]:
            regex = re.compile(params[key]['accept'])
            while not regex.match(val.strip()):
              print "ERROR: " + params[key]['input_error']
              val = raw_input("%s [%s] " % (params[key]['prompt'], default))
          c[key] = val.strip()
          
      #### test for license file
      if len(c['license_file'].strip()) > 0:
        c['license'] = ""
      else:
        while not os.path.exists(c['license_file']):
          print "Cannot find (on this local machine) the license key file %s. Please try again." % c['license_file']
          print "Enter a space to skip using a license file."
          val = raw_input("%s [%s] " % (params['license_file']['prompt'], params['license_file']['default']))
          c['license_file'] = val
          with open(c['license_file']) as f:
            c['license'] = f.read()
            f.close()
          
      #### test for ssh key
      while not os.path.exists(c['ssh_keyfile']):
        print "Cannot find (on this local machine) the ssh private key %s. Please try again." % c['ssh_keyfile']
        val = raw_input("%s [%s] " % (params['ssh_keyfile']['prompt'], params['ssh_keyfile']['default']))
        c['ssh_keyfile'] = val
  
      #### Get Instance type
      if not advanced_mode:
        c['instance_type'] = "m3.large"
      elif "instance_type" not in static_config:
        c['instance_type'] = get_instance_type()
      else:
        res = user_prompt("Use the instance type of %s? (y/n) " % static_config['instance_type'], ["y", "n"])
        if res != "y":
          c['instance_type'] = get_instance_type()
        else:
          c['instance_type'] = static_config['instance_type']
      
      if advanced_mode:
        # ## Populate zone data
        for key in sorted(verbose_params.keys()):
          default = str(verbose_params[key]['default'])
          val = raw_input("%s [%s] " % (verbose_params[key]['prompt'], default))
          if len(val) == 0:
            c[key] = verbose_params[key]['default']
          elif len(val.strip()) == 0:
            c[key] = None
          else:
            if "accept" in verbose_params[key]:
              regex = re.compile(verbose_params[key]['accept'])
              while not regex.match(val.strip()):
                print "ERROR: " + verbose_params[key]['input_error']
                val = raw_input("%s [%s] " % (verbose_params[key]['prompt'], default))
            c[key] = val.strip()
            
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
            if len(c['license']) == 0:
              print "WARNING: Without a license you will be limited to 2 nodes in the domain."
            c["zones"] = get_zone_info(c)
            print "Here is your zone info:"
            for zone in sorted(c["zones"].keys()):
              s = c["zones"][zone]
              print "{}    {:12}    {}    {}    {}".format(zone, s["ami"], str(s["servers"]) + " servers", ",".join(s["subnets"]), ",".join(s["security_group_ids"]))
            res = user_prompt("Use this configuration? (y/n) ", ["y", "n"])
      else:
        c['zones'] = get_zone_info_automatic(c)
        for param in verbose_params:
          c[param] = verbose_params[param]['default']
        
      # Write out the config
      with open("./config.json", 'wt') as f:
        f.write(json.dumps(c, indent=4, sort_keys=True))
      print "Configuration saved to %s" % "./config.json"

    else:
      # Config file given, make sure we have all the info we need
      c = static_config
      for key in params:
        if key not in c:
          c[key] = params[key]['default']
          print "Parameter \"%s\" missing from %s. Using default of \"%s\"" %(key, config_file, str(c[key]))
      for key in verbose_params:
        if key not in c:
          c[key] = verbose_params[key]['default']
          print "Parameter \"%s\" missing from %s. Using default of \"%s\"" %(key, config_file, str(c[key]))
      if len(c['license']) == 0:
        count=0
        for zone in c['zones']:
          count += c['zones'][zone]['servers']
        if count > 2:
          print "ERROR: You have not specified a license so your NuoDB cluster is limited to 2 nodes. Using %d will cause %d nodes to fail." % (count, count-2)
          print "Please add a license or reduce the number of nodes and try again."
          exit(2)
    
    if debug:
      print json.dumps(c, indent=2)
      
    #######################################
    #### Actually do some work
    #######################################
    
    mycluster = nuodbTools.cluster.Cluster(
                                           alert_email=c['alert_email'], ssh_key=c['ssh_key'], ssh_keyfile=c['ssh_keyfile'],
                                           aws_access_key=c['aws_access_key'], aws_secret=c['aws_secret'],
                                           brokers_per_zone=c['brokers_per_zone'], cluster_name=c['domain_name'],
                                           dns_domain=c['dns_domain'], domain_name=c['domain_name'],
                                           domain_password=c['domain_password'], instance_type=c['instance_type'],
                                           nuodb_license=c['license'])
    print "Creating the cluster."
    for zone in c['zones']:
      mycluster.connect_zone(zone)
      z = c['zones'][zone]
      for i in range(0, z['servers']):
        root_name = c['host_prefix'] + str(i)
        myserver = mycluster.add_host(name=root_name, zone=zone, ami=z['ami'], subnets=z['subnets'], security_group_ids=z['security_group_ids'], nuodb_rpm_url=c['custom_rpm'])  # Mark the number of nodes to be created
        print "Added %s" % myserver
      for i in range(0, int(c['load_drivers'])):
        root_name = "load" + str(i)
        myserver = mycluster.add_host(name=root_name, zone=zone, ami=z['ami'], subnets=z['subnets'], security_group_ids=z['security_group_ids'], nuodb_rpm_url=c['custom_rpm'], start_services = False)  # Mark the number of nodes to be created
        print "Added %s as a load driver." % myserver
    
    print "Booting the cluster"
    mycluster.create_cluster(ebs_optimized=ebs_optimized)  # Actually spins up the nodes.
    print "Cluster has started up"

    hosts = mycluster.get_hosts()
    
    print("Waiting for an available web console")
    healthy = False
    i = 0
    wait = 600  # seconds
    good_host = None
    while i < wait:
      if not healthy:
        for host_id in hosts:
          obj = mycluster.get_host(host_id)['obj']
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
      print "======================================================================="
      print "SUCCESS."
      print "You can now access the web console at %s " % str(good_host)
      print "Your domain username is \"domain\" and your password is \"%s\"" % c['domain_password']
      print "Your brokers are:"
      for broker in mycluster.get_brokers():
        print "  " + broker
      print "Other nodes may still be booting and will join the cluster eventually."
      print "For hints and tips on how to operate your new cluster visit the docs at"
      print "http://doc.nuodb.com/display/doc/Next+steps+with+your+NuoDB+cluster"
      print "======================================================================="
    
  ########################
  #### Terminate a cluster
  ########################
  elif action == "terminate":
    if config_file == None and not os.path.exists("./config.json"):
      print "Can't find a previous config file to auto-terminate. If you can't find the file then you will have to destroy the cluster by hand."
      exit(2)
    elif config_file != None and not os.path.exists(config_file):
      print "Can't find provided config file %s. Check the path and try again." % config_file
      exit(2)
    else:
      if config_file == None:
        config_file = "./config.json"
        
      with open(config_file) as f:
        c = json.loads(f.read())
        f.close()
        
      if debug:
        print "DEBUG:"
        print json.dumps(c, indent=2)
 
 
      mycluster = nuodbTools.cluster.Cluster(
                                             alert_email=c['alert_email'], ssh_key=c['ssh_key'], ssh_keyfile=c['ssh_keyfile'],
                                             aws_access_key=c['aws_access_key'], aws_secret=c['aws_secret'],
                                             brokers_per_zone=c['brokers_per_zone'], cluster_name=c['domain_name'],
                                             dns_domain=c['dns_domain'], domain_name=c['domain_name'],
                                             domain_password=c['domain_password'], instance_type=c['instance_type'],
                                             nuodb_license=c['license'])
      
      for zone in c['zones']:
        mycluster.connect_zone(zone)
        z = c['zones'][zone]
        for i in range(0, z['servers']):
          root_name = c['host_prefix'] + str(i)
          myserver = mycluster.add_host(name=root_name, zone=zone, ami=z['ami'], subnets=z['subnets'], security_group_ids=z['security_group_ids'], nuodb_rpm_url=c['custom_rpm'])  # Mark the number of nodes to be created
        for i in range(0, int(c['load_drivers'])):
          root_name = "load" + str(i)
          myserver = mycluster.add_host(name=root_name, zone=zone, ami=z['ami'], subnets=z['subnets'], security_group_ids=z['security_group_ids'], nuodb_rpm_url=c['custom_rpm'], start_services = False)  # Mark the number of nodes to be created
      mycluster.terminate_hosts()
      if not mycluster.dns_emulate:
        if not no_prompt:
          res = user_prompt("Delete DNS records too? Do not do this if you will be restarting the cluster soon. (y/n): ", ["y", "n"])
          if res == "y":
            mycluster.delete_dns()
        else:
          mycluster.delete_dns()
      
  else:
    print "Invalid action"
    exit()

if __name__ == "__main__":
  sys.stdout = nuodbTools.cluster.Unbuffered(sys.stdout)
  parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
  parser.add_argument("-a", "--action", dest='action', action='store', help="What action should be take on the cluster", choices=["create", "terminate"], required=True)
  parser.add_argument("--advanced", dest='advanced_mode', action='store_true', help="Use interactive mode to determine envrionment data. For advanced AWS users.", default=False, required=False)
  parser.add_argument("-c", "--config_file", dest='config_file', action='store', help="A configuration file for the cluster", required=False)
  parser.add_argument("--debug", dest='debug', action='store_true', help="Show a lof of debug data as part of the script", default=False, required=False)
  parser.add_argument("--ebs-optimized", dest='ebs_optimized', action='store_true', help="Use ebs-optimized instances", default=False, required=False)
  args = parser.parse_args()

  cluster(action=args.action, config_file=args.config_file, debug=args.debug, ebs_optimized=args.ebs_optimized, advanced_mode = args.advanced_mode)
