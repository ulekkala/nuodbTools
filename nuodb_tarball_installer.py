#!/usr/bin/python
'''
Created on Mar 4, 2014

@author: rkourtz@nuodb.com

'''
help = """
NuoDB Tarball Installer
...
This script allows for the installation and starting of many NuoDB instances on a single machine, for example in a continuous integration environment.
Each NuoDB installation is a single node only, and therefore does not require a license.
After being passed a HTTP url for the tarball package download and a unique directory the script will search for an open 10 port range between ports 48000 and 49000 (1 for the broker, 9 for subprocesses- TEs and SMs).
If you use the "data" directory inside the install target directory for your SM archive and journals then the environment may be created fresh each time.
At the completion of this script it will present you with a broker port for your clients to connect to.
DO NOT USE THIS SCRIPT IN PRODUCTION - IT GIVES YOU NONE OF THE BENEFITS OF NUODB.
"""
import argparse
import os
import calendar, time
import re
import shutil
import socket
import subprocess
import tarfile
import tempfile
import urllib2

url = "http://download.nuohub.org/nuodb-2.0.3.linux.x64.tar.gz"

parser = argparse.ArgumentParser(description=help)
parser.add_argument("-a", "--action", dest='action', action='store', help="action", required = True, choices=["install", "uninstall"])
# TBD
#parser.add_argument("-b", "--bootstrap-script", dest="bootstrap", action = "store", required = False, help="Use this script to start up subprocesses")
parser.add_argument("-d", "--dir", dest='directory', action='store', help="Target directory", required = True )
parser.add_argument("--url", dest='url', action='store', help="URL to tarball location", default = url, required = False )
parser.add_argument("-s", "--silent", dest='silent', action='store_true', help="Don't print any output until the end", default = False, required = False )
parser.add_argument("-v", "--verbose", dest='verbose', action='store_true', help="Verbose", default = False, required = False )
args = parser.parse_args()

class Error(Exception):
  pass
def error(s):
  print s
  exit(2)
def extract_tarball(tarball, destination):
  if not tarfile.is_tarfile:
    error("Can't open %s for reading" % tarball)
  f = tarfile.open(name=tarball, mode='r:gz')
  for tarinfo in f:
    full_dest = "/".join([destination, tarinfo.name])
    if os.path.exists(full_dest):
      f.close()
      error("Path to be extracted from tarball (%s) already exists. Delete it first to continue." % full_dest)
    elif tarinfo.name[0] == "." or tarinfo.name[0] == "/":
      f.close()
      error("Element %s in %s is of an improper format (starts with \"/\" or \".\") and could do something nasty. Exiting.")
  if not args.silent:
    print "Extracting %s" % tarball
  f.extractall(path=destination)
  f.close()
def url_fetch(url, target = None):
  file_name = url.split("/")[-1]
  u = urllib2.urlopen(url)
  meta = u.info()
  size = int(meta.getheaders("Content-Length")[0])
  start_time = calendar.timegm(time.gmtime())
  if target != None:
    if not args.silent:
      print "Downloading %s to %s" % (file_name, target)
    f = open(target, "wb")
    file_progress = 0
    blk_size = 8192
    while True:
      buff = u.read(blk_size)
      if not buff:
        break
      file_progress += len(buff)
      f.write(buff)
      cur_time = calendar.timegm(time.gmtime())
      try:
        Kbps = file_progress / ((cur_time - start_time) * 1000)
      except:
        Kbps = 0
      status = r"%10d  [%3.2f%%] %4dKbps" % (file_progress, file_progress * 100. / size, Kbps)
      status = status + chr(8)*(len(status)+1)
      if not args.silent:
        print status,
    if not args.silent:
      print
    f.close()
    return True
  else:
    return u.read()
def port_range_clear(start, end, address = ""):
  for port in range(start, end+1):
    try:
      s = socket.socket()
      s.bind((address, port))
      s.close()
    except:
      return False
  return True
    
  
######
def rewrite_file(file, match, replace):
  t = tempfile.NamedTemporaryFile(delete = False)
  f = open(file, "r")
  lines = f.read().split("\n")
  f.close()
  for line in lines:
    if match in line:
      line = replace
    t.write(line + "\n")
  t.close()
  shutil.move(t.name, file)
  

tarball = os.path.basename(args.url)
tmp_dir = "/tmp"
tmp_file = "/".join([tmp_dir, tarball])

if args.action == "install":
  if not os.access(os.path.dirname(args.directory), os.W_OK):
    error("Can't write to target directory parent %s" % os.path.dirname(args.directory))
  elif os.path.exists(args.directory):
    error("Target directory %s already exists. Uninstall first to continue" % args.directory)
  if not os.path.exists(tmp_file):
    url_fetch(url, tmp_file)
  extract_tarball(tmp_file, tmp_dir)
  extract_dir = "/".join([tmp_dir, ".".join(os.path.basename(tmp_file).split(".")[0:-2])])
  if not args.silent:
    print "Moving %s to %s" % (extract_dir, args.directory)
  shutil.move(extract_dir, args.directory)
  portRange = 48000
  while not port_range_clear(portRange, portRange + 9) and portRange < 49000:
    portRange += 10
  if portRange >= 49000:
    error("Tried to find port ranges in increments of 10 from 48000 to 49000. Could not find a clear port range.")
  if not args.silent:
    print "Using ports starting at %s" % str(portRange)
  for file in ["/".join([args.directory, "etc", "default.properties"])]:
    rewrite_file(file, "#port =", "port = %s" % str(portRange))
    rewrite_file(file, "portRange =", "portRange = %s" % str(portRange+1))
  for dir in ["/".join([args.directory, "data"])]:
    os.mkdir(dir)
  subprocess.call(["/".join([args.directory, "bin", "run-nuoagent.sh"])])
  f = open("/".join([args.directory, "etc", "brokerport"]), "w")
  f.write(str(portRange))
  f.close()
  if args.silent:
    print "localhost:%s" % str(portRange)
  else:
    print "Broker available at localhost:%s" % str(portRange)
elif args.action == "uninstall":
  if not os.path.exists(args.directory):
    error("Can't find target directory %s" % args.directory)
  elif not os.access(args.directory, os.W_OK):
    error("Can't write to directory %s" % args.directory)
  elif not os.access("/".join([args.directory, "bin", "nuodb"]), os.R_OK):
    error("Can't find bin/nuodb in target dir %s. Refusing to delete directory as I am not sure it is correct.")
  # determine broker port
  portfile = "/".join([args.directory, "etc", "brokerport"])
  if os.path.exists(portfile):
    f = open(portfile, "r")
    agentport = int(f.read().rstrip())
    f.close()
  else:
    default_propsfile = "/".join([args.directory, "etc", "default.properties"])
    for line in open(default_propsfile):
      if "port = " in line:
        agentport = re.sub("[^0-9]", "", line).rstrip()
        break
  pids = []
  agentpidfile = "/".join([args.directory, "var", "run", "nuoagent.pid"])
  if os.path.exists(agentpidfile):
    f = open(agentpidfile, "r")
    pids.append(f.read().rstrip())
    f.close()
  childpids = subprocess.Popen(["/bin/sh", "-c", args.directory + "/bin/nuodbmgr --broker localhost:" + str(agentport) + " --password bird --command 'show domain summary' | grep RUNNING| awk '{print $7}'"], stdout=subprocess.PIPE).communicate()[0].split("\n")
  for pid in childpids:
    if len(pid) > 0:
      pids.append(int(pid))
  for pid in pids:
    print "Killing %s" % str(pid)
    subprocess.call(["kill", "-9", pid])
  shutil.rmtree(args.directory)
