#!/usr/bin/python
description="""
demo script
"""
import argparse
import nuodbTools
import json

parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-s", "--server", dest='server', action='store', help="server running the Nuo REST API", default = "localhost", required=False, type=str)
parser.add_argument("-p", "--port", dest='port', action='store', help="tcp port for the Nuo REST API", required=False, default=8888, type=int)
parser.add_argument("-u", "--user", dest='username', action='store', help="username for the Nuo REST API", required=False, default="domain", type=str)
parser.add_argument("--password", dest='password', action='store', help="password for the Nuo REST API", required=False, default="bird", type=str)
args = parser.parse_args()

rest_url = "http://%s:%d/api" % (args.server, args.port)
domain = nuodbTools.cluster.Domain(rest_url=rest_url, rest_password=args.password, rest_username=args.username)

processes = {}
template = {"Storefront": {"TE": 6, "SM": 2}}
hosts = {}
for dbname in template:
  processes[dbname] = {"TE": [], "SM": []}

for host in sorted(domain.get_hosts()):
  if host['hostname'] not in hosts:
    hosts[host['hostname']] = 0 

for dbname in processes:
  database= nuodbTools.cluster.Database(dbname, domain=domain)
  for process in database.processes:
    hosts[process['hostname']] += 1
    if process['dbname'] == dbname:
      processes[dbname][process['type']].append(process['hostname'])
      
for dbname in processes:
  print "Creating the %s database" % dbname
  database= nuodbTools.cluster.Database(dbname, domain=domain)
  for t in sorted(processes[dbname]): 
    while len(processes[dbname][t]) < template[dbname][t] and len(processes[dbname][t]) < len(hosts):
      host = sorted(hosts, key=lambda host: hosts[host])[0]
      print "Starting %s process for %s on %s" % (t, dbname, host)
      if t == "SM":
        database.start_process(processtype = t, host_id = domain.get_host_id(host), archive = "/opt/nuodb/data/%s%d_a" % (dbname, 0) , journal  = "/opt/nuodb/data/%s%d_j" % (dbname, 0), initialize=True)
      else:
        try:
          database.start_process(processtype = t, host_id = domain.get_host_id(host), user="%sUser" % dbname, password="%sUser" % dbname)
        except:
          pass
      processes[dbname][t].append(host)
      hosts[host] += 1

print "Now go to http://%s:8080/storefront/admin/ and drive some load." % args.server



