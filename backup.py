import json, nuodbcluster, os

configfile = './config.json'
if os.path.exists():
  with open(configfile) as f:
    c = json.loads(f.read())
    f.close()

db = nuodbcluster.Backup(name = c['database'], host = "db0.resttest.us-east-1.nuodbcloud.net",
                                     aws_access_key=c['aws_access_key'], aws_secret=c['aws_secret'], 
                                     aws_region = c['aws_region'], rest_url = c['rest_url'], 
                                     rest_username = c['rest_username'], rest_password = c['rest_password'], 
                                     ssh_username = c['ssh_username'], ssh_key = c['ssh_key'],
                                     backup_type = "tarball", tarball_destination = "/data_small"
                                     )