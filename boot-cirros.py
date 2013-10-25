#!/usr/bin/env python -u
'''

This script does the following

1. Connect the router to the public network
2. Add a public key
3. Boot a cirros instance
4. Attach a floating IP


'''
from __future__ import print_function


import socket
import os.path
import sys
import time

from novaclient.v1_1 import client as novaclient
from neutronclient.v2_0 import client as neutronclient


auth_url = "http://192.168.27.100:35357/v2.0"
username = "demo"
password = "password"
tenant_name = "demo"

neutron = neutronclient.Client(auth_url=auth_url,
                                    username=username,
                                    password=password,
                                    tenant_name=tenant_name)

nova = novaclient.Client(auth_url=auth_url,
                         username=username,
                         api_key=password,
                         project_id=tenant_name)


print("Creating keypair: mykey...")
if not nova.keypairs.findall(name="mykey"):
    with open(os.path.expanduser('~/.ssh/id_rsa.pub')) as fpubkey:
        nova.keypairs.create(name="mykey", public_key=fpubkey.read())
print("done")

print("Booting cirros instance...", end='')
image = nova.images.find(name="cirros-0.3.1-x86_64-uec")
flavor = nova.flavors.find(name="m1.nano")
instance = nova.servers.create(name="cirros", image=image, flavor=flavor,
                              key_name="mykey")

# Poll at 5 second intervals, until the status is no longer 'BUILD'
status = instance.status
while status == 'BUILD':
    time.sleep(5)
    # Retrieve the instance again so the status field updates
    instance = nova.servers.get(instance.id)
    status = instance.status
print("done")


print("Creating floating ip...", end='')
# Get external network
ext_net, = [x for x in neutron.list_networks()['networks']
                    if x['router:external']]

# Get the port corresponding to the instance
port, = [x for x in neutron.list_ports()['ports']
                 if x['device_id'] == instance.id]

# Create the floating ip
args = dict(floating_network_id=ext_net['id'],
            port_id=port['id'])
ip_obj = neutron.create_floatingip(body={'floatingip': args})
print("done")

ip = ip_obj['floatingip']['floating_ip_address']
print("IP:{}".format(ip))

print("Waiting for ssh to be ready on cirros instance...", end='')
for i in range(60):
    try:
        seconds_to_wait = 1
        ssh_port = 22
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(seconds_to_wait)
        s.connect((ip, ssh_port))
    except socket.timeout:
        pass
    except socket.error:
        pass
    else:
        print("done")
        break
else:
    print("ssh server never came up!")
    sys.exit(1)




