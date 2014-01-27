#!/usr/bin/python

import os, smtplib, subprocess, tempfile, time
from email.mime.text import MIMEText

max_tries = 10
wait_in_between_tries = 30 # seconds
alert_email = "rkourtz@nuodb.com"

commands = [[["chef-client","-S https://chef"], False], [["service","nuoagent","status"], False]]
f = tempfile.NamedTemporaryFile()
overall_success = False
for i in range(0, max_tries):
  for idx, val in enumerate(commands):
    success = True
    command = val[0]
    result = val[1]
    if not result:
      f.write(" ".join(command))
      f.write("\n")
      p = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
      if p.wait() == 0:
        commands[idx][1] = True
      else:
        success = False
      f.write("".join(p.stdout.readlines()))
  if not success:
    time.sleep(wait_in_between_tries)
  else:
    overall_success = True
    i = max_tries

if not overall_success:
  mailbody = "Failed to achieve desired state after " + str(max_tries) + " tries"
  mailbody += "Results:"
  for idx, val in enumerate(commands):
    mailbody += " ".join(val[0]) + "\t" + str(val[1])
  f.seek(0)
  mailbody += "".join(f.readlines())
  msg = MIMEText(mailbody)
  msg['Subject'] = "Error while bootstrapping " + os.environ['HOSTNAME']
  msg['From'] = "bootstrap@localhost"
  msg['To'] = alert_email
  s = smtplib.SMTP("localhost", "25")
  s.sendmail("bootstrap@nuodbcloud.net", [alert_email], msg.as_string())
  s.quit()

f.close()
