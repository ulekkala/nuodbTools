#!/usr/bin/python
import subprocess
import json, os, urllib2

commands = [
            "hostname $hostname",
            "yum -y update",
            "yum -y install git mailx",
            "yum -y install https://opscode-omnibus-packages.s3.amazonaws.com/el/6/x86_64/chef-11.8.2-1.el6.x86_64.rpm",
            "mkdir -p /var/chef/cookbooks"
            ]

git_repos = {"nuodb": "https://github.com/nuodb/nuodb-chef.git",
             "java": "https://github.com/socrata-cookbooks/java",
             "yum-epel": "https://github.com/opscode-cookbooks/yum-epel.git",
             "yum": "https://github.com/opscode-cookbooks/yum.git"
             }
for repo in git_repos:
  commands.append("if [ ! -d /var/chef/cookbooks/%s ]; then git clone %s /var/chef/cookbooks/%s; fi;" % (repo, git_repos[repo], repo))
  commands.append("cd /var/chef/cookbooks/%s && git pull" % repo)

def execute(command):
  p = subprocess.Popen([command], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  stdout, stderr = p.communicate()
  return (p.returncode, stdout, stderr)

def get_public_ip():
  url = "http://169.254.169.254/latest/meta-data/public-ipv4"
  return urllib2.urlopen(url).read()

def mail(destination = "$email_address", msg = "", subject = "Failure starting host $hostname"):
  command = "echo %s | mail -s %s %s" % (msg, subject, destination)
  execute(command)

for command in commands:
  (rc, stdout, stderr) = execute(command)
  # ignore errors
  
ohai = json.loads(execute("/usr/bin/ohai")[1])
public_ip = get_public_ip()
if execute("grep -c $hostname /etc/hosts")[0] != 0:
    f = open("/etc/hosts", "a")
    f.write("\t".join([public_ip, "$hostname" + "\n"]))
    f.close()
chef_data = json.loads('$chef_json')
chef_data['nuodb']['altAddr'] = public_ip
f = open("/var/chef/data.json", "w")
f.write(json.dumps(chef_data))
f.close()
(chef_result, chef_stdout, chef_stderr) = execute("chef-solo -j /var/chef/data.json | tee -a /var/log/chef.log")

if chef_result != 0:
  mail(msg="\n".join([chef_stdout, chef_stderr]))