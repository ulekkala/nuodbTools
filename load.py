#!/usr/bin/python
'''
Created on Feb 25, 2014

@author: rkourtz
'''

import argparse
import nuodbcluster
import sys
import time

description = """
This is a rudimentary NuoDB load generation script which uses the python driver to execute some SQL on a NuoDB cluster. It is not a benchmarking tool, just a validation one.
"""
parser = argparse.ArgumentParser(description=description)
parser.add_argument("-db", "--database", dest='database', action='store', help="Target database", required = True )
parser.add_argument("-b", "--broker", dest='broker', action='store', help="A running broker", required = True )
parser.add_argument("-u", "--user", dest='user', action='store', help="Database username", required = True )
parser.add_argument("-p", "--password", dest='password', action='store', help="Database Password", required = True )
parser.add_argument("-t", "--threads", dest='threads', action='store', help="Number of workers", type=int, default=1)
parser.add_argument("-d", "--duration", dest='duration', action='store', help="How many seconds to run", type=int, default=10)
parser.add_argument("-s", "--schema", dest='schema', action='store', help="What DB schema to use", default="loadgen")
parser.add_argument("-r", "--ratio", dest='ratio', action='store', help="Ratio of SELECT:INSERT:UPDATE:DELETE", default="5:2:1:1")
parser.add_argument("--initial-rows", dest='initial_rows', action='store', help="Each connection pre-populates a table with a certain number of random data rows. This is how many rows to insert at start.", default=100)
parser.add_argument("--data-length", dest='value_length', action='store', help="Each row has a random string of the length defined here as a value", default=100)
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
  loadgen = nuodbcluster.Load("loader" + str(mythread), args.database, args.broker, args.user, args.password, {'schema': args.schema}, initial_rows = int(args.initial_rows), value_length = int(args.value_length))
  thread_tracker.append(loadgen)
for each_thread in thread_tracker:
  each_thread.start_load(ratio)
print "waiting for " + str(how_long_to_run) + " seconds"
for i in range(0, how_long_to_run):
  sys.stdout.write(".")
  time.sleep(1)
for each_thread in thread_tracker:
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
