####
NuoDB DataBase As A Service cluster creation scripts
####

Basic toolset for bringing up a NuoDB cluster. See create.py and terminate.py for usage examples.


# How to use Nuodb AWS cluster creation scripts:
************

## Preparation:
************
* DNS Setup
  * These scripts assume you have a domain that has its records hosted in [Amazon's Route53][http://aws.amazon.com/route53/] and that your AWS credentials have the ability to modify that account. Please see the Route53 documents for how to achieve this.
  * Determine which regions to use
  * Amazon has (as of this writing) 8 different regions. You should determine which zones you wish to use and take note of the AMIs for each one. The appropriate AMIs can be found [here][https://github.com/nuodb/dbaas/blob/master/amis.md].
  * In each region you should determine the subnets for each zone you want to use. Amazon subnet IDs are in the format 'subnet-aaaaaaaa'. You can determine available subnets by using a URL similar to this one and changing the region: `https://console.aws.amazon.com/vpc/home?region=ap-southeast-1#s=subnets`
  * You may use multiple subnets from each region if you like. Instances will be evenly distributed over the subnets.
* Security Zones
  * At a minimum you should allow access to the NuoDB ports listed [here][http://doc.nuodb.com/display/doc/Linux+Installation]. If you are doing multi-region then ensure traffic is allowed from other regions. Take note of each of the ids (sg-aaaaaaaa) of the security groups you want to use in each region
* SSH keys & AWS credentials
  * You should know the name of valid ssh key for each environment and have the private keys for your account accessible.
  * You should know your AWS access key and AWS secret key


## Execution:
************
* Make sure you have python installed
* Install [Boto][https://github.com/boto/boto/tree/master]
* Git clone this repo
* In the root of the newly cloned directory make a file called [config.json][config.json.example] using the data you gathered above
* To create your cluster run create.py
* To delete your cluster run terminate.py

## Notes:
* Persistent data is stored in a file inside your cloned directory root in a directory called /data. If you delete this file then the create & terminate scripts may not behave correctly because they cannot determine cluster state. If this happens you will have to control the instances manually. 


