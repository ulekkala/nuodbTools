import inspect, json, nuodbcluster, os

with open('./config.json') as f:
  c = json.loads(f.read())
  f.close()

mycluster =  nuodbcluster.NuoDBCluster(aws_access_key = c['aws_access_key'], aws_secret = c['aws_secret'], cluster_name = c['cluster_name'])
print "Cluster before:"
print mycluster.dump_db()
mycluster.terminate_hosts()
print mycluster.dump_db()
mycluster.exit()