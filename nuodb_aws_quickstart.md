## Using `nuodb_aws_quickstart.py`:
* This script allows you to spin up the necessary services to run a NuoDB cluster in [Amazon EC2](http://aws.amazon.com/ec2/)

### Preparation:
* DNS Setup
  * The best and easiest way to use these scripts is to use a [Amazon Route53](http://aws.amazon.com/route53/) hosted domain. If you do not have one the script will attempt to emulate DNS by populating /etc/hosts in each of your servers.
* Determine which regions & subnets to use
  * Amazon has (as of this writing) 8 different regions. You should determine which zones you wish to use for your cluster. You will have the ability to choose a base AMI for your installation in each zone- this script will give you the choice of the Amazon Linux ones, a suggested quickstart one, one in your account, or an arbitrary one. If you choose an arbitrary one then make note of the id (ami-xxxxxxxxx) because you will need to enter it later.
  * In each region you should determine the subnets for each zone you want to use. Amazon subnet IDs are in the format 'subnet-aaaaaaaa'. You will be prompted for the subnets you would like to use.
  * You may use multiple subnets from each region if you like. Instances will be evenly distributed over the subnets.
* Security Zones
  * At a minimum you should allow access to the NuoDB ports listed [here](http://doc.nuodb.com/display/doc/Linux+Installation). If you are doing multi-region then ensure traffic is allowed from other regions. Take note of each of the ids (sg-aaaaaaaa) of the security groups you want to use in each region, or have this script automatically create one for you.
  * Auto creation of security zones
    * This script has the ability to auto-create a security zone for you. This security zone will contain the following ports:
      * 22 (for ssh from the local machine- this script will use ssh to execute commands on the host)
      * 8080 (NuoDB web console)
      * 8888 (NuoDB REST API)
      * 8889 (NuoDB Admin port)
      * 48004 (NuoDB agent port)
      * 48005-48020 (NuoDB TE & SM)
  * If you choose another security group that you created these ports must be open to all of your hosts.
* SSH keys & AWS credentials
  * Every region you want to work from should have the same public key loaded and the private key should be available on your local machine. The script will prompt you for the name of your public key (again, consistent across all regions) and the localtion of your local private key.
  * You should know your AWS access key and AWS secret key
  
### Execution
* Run `nuodb_aws_quickstart.py -a create`
* Enter the information you gathered above, following the prompts
* When the script completes you will have a running cluster in AWS. The script will provide you with URLs for the consoles and brokers so that you may start interacting with it immediately.
* Enjoy NuoDB!
