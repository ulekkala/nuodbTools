'''
Created on Feb 21, 2014

@author: rkourtz
'''
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
            
          
          
        
      
      
        