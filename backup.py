import json, nuodbcluster, os

configfile = './config.json'
if os.path.exists(configfile):
  with open(configfile) as f:
    c = json.loads(f.read())
    f.close()

c['database'] = "test1"
c['host'] = "db3.wrapper.us-east-1.nuoDB"
c['aws_region'] = "us-east-1"
c['rest_url'] = "http://54.84.134.108:8888/api"
c['ssh_username'] = "ec2-user"


db = nuodbcluster.Backup(name = c['database'], host = c['host'],
                                     aws_access_key=c['aws_access_key'], aws_secret=c['aws_secret'], 
                                     aws_region = c['aws_region'], rest_url = c['rest_url'], 
                                     rest_username = c['domain_name'], rest_password = c['domain_password'], 
                                     ssh_username = c['ssh_username'], ssh_keyfile = c['ssh_keyfile'],
                                     backup_type = "ebs", tarball_destination = "/tmp"
                                     )