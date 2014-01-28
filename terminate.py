import nuodbcluster, os, sys, time


subnets = ["subnet-7b4b720f", "subnet-21dac443", "subnet-21dac443"]

c = {}
with open('./credentials') as f:
  lines = f.read().splitlines()
  for cred in lines:
    key, value = cred.split("=")
    c[key.strip().lower()] = value.strip()

mycluster =  nuodbcluster.NuoDBCluster(aws_access_key = c['aws_access_key'], aws_secret = c['aws_secret'], dns_domain = c['dns_domain'])
print mycluster.dump_db()
mycluster.connect_zone(c['zone'])
mycluster.terminate_all_hosts()
print mycluster.dump_db()
mycluster.exit()