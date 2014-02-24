import nuodbcluster

class Database():
    def __init__(self, name, domain = None):
        if domain == None:
          raise Error("Don't have a domain connection")
        self.name = name
        self.domain = domain
        self.update()
        
    def get_hosts(self):
      self.update()
      hosts = []
      for process in self.processes:
        if process['hostname'] not in hosts:
          hosts.append(process['hostname'])
      return sorted(hosts)
    
    def start_process(self, type, host = None, archive = None, journal = None, options = []):
      if type == "SM":
        proto = archive.split("/")[0]
        if proto == "s3:":
          #Do some s3 test here
          pass
        elif proto == "webhdfs:":
          #Do some webhdfs test here
          pass
        elif proto == "": # meaning it is an absolute path for a directory
          # test that the file exists
          pass
        
    def update(self):
      data = self.domain.rest_req("GET", "databases/%s" % self.name)
      for key in data:
        setattr(self, key, data[key])
        
class Error(Exception):
  pass
        
        