import inspect, json, nuodbcluster, os, sys, time

with open('./config.json') as f:
  c = json.loads(f.read())
  f.close()

mycluster =  nuodbcluster.NuoDBCluster(
                                       alert_email = c['alert_email'], 
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
mycluster.exit()