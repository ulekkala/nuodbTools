#!/usr/bin/python
from subprocess import *
import json, os, urllib2

commands = [
            "hostname $hostname",
            "yum -y update",
            "yum -y install git",
            "yum -y install https://opscode-omnibus-packages.s3.amazonaws.com/el/6/x86_64/chef-11.8.2-1.el6.x86_64.rpm",
            "mkdir -p /var/chef/cookbooks",
            "git clone https://github.com/nuodb/nuodb-chef.git /var/chef/cookbooks/nuodb",
            "git clone https://github.com/socrata-cookbooks/java /var/chef/cookbooks/java",
            "git clone https://github.com/opscode-cookbooks/yum-epel.git /var/chef/cookbooks/yum-epel",
            "git clone https://github.com/opscode-cookbooks/yum.git /var/chef/cookbooks/yum"
            ]
for command in commands:
  parts = command.split(" ")
  try:
    call(parts)
  except:
    pass

def get_public_ip():
  url = "http://169.254.169.254/latest/meta-data/public-ipv4"
  return urllib2.urlopen(url).read()

ohai = json.loads(Popen(["/usr/bin/ohai"], stdout=PIPE).communicate()[0])
public_ip = get_public_ip()
if call(["grep", "-c", "$hostname", "/etc/hosts"]):
    f = open("/etc/hosts", "a")
    f.write("\t".join([public_ip, "$hostname" + "\n"]))
    f.close()
chef_data = json.loads('$chef_json')
chef_data['nuodb']['altAddr'] = public_ip
f = open("/var/chef/data.json", "w")
f.write(json.dumps(chef_data))
f.close()
command = "chef-solo -j /var/chef/data.json"
call(command.split(" "))