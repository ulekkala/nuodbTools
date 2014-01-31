#!/bin/bash

if [ ! -f /var/chef/data.json ];
then
echo "Please create a /var/chef/data.json file that looks like https://raw.github.com/nuodb/dbaas/master/solo_install/data.json"
fi

# install chef
yum -y install git
curl -L https://www.opscode.com/chef/install.sh | bash
git clone https://github.com/nuodb/nuodb-chef.git /var/chef/cookbooks/nuodb
git clone https://github.com/socrata-cookbooks/java /var/chef/cookbooks/java
chef-solo -j /var/chef/data.json