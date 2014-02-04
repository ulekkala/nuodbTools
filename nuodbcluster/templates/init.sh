#!/bin/bash

hostname $hostname
yum -y install git
curl -L https://www.opscode.com/chef/install.sh | bash
mkdir -p /var/chef/cookbooks
git clone https://github.com/nuodb/nuodb-chef.git /var/chef/cookbooks/nuodb
git clone https://github.com/socrata-cookbooks/java /var/chef/cookbooks/java
cat > /var/chef/data.json <<EOF
$chef_json
EOF
chef-solo -j /var/chef/data.json