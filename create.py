import inspect, json, nuodbcluster, os, sys, time, urllib2

with open('./config.json') as f:
  c = json.loads(f.read())
  f.close()

mycluster =  nuodbcluster.NuoDBCluster(
                                       alert_email = c['alert_email'], ssh_key = c['ssh_key'],
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
    myserver = mycluster.add_host(name=root_name, zone=zone, ami=z['ami'], subnets=z['subnets'], security_group_ids = z['security_group_ids']) # Mark the number of nodes to be created
    print "Added %s" % myserver

print "Booting the cluster"
mycluster.create_cluster() # Actually spins up the nodes.
for myserver in mycluster.get_hosts():
  sys.stdout.write("Waiting for %s to start" % myserver)
  while mycluster.get_host(myserver).status() != "running":
    sys.stdout.write(".")
    time.sleep(5)
  print
for myserver in mycluster.get_hosts():
  print "Setting DNS for %s" % myserver
  mycluster.get_host(myserver).dns_set()
mycluster.sync()
print
print "Cluster is starting up. Here are your brokers:"
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
mycluster.exit()
