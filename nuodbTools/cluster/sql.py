'''
Created on Feb 21, 2014

@author: rkourtz
'''
import json
import pynuodb

class sql():
    def __init__(self, 
                 dbname,
                 host,
                 username,
                 password,
                 options
                 ):
      self.connection = pynuodb.connect(dbname, host, username, password, options)
      
    def close(self):
      self.connection.close()
    
    def commit(self):
      cursor = self.execution.cursor()
      try:
        cursor.execute("COMMIT")
        return True
      except:
        return False
      
    def execute(self, command, autocommit = False, associative = False):
      cursor = self.connection.cursor()
      cursor.execute(command)
      if autocommit:
        cursor.execute("COMMIT")
      if command.split(" ")[0] != "SELECT" or not associative:
        if cursor._result_set != None:
          results = cursor.fetchall()
        else:
          results = True
        cursor.close()
        return results
      else:
        returnval = []
        desc = cursor.description
        results = cursor.fetchall()
        cursor.close()
        for rownum, row in enumerate(results):
          returnrow = {}
          for idx, field in enumerate(row):
            returnrow[desc[idx][0]] = field
          returnval.append(returnrow)
        return returnval
    
    def make_insert_sql(self, table, fields = []):
      p = "INSERT INTO %s " % table
      d1 = []
      d2 = []
      if isinstance(fields, dict):
        for field in fields.keys():
          d1.append(field)
          value = str(fields[field])
          if value.isdigit():
            d2.append(value)
          else:
            d2.append("'%s'" % value)
      elif isinstance(fields, list) or isinstance(field, tuple): 
        for field in fields:
          if isinstance(field, dict):
            for key in field.keys():
              d1.append(key)
              if isinstance(field['key'], str):
                d2.append("'%s'" % field['key'])
              else:
                d2.append(str(field['key']))
          elif isinstance(field, tuple) or isinstance(field, list):
            d1.append(field[0])
            if isinstance(field[1], str):
              d2.append("'%s'" % field[1])
            else:
              d2.append(str(field[1]))
      else:
        raise Error("fields passed must be an array or list or tuples, or an array of dicts. Got %s" % json.dumps(fields))
      if len(d1) == len(d2) and len(d1) > 0:
        return " ".join([p, "(",", ".join(d1), ") VALUES (", ", ".join(d2), ")"])
      
      
          
class Error(Exception):
  pass