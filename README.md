
[NuoDB](http://www.nuodb.com) Tools
===========
## Quckstart
* If this is your first database and you want to get up and running you have a few options (in order of complexity):
  * [Install NuoDB natively on a physical machine](http://dev.nuodb.com/download-nuodb/request/download)
  * [Create a NuoDB cluster in a set of virtual machines using Vagrant](https://github.com/nuodb/nuodb-chef#vagrant)
  * [Create a NuoDB cluster in Amazon](#cluster_instructions)
* Once you have a running database you can take advantage of the tools provided in this package

## What are the tools provided?
* `nuodb_backup.py` Take backups of a running NuoDB database 
* `nuodb_cluster.py` Allows you to create a fully functional multi-node and multi-region sandbox database in AWS
* `nuodb_load.py` Simple load generator. For testing only. For a better benchmarking suite go [here](http://tbd)
* `nuodb_tarball_installer.py` If you want to install multiple parallel instances of NuoDB on a single host (for example in build environments)

<a name="cluster_instructions"></a>
## Using `nuodb_cluster.py`:

### Preparation:
* DNS Setup
  * The best and easiest way to use these scripts is to use a [Amazon Route53](http://aws.amazon.com/route53/) hosted domain. If you do not have one the script will attempt to emulate DNS by populating /etc/hosts in each of your servers.
* Determine which regions to use
  * Amazon has (as of this writing) 8 different regions. You should determine which zones you wish to use for your cluster. You will have the ability to choose a base AMI for your installation in each zone- this script will give you the choice of the Amazon Linux ones, one in your account, or an arbitrary one. If you choose an arbitrary one then make note of the id (ami-xxxxxxxxx) because you will need to enter it later.
  * In each region you should determine the subnets for each zone you want to use. Amazon subnet IDs are in the format 'subnet-aaaaaaaa'. You can determine available subnets by using a URL similar to this one and changing the region: `https://console.aws.amazon.com/vpc/home?region=ap-southeast-1#s=subnets`
  * You may use multiple subnets from each region if you like. Instances will be evenly distributed over the subnets.
* Security Zones
  * At a minimum you should allow access to the NuoDB ports listed [here](http://doc.nuodb.com/display/doc/Linux+Installation). If you are doing multi-region then ensure traffic is allowed from other regions. Take note of each of the ids (sg-aaaaaaaa) of the security groups you want to use in each region.
  * Auto creation of secutity zones
    * This script has the ability to auto-create a security zone for you. This security zone will contain the following ports open to the world:
      * 8080 (NuoDB web console)
      * 8888 (NuoDB REST API)
      * 8889 (NuoDB Admin port)
      * 48004 (NuoDB agent port)
      * 48005-48020 (NuoDB TE & SM)
    * Should you choose this security group you must also ensure that SSH is open to the host that you are running the script on. This script uses SSH for some configuration activities.
* SSH keys & AWS credentials
  * You should know the name of valid ssh key for each environment and have the private keys for your account accessible.
  * You should know your AWS access key and AWS secret key
* Python required modules.
  * The package will install the following dependencies:
    * [Boto](https://github.com/boto/boto/tree/master)
    * [Paramiko](https://github.com/paramiko/paramiko)
    * [Requests](http://docs.python-requests.org/en/latest/)
    * [NuoDB Python Driver](https://github.com/nuodb/nuodb-python)
  
### Execution:
* Git clone this repo to a local directory on your machine `git clone http://www.github.com/nuodb/dbaas`
* Run nuodb_cluster.py and enter the data you collected above
* If the script completes correctly it will display the address of a running web console.