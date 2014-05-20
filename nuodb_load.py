#!/usr/bin/python
'''
Created on Feb 25, 2014

@author: rkourtz
'''

import argparse
import nuodbTools.cluster
import sys
import time

description = """
This is a rudimentary NuoDB load generation script which uses the python driver to execute some SQL on a NuoDB cluster. It is not a benchmarking tool, just a validation one. The load generator has two modes: random queries and sql file.

Random Queries
==============
The file will create a table on the database called "LOADERX" where X is a number corresponding to the load thread. Each thread will the execute a series of SELECT:INSERT:UPDATE:DELETE sql queries determined by the ratio flag (by default 5:2:1:1) on that table. Each thread will run for a duration of seconds (by default 10) before it is killed.

SQL File
========
By passing in a text file of SQL commands this script will have each thread execute the SQL file in order. Please be aware that some write transactions will fail due to transactional overlap. When using this mode the Random Query fields described above are ignored. Each thread will run the file as quickly as possible and then exit.
"""
parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-db", "--database", dest='database', action='store', help="Target database", required = True )
parser.add_argument("-b", "--broker", dest='broker', action='store', help="A running broker in the domain", required = True )
parser.add_argument("-u", "--user", dest='user', action='store', help="Database username", required = True )
parser.add_argument("-p", "--password", dest='password', action='store', help="Database Password", required = True )
parser.add_argument("-t", "--threads", dest='threads', action='store', help="Number of parallel connections", type=int, default=1)
parser.add_argument("-f", "--file", dest='file', action='store', help="SQL file to use as import. Otherwise random queries are generated")
parser.add_argument("-d", "--duration", dest='duration', action='store', help="Random queries: How many seconds to run", type=int, default=10)
parser.add_argument("-s", "--schema", dest='schema', action='store', help="What DB schema to use", default="USER")
parser.add_argument("-r", "--ratio", dest='ratio', action='store', help="Random queries: Ratio of SELECT:INSERT:UPDATE:DELETE", default="5:2:1:1")
parser.add_argument("--initial-rows", dest='initial_rows', action='store', help="Random queries: Each connection pre-populates a table with a certain number of random data rows. This is how many rows to insert at start.", default=100)
parser.add_argument("--data-length", dest='value_length', action='store', help="Random queries: Each row has a random string of the length defined here as a value", default=100)
args = parser.parse_args()

threads = args.threads
how_long_to_run = args.duration
ratio = args.ratio

print("Starting load")
thread_tracker = []
selects = 0
inserts = 0
updates = 0
deletes = 0
for mythread in range(1, threads+1):
  print "Initiating connection " + str(mythread)
  loadgen = nuodbTools.cluster.Load("loader" + str(mythread), args.database, args.broker, args.user, args.password, {'schema': args.schema}, initial_rows = int(args.initial_rows), value_length = int(args.value_length), file=args.file)
  thread_tracker.append(loadgen)
for each_thread in thread_tracker:
  each_thread.start_load(ratio)
if args.file == None: 
  print "waiting for " + str(how_long_to_run) + " seconds"
  for i in range(0, how_long_to_run):
    sys.stdout.write(".")
    time.sleep(1)
for idx, each_thread in enumerate(thread_tracker):
  print "Waiting for thread %s completion..." % str(idx+1)
  result = each_thread.stop_load()
  each_thread.close()
  selects += result['select']
  inserts += result['insert']
  updates += result['update']
  deletes += result['delete']
print "Done"
print "Selects done:" + str(selects)
print "Inserts done:" + str(inserts)
print "Updates done:" + str(updates)
print "Deletes done:" + str(deletes)
