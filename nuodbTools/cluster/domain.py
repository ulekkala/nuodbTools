# requests module available at http://docs.python-requests.org/en/latest/


import collections, inspect, json, re, requests, socket

class Domain():
    '''
    classdocs
    '''
    def __init__(self, rest_url=None, rest_username=None, rest_password=None):
      args, _, _, values = inspect.getargvalues(inspect.currentframe())
      for i in args:
        setattr(self, i, values[i])
      # Set up for REST
      #################
      # handle urls that have a slash at the end by truncating it
      if rest_url[-1] == "/":
        substr_index = len(rest_url) - 1
        rest_url = rest_url[0:substr_index]
        self.rest_url = rest_url
      (self.rest_protocol, self.rest_path) = rest_url.split("://")
      path_components = self.rest_path.split("/")
      (self.rest_hostname, self.rest_port) = path_components[0].split(":")
      if self.rest_port == None:
        if self.rest_protocol == "https":
          self.rest_port = 443
        elif self.rest_protocol == "http":
          self.rest_port = 80
      self.rest_query_string = "/".join(path_components[1:len(path_components)])
      ip_pattern = re.compile("^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+")
      if not ip_pattern.match(self.rest_hostname):
        try:
          self.rest_ip = socket.gethostbyname(self.rest_hostname)
        except:
          raise Error("Could not find a valid address for %s" % self.rest_hostname)
      db_url = "/".join([self.rest_url, "databases"])
      r = requests.get(db_url, auth=(rest_username, rest_password)) 
      if r.status_code != 200:
        print "Bad result from %s" % db_url
        r.raise_for_status() 
      
    def get_databases(self):
      data = self.rest_req("GET", "databases")
      databases = []
      for db in data:
        databases.append(db['name'])
      return sorted(databases)
    
    def get_host_id(self, hostname):
      for host in self.get_hosts():
        if hostname == host['hostname']:
          return host['id']
      return None
      
    def get_hosts(self):
      return self.rest_req(action = "GET", path = "hosts")
      
    def get_processes(self, database=None):
      data = self.rest_req("GET", "processes")
      processes = []
      for process in data:
        if database == None:
          processes.append(process)
        elif process['dbname'] == database:
          processes.append(process)
      return processes
        
    def rest_req(self, action="GET", path="", data=None, timeout=10):
      if path[0] == "/":
        path = path[1:len(path)]
      url = "/".join([self.rest_url, path])
      headers = {"Accept": "application/json", "Content-type": "application/json"}
      if isinstance(data, dict) or isinstance(data, collections.OrderedDict):
        data = json.dumps(data)
      if action == "POST":
        req = requests.post(url, data=data, auth=(self.rest_username, self.rest_password), headers=headers)
      elif action == "PUT":
        req = requests.put(url, data=data, auth=(self.rest_username, self.rest_password), headers=headers)
      elif action == "DELETE":
        req = requests.delete(url, data=data, auth=(self.rest_username, self.rest_password), headers=headers)
      elif action == "HEAD":
        req = requests.head(url, data=data, auth=(self.rest_username, self.rest_password), headers=headers)
      elif action == "OPTIONS":
        req = requests.options(url, auth=(self.rest_username, self.rest_password), headers=headers)
      else:  # Assume GET
        req = requests.get(url, auth=(self.rest_username, self.rest_password), headers=headers)
      if req.status_code == 200:
        if len(req.text) > 0:
          return req.json()
        else:
          return {}
      else:
        print req.content
        print "DEBUG: method: %s" % action
        print "DEBUG: url: %s" % url
        print "DEBUG: data: %s" % json.dumps(data)
        print "DEBUG: headers: %s" % json.dumps(headers)
        req.raise_for_status()
    
    def pp_rest_req(self, action="GET", path="", data=None, timeout=10):
      return json.dumps(self.rest_req(action, path, data, timeout), indent=4, sort_keys=True)

class Error(Exception):
  pass

class TemporaryAddPolicy:
  def missing_host_key(self, client, hostname, key):
    pass
