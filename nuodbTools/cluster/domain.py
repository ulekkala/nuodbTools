# requests module available at http://docs.python-requests.org/en/latest/

import nuodbTools
import collections, inspect, json, re, requests, socket

class Domain():
    '''
    classdocs
    '''
    def __init__(self, rest_url=None, rest_username=None, rest_password=None):
      args, _, _, values = inspect.getargvalues(inspect.currentframe())
      for i in args:
        setattr(self, i, values[i])
      self.rest_urls = []
      # Set up for REST
      #################
      # handle urls that have a slash at the end by truncating it
      def process(url):
        c = {}
        if url[-1] == "/":
          url = url[0:len(url) - 1]
        parts = url.split("://")
        if len(parts) > 1:
          c['protocol'] = parts[0]
          c['path'] = parts[1]
          c['url'] = url
        else:
          c['protocol'] = "http"
          c['rest_port'] = 80
          c['path'] = url
          c['url'] = "://".join([c['protocol'], c['path']])
        path_components = c['path'].split("/")
        c['query_string'] = "/".join(path_components[1:len(path_components)])
        self.rest_urls.append(c)
      
      if isinstance(rest_url, tuple) or isinstance(rest_url, list):
        for url in rest_url:
          process(url)
      else:
        process(rest_url)
      
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
      # Try each url we have, return if we get a hit, good or bad.
      urls_tried = []
      for rest_url in self.rest_urls:
        url = "/".join([rest_url['url'], path])
        headers = {"Accept": "application/json", "Content-type": "application/json"}
        if isinstance(data, dict) or isinstance(data, collections.OrderedDict):
          data_json = json.dumps(data)
        urls_tried.append(url)
        try:
          if action == "POST":
            req = requests.post(url, data=data_json, auth=(self.rest_username, self.rest_password), headers=headers)
          elif action == "PUT":
            req = requests.put(url, data=data_json, auth=(self.rest_username, self.rest_password), headers=headers)
          elif action == "DELETE":
            req = requests.delete(url, data=data_json, auth=(self.rest_username, self.rest_password), headers=headers)
          elif action == "HEAD":
            req = requests.head(url, data=data_json, auth=(self.rest_username, self.rest_password), headers=headers)
          elif action == "OPTIONS":
            req = requests.options(url, auth=(self.rest_username, self.rest_password), headers=headers)
          else:  # Assume GET
            req = requests.get(url, auth=(self.rest_username, self.rest_password), headers=headers)
        except requests.ConnectionError, e:
          # Can't connect to this guy, try the next
          pass
        else:
          if req.status_code == 200:
            if len(req.text) > 0:
              return req.json()
            else:
              return {}
          else:
            d = {"content": req.content, "method": action, "url": url, "data": data, "headers": headers, "code": req.status_code}
            s = "Failed REST Request. DEBUG: %s" % json.dumps(d)
            raise nuodbTools.RESTError(s)
      # If we are here then we couldn't connect to anyone. Raise the flag.
      raise nuodbTools.RESTNotAvailableError("Can't get a connection to any endpoint. Tried: %s" % ",".join(urls_tried))
    
    def pp_rest_req(self, action="GET", path="", data=None, timeout=10):
      return json.dumps(self.rest_req(action, path, data, timeout), indent=4, sort_keys=True)

class Error(Exception):
  pass

class TemporaryAddPolicy:
  def missing_host_key(self, client, hostname, key):
    pass
