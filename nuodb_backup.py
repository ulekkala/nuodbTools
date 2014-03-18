#!/usr/bin/python

import argparse, json, nuodbTools.cluster, os
description="""
NuoDB Backup script
This script will attempt to autodiscover stuff and backup more stuff.
"""

parser = argparse.ArgumentParser(description=description)
parser.add_argument("-a", "--action", dest='action', action='store', help="What action to take",  choices=["backup", "restore", "list"], required = True )
parser.add_argument("-db", "--database", dest='database', action='store', help="Target database", required = True )
parser.add_argument("--host", dest='host', action='store', help="Host to take the backup on", required = True)
parser.add_argument("--rest-url", dest='rest_url', action='store', help="URL of a running NuoDB REST service", required = True )
parser.add_argument("--rest-username", dest='rest_username', action='store', help="Username for the NuoDB REST service", required = True )
parser.add_argument("--rest-password", dest='rest_password', action='store', help="Password for the NuoDB REST service", required = True )
parser.add_argument("--aws-key", dest='aws_key', action='store', default = None, help="AWS access key. Only needed for Amazon Web Services instances.", required = False)
parser.add_argument("--aws-secret", dest='aws_secret', action='store', default = None, help="AWS secret. Only needed for Amazon Web Services instances.", required = False)
parser.add_argument("--aws-region", dest='aws_region', action='store', default = None, help="AWS region to connect to", required = False )
parser.add_argument("--ssh-username", dest='ssh_username', action='store', default = None, help="For non-local backups this script will need to ssh in to a host. Use this username.", required = False)
parser.add_argument("--ssh-key", dest='ssh_keyfile', action='store', default = None, help="SSH private key file", required = False)
parser.add_argument("--backup-type", dest='backup_type', action='store', help="SSH private key file", choices=["auto", "ebs", "tarball", "zfs"], default="auto", required = False)
parser.add_argument("--tarball-dest", dest='tarball_destination', action='store', help="For tarball type backups, put the tarball in this directory on the host", required = False)
parser.add_argument("--comment", dest='comment', action='store', help="Human readable comment on the backup", default = None, required = False)
parser.add_argument("--snapshot", dest='snapshot', action='store', help="AWS snapshot to recover from", default = None, required = False)
parser.add_argument("--db-user", dest='db_user', action='store', help="RESTORE ONLY. The user for the restore DB TE", default = None, required = False)
parser.add_argument("--db-password", dest='db_pass', action='store', help="RESTORE ONLY. The password for the restore DB TE", default = None, required = False)
args = parser.parse_args()

## Helpers
def user_prompt(prompt, valid_choices = [], default = None):
  if default != None:
    prompt = "%s [%s] " % (prompt, str(default))
  val = raw_input(prompt)
  if len(valid_choices) == 0:
    if default == None:
      return val
    else:
      return default
  for choice in valid_choices:
    if val == str(choice):
      return choice
  valid_strings = []
  #Handle integer inputs
  for choice in valid_choices:
    valid_strings.append(str(choice))
  print "Invalid choice. Your choices are: [" + ",".join(valid_strings) + "]"
  return user_prompt(prompt, valid_choices)
  
def choose_from_list(params = [], suggested = None):
  # returns index of the list you gave me
  i = 0
  options = []
  while i < len(params):
    if suggested != None and suggested == i:
      suggest_prompt = "<----- SUGGESTED"
    else:
      suggest_prompt = ""
    #print "%s)  %s %s" % (i+1, params[i], suggest_prompt)
    print '{:2d}) {:25} {}'.format(i+1, params[i], suggest_prompt)
    i += 1
    options.append(i)
  return user_prompt("Choose one:", options) - 1

## Start work

db = nuodbTools.cluster.Backup(database = args.database, host = args.host,
                                     aws_access_key=args.aws_key, aws_secret=args.aws_secret, 
                                     aws_region = args.aws_region, rest_url = args.rest_url, 
                                     rest_username = args.rest_username, rest_password = args.rest_password, 
                                     ssh_username = args.ssh_username, ssh_keyfile = args.ssh_keyfile,
                                     backup_type = args.backup_type, tarball_destination = args.tarball_destination
                                     )
if args.action == "backup":
  if args.comment != None and len(args.comment) > 0:
    db.backup(comment = str(args.comment))
  else:
    db.backup()
elif args.action == "restore":
  options = []
  for bu in db.backups:
    options.append(bu[0])
  print "Choose a backup of database '%s' to restore:" % args.database
  choice = choose_from_list(params = options)
  db.restore(db_user = args.db_user, db_password = args.db_pass, snapshots = db.backups[choice][1])
  #if "snap-" in args.snapshot:
  #  db.restore([args.snapshot])
else:
  print "Invalid action. Exiting."
  
