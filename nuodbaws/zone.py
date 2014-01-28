import boto.ec2
import boto.route53
from paramiko import SSHClient, SFTPClient
from string import Template
import os, socket, sys, time

class NuoDBzone:
    def __init__(self, name):
        self.name = name
    def connect(self, aws_access_key, aws_secret):
        self.connection = boto.ec2.connect_to_region(self.name, aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret)
        return self.connection
    def edit_security_group(self, name, description="EMPTY", rules=[]):
        errorstr = ""
        exists = False
        
        for security_group in self.connection.get_all_security_groups():
            if security_group.name == name:
                securityGroup = security_group
                exists = True
        if not exists:
            securityGroup = self.connection.create_security_group(name, description)
        for rule in rules:
            try:
                self.__add_security_group_rule(securityGroup=securityGroup, protocol=rule['protocol'], from_port=rule['from_port'], to_port=rule['to_port'], cidr_ip=rule['cidr_ip'])
            except Exception, e:
                pass
    def __add_security_group_rule(self, securityGroup, protocol, from_port, to_port, cidr_ip, src_group=None, dry_run=None):
        securityGroup.authorize(ip_protocol=protocol, from_port=from_port, to_port=to_port, cidr_ip=cidr_ip)
    def get_amis(self):
      return self.connection.get_all_images(owners="self")
