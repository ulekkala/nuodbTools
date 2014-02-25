'''
Created on Feb 25, 2014

@author: rkourtz
'''

import nuodbcluster
import sys
import time
 
threads = 1
how_long_to_run = 10
ratio = "5:2:1:0" # Selects:Inserts:Updates:Deletes

print("Starting load")
thread_tracker = []
selects = 0
inserts = 0
updates = 0
deletes = 0
for mythread in range(1, threads+1):
  print "Initiating connection " + str(mythread)
  loadgen = nuodbcluster.Load("loader" + str(mythread), "mydb", "db0.cluster1.us-west-2.nuodbcloud.net", "dba", "dba", {'schema': 'test'})
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
