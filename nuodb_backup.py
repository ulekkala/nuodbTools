#!/usr/bin/python

import argparse, json, nuodbTools.cluster, os
description="""
NuoDB Backup script
This script will attempt to autodiscover stuff and backup more stuff.
"""

parser = argparse.ArgumentParser(description=description)
parser.add_argument("-db", "--database", dest='database', action='store', help="Target database", required = True )
parser.add_argument("--host", dest='host', action='store', help="Host to take the backup on", required = True)
parser.add_argument("--rest-url", dest='rest_url', action='store', help="URL of a running NuoDB REST service", required = True )
parser.add_argument("--rest-username", dest='rest_username', action='store', help="Username for the NuoDB REST service", required = True )
parser.add_argument("--rest-password", dest='rest_password', action='store', help="Password for the NuoDB REST service", required = True )
parser.add_argument("--aws-key", dest='aws_key', action='store', default = None, help="AWS access key. Only needed for Amazon Web Services instances.", required = False)
parser.add_argument("--aws-secret", dest='aws_secret', action='store', default = None, help="AWS secret. Only needed for Amazon Web Services instances.", required = False)
parser.add_argument("--aws_region", dest='aws_region', action='store', default = None, help="AWS region to connect to", required = False )
parser.add_argument("--ssh-username", dest='ssh_username', action='store', default = None, help="For non-local backups this script will need to ssh in to a host. Use this username.", required = False)
parser.add_argument("--ssh-key", dest='ssh_keyfile', action='store', default = None, help="SSH private key file", required = False)
parser.add_argument("--backup-type", dest='backup_type', action='store', help="SSH private key file", choices=["auto", "ebs", "tarball", "zfs"], default="auto", required = False)
parser.add_argument("--tarball-dest", dest='tarball_destination', action='store', help="For tarball type backups, put the tarball in this directory on the host", required = False)
args = parser.parse_args()


db = nuodbTools.cluster.Backup(database = args.database, host = args.host,
                                     aws_access_key=args.aws_key, aws_secret=args.aws_secret, 
                                     aws_region = args.aws_region, rest_url = args.rest_url, 
                                     rest_username = args.rest_username, rest_password = args.rest_password, 
                                     ssh_username = args.ssh_username, ssh_keyfile = args.ssh_keyfile,
                                     backup_type = args.backup_type, tarball_destination = args.tarball_destination
                                     )
