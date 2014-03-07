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
    
    def get_process(self, process_id=None):
      return self.domain.rest_req(action="GET", path="/".join(["processes", process_id]))
      
    def get_processes(self, type=None):
      processes = []
      for process in self.processes:
        if "transactional" in process:
          if (type == "SM" and not process['transactional']) or (type == "TE" and process['transactional']) or type == None:
            processes.append(process)
        else:
          if type == process["type"] or type == None:
            processes.append(process)
      return processes
    
    @property
    def processes(self):
      data = self.domain.rest_req("GET", "/".join(["databases", self.name]))
      return data["processes"]
      
    def start_process(self, type, host = None, archive = None, journal = None, initialize = False, user = None, password = None):
      # curl -X POST -H "Accept: application/json" -H "Content-type: application/json" -u domain:bird -d '{ "type": "TE", "dbname": "foo", "options": {"--dba-user": "dba", "--dba-password": "goalie" } }' http://localhost:8888/api/processes
      # curl -X POST -H "Accept: application/json" -H "Content-type: application/json" -u domain:bird -d '{ "type": "SM", "host": "194e1a9e-ea6d-4874-a030-98c1522c64b3", "dbname": "foo", "initialize": true, "overwrite": false, "archive": "/tmp", "options": {"--journal": "enable", "--journal-dir": "/journal"} }' http://localhost:8888/api/processes
      if type == "SM":
        data = {
                "type": "SM",
                "host": host,
                "dbname": self.name,
                "archive": archive,
                "initialize": str(initialize).lower()
                }
        if journal != None:
          data['options'] = {"--journal-enable": "true", "--journal-dir": journal}
      elif type == "TE":
        if user == None or password == None:
          Error("You must populate 'user' and 'password' fields when starting TEs")
        data = {
                "type": "TE",
                "host": host,
                "dbname": self.name,
                "options": {"---dba-user": user, "--dba-password": password}
                }
      else:
        Error("Invalid value %s for type" % type)
      print "data"
      print data
      self.domain.rest_req("POST", "/databases", data=data)
      
    def stop_process(self, process_id):
      for process in self.processes:
        if process_id == process['uid']:
          self.domain.rest_req(action="DELETE", path="/".join(["processes", process_id]))
          return True
      raise Error("Could not find process %s to stop it" % process_id)
        
    def update(self):
      data = self.domain.rest_req("GET", "databases/%s" % self.name)
      for key in data:
        setattr(self, key, data[key])
        
class Error(Exception):
  pass
        
        