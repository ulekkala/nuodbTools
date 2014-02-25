#!/usr/bin/python

import calendar, hashlib, pynuodb, random, threading, time

class Load:
  def __init__(self, name, database, broker, username, password, options=""):
    self.name = name
    self.database = database
    self.broker = broker
    self.username = username
    self.password = password
    self.runload = False
    self.table = name
    self.threads = []
    
    if not hasattr(self, 'dbconn'):
        self.dbconn = pynuodb.connect(database, broker, username, password, options)
        # self.dbconn.auto_commit(1)
    self.__create_data()
# self.get_tables()
  def __create_data(self):
    sql = "CREATE TABLE IF NOT EXISTS " + self.table + " (ID BIGINT NOT NULL generated always as identity  primary key, VALUE STRING NOT NULL)"
    self.execute_query(sql)
    self.__truncate()
    if self.__count() == 0:
      for i in range(0, 100):
        self.insert()
  def close(self):
    self.dbconn.close()
  def __count(self):
    sql = "SELECT COUNT(*) FROM " + self.table
    result = self.execute_query(sql);
    return result[0]['COUNT']
  def __get_random_row(self):
    sql = "SELECT MIN(ID), MAX(ID) FROM " + self.table
    result = self.execute_query(sql);
    return random.randrange(int(result[0]['MIN']), int(result[0]['MAX']))
  
  def execute_query(self, sql):
    cursor = self.dbconn.cursor()
    # print sql
    try:
      cursor.execute(sql)
    except Exception, e:
      print e
      exit(2)
      # We want to return array of dicts, array of arrays is useless to me.
    try:
      results = []
      resultarray = cursor.fetchall()
      columnarray = cursor.description
      for row in resultarray:
        rowdict = {}
        for myid in range(0, len(columnarray)):
          rowdict[columnarray[myid][0]] = row[myid]
          results.append(rowdict)
    except Exception, e:
      results = []
    cursor.close()
    self.dbconn.commit()
    return results
    
  def get_tables(self):
    sql = "SHOW TABLES"
    print self.execute_query(sql)
  def insert(self):
    value = hashlib.sha224(str(time.clock())).hexdigest()
    sql = "insert into " + self.table.upper() + " (value) values ('" + value + "');"
    self.execute_query(sql)
  def load_threader (self, ratio):
    while self.runload:
      ratios = ratio.split(":")
      #Selects
      for i in range(0, int(ratios[0])):
        count = self.__count()
        startrow = random.randrange(1, count)
        rowrange = random.randrange(0, count - startrow)
        sql = "SELECT * FROM " + self.table + " LIMIT " + str(startrow) + "," + str(rowrange)
        self.execute_query(sql)
        self.query_info['select'] += 1
      #Inserts
      for i in range(0, int(ratios[1])):
        self.insert()
        self.query_info['insert'] += 1
      #Updates
      for i in range(0, int(ratios[2])):
        self.update()
        self.query_info['update'] += 1
      #deletes
      for i in range(0, int(ratios[3])):
        #Don't actually delete now
        self.query_info['delete'] += 1
    self.query_info['stop_time'] = calendar.timegm(time.gmtime())
	    	
  def start_load(self, thread_ratio="1:1:1:1"):
    self.runload = True
    # figure out how to commit every transaction instead of on the dbconn and we can have multiple threads in here.
    for mythread in range(0, 1):
      self.query_info = {"start_time": calendar.timegm(time.gmtime()), "select":0, "insert": 0, "update":0, "delete":0}
      self.threads.append(threading.Thread(target=self.load_threader, args=(thread_ratio,)))
    for mythread in self.threads:
      mythread.start()

  def stop_load(self):
    self.runload = False
    for mythread in self.threads:
      result = mythread.join()
      if mythread.is_alive():
      # print mythread.__dict__
        time.sleep(1)
      return self.query_info
    
  def __truncate(self):
    sql = "TRUNCATE TABLE " + self.table
    self.execute_query(sql)

  def update(self):
    value = hashlib.sha224(str(time.clock())).hexdigest()
    myid = self.__get_random_row()
    sql = "UPDATE " + self.table + " SET value='" + value + "' WHERE ID=" + str(myid)
    self.execute_query(sql)