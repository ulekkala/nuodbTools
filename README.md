
[NuoDB](http://www.nuodb.com) Quickstart
===========
## Getting started
* If this is your first database and you want to try out NuoDB you have a few options (in order of complexity):
  * [Install NuoDB natively on a physical machine](http://dev.nuodb.com/download-nuodb/request/download)
  * [Create a NuoDB cluster in a set of virtual machines using Vagrant](https://github.com/nuodb/nuodb-chef#vagrant)
  * [Create a NuoDB multiple region cluster in Amazon](nuodb_aws_quickstart.md)
* Once you have a running database you can take advantage of the tools provided in this package

## What are the tools provided?
* [`nuodb_backup.py`](nuodb_backup.md) Take backups of a running NuoDB database 
* [`nuodb_aws_quickstart.py`](nuodb_aws_quickstart.md) Allows you to create a fully functional multi-node and multi-region sandbox database in AWS
* [`nuodb_load.py`](nuodb_load.md) Simple load generator. For testing only.
* [`nuodb_tarball_installer.py`](nuodb_tarball_installer.md) If you want to install multiple parallel instances of NuoDB on a single host (for example in build environments)


### Requirements
* Python 2.7
* The package will install the following Python dependencies:
  * [Boto](https://github.com/boto/boto/tree/master)
  * [Paramiko](https://github.com/paramiko/paramiko)
  * [Requests](http://docs.python-requests.org/en/latest/)
  * [NuoDB Python Driver](https://github.com/nuodb/nuodb-python)
  
### Installation:
#### Prerequisites
  * Fedora

`sudo yum -y install git python-devel python-pip`
  * Ubuntu

`sudo apt-get install git python-dev python-pip`

#### Installation
* Run the following from the command line
`git clone https://github.com/nuodb/nuodbTools.git`
`cd nuodbTools`
`sudo python setup.py install` 
* Run the tool of your choice:
[`nuodb_backup.py`](nuodb_backup.md)
[`nuodb_aws_quickstart.py`](nuodb_aws_quickstart.md)
[`nuodb_load.py`](nuodb_load.md)
[`nuodb_tarball_installer.py`](nuodb_tarball_installer.md)