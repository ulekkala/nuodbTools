import collections
import json
import nuodbTools.cluster
import random

class Database():
    def __init__(self, name, domain = None):
        if domain == None:
          raise Error("Don't have a domain connection")
        self.name = name
        self.domain = domain
        self.update()
    
    def create(self, template = "UnmanagedTemplate", username = None, password = None, variables = {}):
      if self.exists:
        raise Error("Database %s already exists" % self.name) 
      if username == None or password == None:
        raise Error("Username and password must be defined for a new database")
      else:
        data = {"name": self.name, "username": username, "password": password, "template": template, "variables": variables}
        self.domain_obj = self.domain.rest_req(action = "POST", path="databases/", data = data)
        self.exists = True
        return self
    
    @property
    def exists(self):
      if len(self.get_processes()) == 0:
        return False
      else:
        return True
        
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
      
    def start_process(self, processtype = "SM", host_id = None, archive = None, journal = None, initialize = False, user = None, password = None):
      # curl -X POST -H "Accept: application/json" -H "Content-type: application/json" -u domain:bird -d '{ "type": "TE", "dbname": "foo", "options": {"--dba-user": "dba", "--dba-password": "goalie" } }' http://localhost:8888/api/processes
      # curl -X POST -H "Accept: application/json" -H "Content-type: application/json" -u domain:bird -d '{ "type": "SM", "host": "194e1a9e-ea6d-4874-a030-98c1522c64b3", "dbname": "foo", "initialize": true, "overwrite": false, "archive": "/tmp", "options": {"--journal": "enable", "--journal-dir": "/journal"} }' http://localhost:8888/api/processes
      # Find the host with the fewest processes
      data = collections.OrderedDict()
      if host_id == None:
        hosts =[]
        
        for host in self.domain.get_hosts():
          hosts.append((len(host['processes']), host['id']))
        host_id = sorted(hosts)[0][1]
      if processtype == "SM":
        data["type"] = "SM"
        data['host'] = host_id
        data["dbname"] = self.name
        data["archive"] = archive
        data["initialize"] = initialize
        if journal != None:
          data['options'] = collections.OrderedDict()
          data['options']["--journal"] = "enable"
          data['options']["--journal-dir"] = journal
      elif processtype == "TE":
        if user == None or password == None:
          Error("You must populate 'user' and 'password' fields when starting TEs")
        data["type"] = "TE"
        data["host"] = host_id
        data["dbname"] = self.name
        data["options"] = collections.OrderedDict()
        data["options"]["--dba-user"] = user
        data["options"]["--dba-password"] = password
      else:
        raise Error("Invalid value %s for processtype" % processtype)
      r = self.domain.rest_req("POST", "/processes", data=data)
      if isinstance(r, dict):
        return r
      else:
        raise Error("Could not start process %s: %s" % (json.dumps(data), r))
      
      
    def stop_process(self, process_id):
      for process in self.processes:
        if process_id == process['uid']:
          self.domain.rest_req(action="DELETE", path="/".join(["processes", process_id]))
          return True
      raise Error("Could not find process %s to stop it" % process_id)
        
    def update(self):
      if self.name in self.domain.get_databases():
        self.exists = True
        data = self.domain.rest_req("GET", "databases/%s" % self.name)
        for key in data:
          setattr(self, key, data[key])
      else:
        self.exists = False
        
class Error(Exception):
  pass
        
        