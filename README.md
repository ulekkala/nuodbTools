
[NuoDB](http://www.nuodb.com) Tools
===========
## Quckstart
* If this is your first database and you want to get up and running you have a few options (in order of complexity):
  * [Install NuoDB natively on a physical machine](http://dev.nuodb.com/download-nuodb/request/download)
  * [Create a NuoDB cluster in a set of virtual machines using Vagrant](https://github.com/nuodb/nuodb-chef#vagrant)
  * [Create a NuoDB cluster in Amazon](nuodb_cluster.md)
* Once you have a running database you can take advantage of the tools provided in this package

## What are the tools provided?
* `nuodb_backup.py` Take backups of a running NuoDB database 
* `nuodb_cluster.py` Allows you to create a fully functional multi-node and multi-region sandbox database in AWS
* `nuodb_load.py` Simple load generator. For testing only. For a better benchmarking suite go [here](http://tbd)
* `nuodb_tarball_installer.py` If you want to install multiple parallel instances of NuoDB on a single host (for example in build environments)


### Requirements
* Python 2.7
* The package will install the following Python dependencies:
  * [Boto](https://github.com/boto/boto/tree/master)
  * [Paramiko](https://github.com/paramiko/paramiko)
  * [Requests](http://docs.python-requests.org/en/latest/)
  * [NuoDB Python Driver](https://github.com/nuodb/nuodb-python)
  
### Execution:
* Git clone this repo to a local directory on your machine 
* `python setup.py install`