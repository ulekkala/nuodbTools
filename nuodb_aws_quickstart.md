## Using `nuodb_aws_quickstart.py`:
* This script allows you to spin up the instances and services to run a NuoDB cluster in [Amazon EC2](http://aws.amazon.com/ec2/)

### Preparation:
* Install this toolkit
  * Follow the instructions at the bottom of [this page](README.md#usage)
 
### Basic Mode
* Use this mode if you would like to create your cluster inside the default VPC
* What you will need:
  * Your AWS access key and secret
    * Your access key can be found from the AWS console ["Services -> IAM -> Users -> YOURUSER -> Security Credentials"](https://console.aws.amazon.com/iam/home#users)
    * If you do not have any access keys listed you may "Manage Access Keys" and create a new pair.
    * Each access key has an associated secret. You must have that key stored somewhere as it is not retrievable from the AWS console. If you do not have it you must create another access key and secret thorough "Manage Access Keys"
    * Any user you will be using for this purpose should have Power User or Administrator privileges ("Services -> IAM -> Users -> YOURUSER -> Permissions")
  * A consistent SSH public key (also named consistently) loaded in each region you want to run in and the associated private key
    * Your keys are loaded individually for each region and can be managed through the [web UI](https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#KeyPairs:)
    * Please consult [this document](http://www.nuodb.com/tbd) on how to do this
* From your terminal prompt run the following command:
`nuodb_aws_quickstart.py -a create`
* Enter the information you gathered above to create your cluster.
  
### Advanced Mode
* DNS Setup
  * For all of the instances to work together the machines need to find each other.
  * The best and easiest way to do this is to use a [Amazon Route53](http://aws.amazon.com/route53/) hosted domain. If you do not have one the script will attempt to emulate DNS by populating /etc/hosts in each of your servers.
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
* In the directory you ran the script from there will be a config.json file which stores information about your cluster... keep this someplace handy.
* To terminate your cluster and restart you can run
```
nuodb_aws_quickstart.py -a terminate -c /YOUR/CONFIG/FILE.json
nuodb_aws_quickstart.py -a create -c /YOUR/CONFIG/FILE.json
```
* Enjoy NuoDB!
