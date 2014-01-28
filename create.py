import nuodbcluster, os, sys, time


subnets = ["subnet-7b4b720f", "subnet-21dac443", "subnet-21dac443"]
security_group_ids = ['sg-e40dec81', 'sg-63f31206']
hosts = 3

c = {}
with open('./credentials') as f:
  lines = f.read().splitlines()
  for cred in lines:
    key, value = cred.split("=")
    c[key.strip().lower()] = value.strip()

mycluster =  nuodbcluster.NuoDBCluster(aws_access_key = c['aws_access_key'], aws_secret = c['aws_secret'], dns_domain = c['dns_domain'])
print mycluster.dump_db()
mycluster.connect_zone(c['zone'])
print mycluster.get_hosts()
for i in range(0,hosts):
  root_name = "db" + str(i)
  myserver = mycluster.create_host(name=root_name, zone=c['zone'], ami="ami-4686e676", subnets=subnets, security_group_ids = security_group_ids)
for myserver in mycluster.get_hosts():
  sys.stdout.write("Waiting for %s to start" % myserver)
  while mycluster.get_host(myserver).status() != "running":
    sys.stdout.write(".")
    time.sleep(5)
  print
for myserver in mycluster.get_hosts():
  print "Setting DNS for %s" % myserver
  mycluster.get_host(myserver).dns_set()
print mycluster.dump_db()
mycluster.exit()