## Using `nuodb_cluster.py`:
* This script allows you to spin up the necessary services to run a NuoDB cluster in [Amazon EC2](http://aws.amazon.com/ec2/)

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
  
### Execution
* Run `nuodb_cluster.py`
* Enter the information you gathered above, following the prompts
* When the script completes you will have a running cluster in AWS. The script will provide you with URLs for the consoles and brokers so that you may start interacting with it immediately.