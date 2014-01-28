#!/usr/bin/python

from subprocess import *
import base64, json, os, re, subprocess, sys, time, urllib2

def get_user_data():
  url = "http://169.254.169.254/latest/user-data"
  string = urllib2.urlopen(url).read()
  return json.loads(base64.b64decode(string))
def get_external_ip():
  url = "http://checkip.dyndns.org"
  try:
    data = urllib2.urlopen(url).read()
    return re.sub(r'[a-zA-Z<>/: ]', "", data).strip()
  except urllib2.URLError, e:
    return None

userdata = get_user_data()
ohai = json.loads(Popen(["/usr/bin/ohai"], stdout=PIPE).communicate()[0])

if "hostname" in userdata:
  hostname = userdata['hostname']
  subprocess.call(["hostname", hostname])
  if subprocess.call(["grep", "-c", hostname, "/etc/hosts"]):
    f = open("/etc/hosts", "a")
    f.write("\t".join([ohai['ipaddress'], hostname+ "\n"]))
    f.close()
if "chef" in userdata:
  external_ip = None
  for i in range(0,10):
    if external_ip == None:
      external_ip = get_external_ip()
      time.sleep(1)
  if external_ip != None:
    userdata['chef']['nuodb']['altAddr'] = external_ip
  os.makedirs("/var/chef/cookbooks")
  f = open("/var/chef/data.json", "w")
  f.write(json.dumps(userdata['chef']))