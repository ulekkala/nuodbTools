#!/usr/bin/python
description="""
nuotop - a 'top' like interface for NuoDB. Requires a REST endpoint for the database.
"""

import argparse
import nuodbTools
import sys
import fcntl
import termios
import time
import struct
import traceback
import curses


def size():
  lines, cols = struct.unpack('hh',  fcntl.ioctl(sys.stdout, termios.TIOCGWINSZ, '1234'))
  return (lines,cols)

class Window:
  def __init__(self, height, width, starty, startx):
    self.object = curses.newwin(height, width, starty, startx)
    self.height = height
    self.line = 0
    self.col = 0
    self.width = width
  def clear(self):
    self.line = 0
    self.col = 0
    self.object.clear()
  def get(self):
    return self.object.getch()
  def move(self, starty, startx):
    self.clear()
    self.object.mvwin(starty, startx)
  def newline(self):
    self.line += 1
    self.col=0
  def refresh(self):
    self.object.refresh()
  def resize(self, height, width):
    self.height=height
    self.width=width
    self.object.resize(height, width)
  def write(self, string, attr = 0):
    self.object.addstr(self.line, self.col, string, attr)
    if self.col + len(string) >= self.width:
      self.newline()
    else:
      self.col = self.col + len(string)
  def writeline(self, string, attr = 0):
    self.object.addstr(self.line, 0, string, attr)
    self.line += 1
  def write_block(self, data):
    self.clear()
    for line in data:
      if isinstance(line, (list, tuple)):
        if len(line) > 0:
          self.writeline(line[0], line[1])
        else:
          self.writeline(line[0])
      else:
        self.writeline(line)
  def write_table(self, data):
    self.clear()
    col_meta = {}
    for row in data:
      for idx, col in enumerate(row):
        if isinstance(col, (tuple, list)):
          val = str(col[0])
        else:
          val = str(col)
        if idx not in col_meta or len(val) > col_meta[idx]:
          col_meta[idx] = len(val)
    for row in data:
      for idx, col in enumerate(row):
        if isinstance(col, (tuple, list)):
          val = str(col[0])
          attr = col[1]
        else:
          val = str(col)
          attr = 0
        self.write(val, attr)
        if len(val) < col_meta[idx]:
          for i in range(0, col_meta[idx] - len(val)):
            self.write(" ")
        self.write(" ")
      self.newline()
          
parser = argparse.ArgumentParser(description=description)
parser.add_argument("-s", "--server", dest='host', action='store', help="server address running REST service", default="localhost")
parser.add_argument("-p", "--port", dest='port', action='store', help="server port running REST service", default=8888, type=int)
parser.add_argument("-u", "--user", dest='user', action='store', help="domain username", default="domain")
parser.add_argument("--password", dest='password', action='store', help="domain password", default="bird")
parser.add_argument("-i", "--compute-interval", dest='metric_interval', action='store', help="When computing metric data use data from the last N seconds", default=10, type=int)
parser.add_argument("-d", dest='debug', action='store_true')
args = parser.parse_args()
  
metric_interval = args.metric_interval # seconds
user=args.user
password=args.password
host=args.host
port=args.port
rest_url = "http://%s:%s/api" % (host, str(port))
iteration = 0 
try:
  domain = nuodbTools.cluster.Domain(rest_url=rest_url, rest_username = user, rest_password = password)
  domain.rest_req(path="/databases")
except:
  print "ERROR: Unable to access REST service at %s:%s. Please check your configuration and try aagin." % ( host, port )
  exit (2)
