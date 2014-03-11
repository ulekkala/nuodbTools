import calendar, hashlib, inspect, nuodbTools.cluster, pynuodb, random, threading, time

class Load():
  def __init__(self, name, database, broker, username, password, options="", initial_rows = 100, truncate_table = True, value_length = 100):
    args, _, _, values = inspect.getargvalues(inspect.currentframe())
    for i in args:
      setattr(self, i, values[i])
    self.runload = False
    self.table = name
    self.threads = []
    self.dbconn = nuodbTools.cluster.sql(database, broker, username, password, options)
        # self.dbconn.auto_commit(1)
    self.__create_data()
# self.get_tables()
  def __create_data(self):
    sql = "CREATE TABLE IF NOT EXISTS " + self.table + " (ID BIGINT NOT NULL generated always as identity  primary key, VALUE STRING NOT NULL)"
    self.dbconn.execute(sql, autocommit=True)
    if self.truncate_table:
      self.__truncate()
    if self.__count() == 0:
      for i in range(0, self.initial_rows):
        self.insert()
  def close(self):
    self.dbconn.close()
  def __count(self):
    sql = "SELECT COUNT(*) FROM " + self.table
    result = self.dbconn.execute(sql, associative = True);
    return result[0]['COUNT']
  def delete(self):
    myid = self.__get_random_row()
    sql = "DELETE FROM " + self.table + " WHERE ID=" + str(myid)
    self.dbconn.execute(sql, autocommit = True)
  def __get_random_row(self, associative = True):
    sql = "SELECT MIN(ID), MAX(ID) FROM " + self.table
    result = self.dbconn.execute(sql, associative = True);
    return random.randrange(int(result[0]['MIN']), int(result[0]['MAX']))
  def __get_random_value(self, length = 20):
    ret = ""
    for i in range(0, length):
            ret += chr(random.randrange(65,125))
    return ret
  def get_tables(self):
    sql = "SHOW TABLES"
    print self.dbconn.execute(sql, associative = True)
  def insert(self):
    value = self.__get_random_value(self.value_length)
    sql = "insert into " + self.table.upper() + " (value) values ('" + value + "');"
    self.dbconn.execute(sql, autocommit = True)
  def load_threader (self, ratio):
    while self.runload:
      ratios = ratio.split(":")
      #Selects
      for i in range(0, int(ratios[0])):
        count = self.__count()
        startrow = random.randrange(1, count)
        rowrange = random.randrange(0, count - startrow)
        sql = "SELECT * FROM " + self.table + " LIMIT " + str(startrow) + "," + str(rowrange)
        self.dbconn.execute(sql)
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
        self.delete()
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
      mythread.join()
      if mythread.is_alive():
      # print mythread.__dict__
        time.sleep(1)
      return self.query_info
    
  def __truncate(self):
    sql = "TRUNCATE TABLE " + self.table
    self.dbconn.execute(sql)

  def update(self):
    value = self.__get_random_value(self.value_length)
    myid = self.__get_random_row()
    sql = "UPDATE " + self.table + " SET value='" + value + "' WHERE ID=" + str(myid)
    self.dbconn.execute(sql, autocommit = True)