'''
Created on Feb 20, 2014

@author: rkourtz
'''
import inspect
import json
import math
import nuodbcluster
import re
import uuid


class Customer():
  def __init__(self, 
               domain, # nuoDB domain object
               db, # nuodbaas SQL object
               alias = None,
               uuid = None,
               id = None
               ):
    args, _, _, values = inspect.getargvalues(inspect.currentframe())
    for i in args:
      setattr(self, i, values[i])
    self.__database_load()
  
  def create(self, fname, lname, address1, address2, city, state, country, postcode):
    if self.exists:
      raise Error("Customer already exists")
    self.uuid = uuid.uuid4()
    sql_fields = ['UUID'] 
    sql_values = ["'%s'" % self.uuid]
    args, _, _, values = inspect.getargvalues(inspect.currentframe())
    for i in args:
      setattr(self, i, values[i])
      if i != "self" and values[i] != None:
        sql_fields.append(i.upper())
        sql_values.append("'%s'" % values[i])
    sql = "INSERT INTO customers (%s) VALUES (%s)" % (",".join(sql_fields), ",".join(sql_values))
    self.db.execute(sql, autocommit="True")
    self.id = self.db.execute("SELECT ID FROM CUSTOMERS WHERE UUID='%s'" % self.uuid)[0][0]
    self.alias = format(int(self.id) + 43690, 'x') # Start at aaaa
    sql = "UPDATE customers SET ALIAS='%s' WHERE UUID='%s'" % (self.alias, self.uuid)
    self.db.execute(sql, autocommit="True")


  def get_database(self, name):
    if not getattr(self.databases):
      self.get_databases()
    if name in self.databases:
      return self.databases[name]
    else:
      return None
    
  @property
  def databases(self):
    if hasattr(self, 'databases_cached'):
      return self.databases_cached
    returnval= []
    database_list = {}
    databases = self.domain.get_databases()
    for database in databases:
      if re.match("^%s-" % self.alias, database):
        database_list[database] = nuodbcluster.Database(database, self.domain)
    self.databases_cached = database_list
    return self.databases_cached
  
  def get_host(self, name):
    if not getattr(self.hosts):
      self.get_hosts()
      
      #### Make a host object
    
  @property
  def hosts(self):
    hosts = []
    for database in self.databases:
      for process in self.databases[database].processes:
        if process['hostname'] not in hosts:
          hosts.append(process['hostname'])
    self.hosts = sorted(hosts)
    return self.hosts
  
  def get_processes(self):
    processes = []
    for database in self.databases:
      for process in self.databases[database].processes:
        processes.append(process['uid'])
    self.processes = sorted(processes)
    return self.processes
      
  
  def __database_load(self):
    if self.uuid != None:
      sql = "SELECT * FROM customers WHERE UUID='%s'" % self.uuid
    elif self.alias != None:
      sql = "SELECT * FROM customers WHERE ALIAS='%s'" % self.uuid
    elif self.id != None:
      sql = "SELECT * FROM customers WHERE ID='%s'" % self.id
    else:
      self.exists = False
      return
    results = self.db.execute(sql, associative = True)
    if len(results) == 0:
      self.exists = False
    else:
      self.exists = True
      for field in results[0]:
        setattr(self, field.lower(), results[0][field])
      
  def __database_save(self):
    data = json.dumps(self.data)
    if not self.exists:
      sql = "INSERT INTO customers (ID, DATA) VALUES ('%s', '%s')" % (self.id, data)
    else:
      sql = "UPDATE customers SET DATA='%s' WHERE ID='%s'" % (data, self.id)
    self.db.execute(sql)
    
class Error(Exception):
  pass
        
