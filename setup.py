from setuptools import setup
import sys

v = sys.version_info
if v[0] == 2 and v[1] == 7:
  setup(name='nuodbTools',
        version='0.1.1',
        description='Various tools to deploy, manintain and monitor NuoDB',
        url='http://github.com/nuodb/nuodbTools',
        author='NuoDB Inc.',
        author_email='info@nuodb.com',
        data_files=[('nuodbTools/cluster/templates', ['nuodbTools/cluster/templates/init.py'])],
        install_requires=["boto", "paramiko", "pynuodb", "requests"],
        license='BSD licence, see LICENCE.txt',
        packages=['nuodbTools'],
        scripts=["nuodb_backup.py", "nuodb_aws_quickstart.py", "nuodb_load.py", "nuodb_tarball_installer.py"],
        zip_safe=False)
else:
  print "The nuodbTools module and some of its dependencies only work on Python version 2.7. Detected %s. Cannot continue." % ".".join(str(e) for e in v[0:2])
  exit(2)
