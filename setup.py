from setuptools import setup

setup(name='nuodbTools',
      version='0.1.0',
      description='Various tools to deploy, manintain and monitor NuoDB',
      url='http://github.com/nuodb/dbaas',
      author='NuoDB Inc.',
      author_email='info@nuodb.com',
      install_requires=["boto", "paramiko", "requests"], 
      license='BSD licence, see LICENCE.txt',
      packages=['nuodbTools', 'nuodbTools.cluster', 'nuodbTools.aws', 'nuodbTools.physical'],
      scripts=["nuodb_backup.py", "nuodb_cluster.py", "nuodb_load.py", "nuodb_tarball_installer.py"],
      zip_safe=False)