windows = {}
try:
  curses.initscr()
  curses.start_color()
  curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
  curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
  curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
  curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
  curses.noecho()
  curses.halfdelay(25)
  i = 410
  oldmode=None
  mode="hosts"
  render_time = 0
  render_times = []
  while i != 101:
    mytime = int(time.time()) * 1000
    start_time = time.time()
    
    if i == 410:
      # redraw screen
      height, width = size()
      screen = curses.initscr()
      windows['header'] = Window(1, width,0,0)
      windows['footer'] = Window(1, width,height-1,0)
      windows['left'] = Window(height-2, int(width), 1,0)
      for window in windows:
        windows[window].clear()
        windows[window].refresh()
      windows['header'].writeline("nuotop - [h]osts [i]nfo [d]atabases [p]rocesses [q]ueries [e]xit")
    elif i == 113:
      mode = "queries"
    elif i == 104:
      mode = "hosts"
    elif i == 105:
      mode = "info"
    elif i == 100:
      mode = "databases"
    elif i == 112:
      mode = "processes"
    
    if oldmode != mode:
      windows['left'].clear()
      windows['left'].writeline("Loading...", curses.color_pair(4))
      windows['left'].refresh()
    
    for window in windows:
      windows[window].refresh()
    iteration += 1
    
    # local helper functions
    def average_metric(data, length=4, red_threshold=90, yellow_threshold=75):
      acc = 0
      for measurement in data:
        acc += measurement['value']
      avg = acc / len(data)
      if avg > red_threshold:
        attr = curses.color_pair(3)
      elif avg > yellow_threshold:
        attr = curses.color_pair(2)
      else:
        attr = curses.color_pair(1)
      return (str(avg)[0:length], attr)
    def latest_metric(data, default = "?", length=4, red_threshold=90, yellow_threshold=75):
      timestamp = 0
      value = default
      for measurement in data:
        if measurement['timestamp'] > timestamp:
          value = measurement['value']
      if value > red_threshold:
        attr = curses.color_pair(3)
      elif value > yellow_threshold:
        attr = curses.color_pair(2)
      else:
        attr = curses.color_pair(1)
      return (str(value)[0:length], attr)
    
    # fetch data
    
    rows = []
            
    if mode == "info":
      rows.append([
                   ("KEY", curses.A_REVERSE),
                   ("VALUE", curses.A_REVERSE)
                   ])
      items =  args.__dict__
      for item in items:
        rows.append([(item.upper(), curses.A_BOLD), items[item]])
      rows.append([("REST URL", curses.A_BOLD), rest_url])
      rows.append([("UNIX TIME", curses.A_BOLD), str(int(time.time()))])
      rows.append([("ITERATION", curses.A_BOLD), str(iteration)])
      rows.append([("CONSOLE SIZE", curses.A_BOLD), "%d x %d" % size()])
      rows.append([("LAST RENDER TIME", curses.A_BOLD), str(int(render_time))])
      rows.append([("AVG RENDER TIME", curses.A_BOLD), str(int(sum(render_times)/len(render_times)))])
      
    elif mode =="databases":
      ################
      # DATABASE VIEW
      ################
      
      # Fetch data
      try:
        databases = domain.rest_req(path="/databases")
        regions = domain.rest_req(path="/regions")
      except:
        pass
      # assemble data structure
      processes = {}
      for region in regions:
        region_name = region['region']
        for host in region['hosts']:
          for process in host['processes']:
            if process['dbname'] not in processes:
              processes[process['dbname']] = {}
            if region_name not in processes[process['dbname']]:
              processes[process['dbname']][region_name] = {}
            if host['hostname'] not in processes[process['dbname']][region_name]:
              processes[process['dbname']][region_name][host['hostname']] = {"SM": 0, "TE":0}
            processes[process['dbname']][region_name][host['hostname']][process['type']] +=1
            
      rows.append([
                   ("DATABASE", curses.A_REVERSE),
                   ("STATUS", curses.A_REVERSE),
                   ("#REG", curses.A_REVERSE),
                   ("#SM", curses.A_REVERSE),
                   ("#TE", curses.A_REVERSE),
                   ("TEMPLATE", curses.A_REVERSE)
                   ])
      for database in databases:
        row = []
        if database['active'] and database['ismet']:
          attr = curses.color_pair(1)
        elif database['active']:
          attr = curses.color_pair(2)
        else:
          attr = curses.color_pair(3)
        row.append((database['name'], attr))
        row.append(database['status'])
        row.append(str(len(processes[database['name']])))
        sm_count = 0
        te_count = 0
        for region in processes[database['name']]:
          for host in processes[database['name']][region]:
            sm_count += processes[database['name']][region][host]['SM']
            te_count += processes[database['name']][region][host]['TE']
        row.append(str(sm_count))
        row.append(str(te_count))
        row.append(database['template']['name'])
        rows.append(row)
   
    elif mode == "processes":
      ##############
      # PROCESS VIEW
      ##############
      rows.append([
                 ("DATABASE", curses.A_REVERSE),
                 ("HOST", curses.A_REVERSE),
                 ("REGION", curses.A_REVERSE),
                 ("PORT", curses.A_REVERSE),
                 ("TYPE", curses.A_REVERSE),
                 ("PID", curses.A_REVERSE)
                 ])
      databases = domain.rest_req(path="/databases")
      hosts = domain.rest_req(path="/hosts")
      for database in databases:
        for process in database['processes']:
          row = []
          row.append((process['dbname'], curses.A_BOLD))
          row.append(process['hostname'])
          for host in hosts:
              if process['agentid'] == host['id']:
                row.append((host['tags']['region'], curses.A_BOLD))
          row.append(str(process['port']))
          row.append((str(process['type']), curses.A_BOLD))
          row.append(str(process['pid']))
          rows.append(row)
    elif mode == "queries":
      rows.append([
                   ("QUERY", curses.A_REVERSE),
                   ("TIME", curses.A_REVERSE),
                   ("USER", curses.A_REVERSE),
                   ("DATABASE", curses.A_REVERSE)
                   ])
      active_queries = []
      databases = domain.rest_req(path="/databases")
      for database in databases:
        queries = domain.rest_req(path="/databases/%s/queries" % database['name'])
        for query in queries:
          if "statement" in query and 'statementHandle' in query and query['statementHandle'] >= 0:
            active_queries.append((query['time'], query['statement'], query['username'], database['name']))
      for query in sorted(active_queries, reverse=True):
        # we need to be conscious of query output width. therefore insert possible truncated query at end.
        line_len = 0
        row=[]
        for item in [query[0]/100, query[2], query[3]]:
          value = str(item)
          line_len += len(value) + 1
          row.append(value)
        statement = str(query[1])
        statement_width = width - line_len - 4
        if query[0] > 6000:
          attr = curses.color_pair(3)
        elif query[0] > 1000:
          attr = curses.color_pair(2)
        else:
          attr = curses.color_pair(1)
        row.insert(0, (statement[0:statement_width], attr))
        rows.append(row)
        
    else:
      ############
      # HOSTS VIEW
      ############
      regions = domain.rest_req(path="/regions")
      cpu = domain.rest_req(path="/domain/stats?metric=OS-cpuTotalTimePercent&start=%d&stop=%d&breakdown=host" % (mytime-10000, mytime))
      memory = domain.rest_req(path="/domain/stats?metric=OS-memUsedPercent&start=%d&stop=%d&breakdown=host" % (mytime-10000, mytime))
      conns = domain.rest_req(path="/domain/stats?metric=ClientCncts&start=%d&stop=%d&breakdown=host" % (mytime-10000, mytime))
      
      rows.append([
                   ("HOSTNAME", curses.A_REVERSE), 
                   ("REGION", curses.A_REVERSE), 
                   ("B", curses.A_REVERSE),
                   ("IPADDR", curses.A_REVERSE), 
                   ("PORT", curses.A_REVERSE), 
                   ("#PRC", curses.A_REVERSE), 
                   ("%CPU", curses.A_REVERSE), 
                   ("%MEM", curses.A_REVERSE), 
                   ("#CON", curses.A_REVERSE)
                  ])
      for region in regions:
        region_name = region['region']
        for host in sorted(region['hosts'], key=lambda host: host['hostname']):
          row = []
          row.append((host['hostname'], curses.A_BOLD))
          row.append(region_name)
          if host['isBroker']:
            row.append(("Y", curses.color_pair(1)))
          else:
            row.append(("n", curses.color_pair(0)))
          row.append((host['ipaddress'], curses.A_BOLD))
          row.append(str(host['port']))
          row.append((str(len(host['processes'])), curses.A_BOLD))
          if host['id'] in cpu:
            row.append(average_metric(cpu[host['id']]))
          else:
            row.append("?")
          if host['id'] in memory:
            row.append(average_metric(memory[host['id']]))
          else:
            row.append("?")
          if host['id'] in conns:
            row.append(latest_metric(conns[host['id']], default=0))
          else:
            row.append("?")
          rows.append(row)
          
    end_time = time.time()
    if mode != "info":
      render_time = end_time - start_time
      render_times.append(int(render_time))
    if args.debug:
      # Reset the bottom
      windows['footer'].clear()
      windows['footer'].writeline("page render time: %d" % render_time)
    windows['left'].clear()
    windows['left'].write_table(rows)
    windows['left'].refresh()
    i = screen.getch()
    curses.flash()
    oldmode=mode
  curses.endwin()
except KeyboardInterrupt:
  curses.endwin()
except:
  curses.endwin()
  e = sys.exc_info()
  print "".join(["ERROR: " + e[1].__str__() + "\n"] + traceback.format_tb(e[2]))
