#!/usr/bin/python

from subprocess import *
import base64, json, subprocess, sys, urllib2

def get_user_data():
	url = "http://169.254.169.254/latest/user-data"
	string = urllib2.urlopen(url).read()
	return json.loads(base64.b64decode(string))

userdata = get_user_data()
ohai = json.loads(Popen(["/usr/bin/ohai"], stdout=PIPE).communicate()[0])

hostname = userdata['hostname']
subprocess.call(["hostname", hostname])
if subprocess.call(["grep", "-c", hostname, "/etc/hosts"]):
	f = open("/etc/hosts", "a")
	f.write("\t".join([ohai['ipaddress'], hostname+ "\n"]))
	f.close()
