#!/usr/bin/python3

###############################################################
# Given two APIs with Authentication
# API1
# API2
# 
# Given 2 policies
# Pol1 gives access to API1
# Pol2 gives access to API2
# 
# Create Key based on Pol1
# Key1
# 
# Access API1 using the Key1
# Add Pol2 to Key1
# 
# Access API2 using Key1
###############################################################

import json
import requests
import os
import getopt
import sys
import time
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/../python/module')
import tyk
# Suppress the warnings from urllib3 when using a self signed certs
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --API1 <API1_listen_path> --API2 <API2_listen_path> --Pol1 <policy_for_API1> --Pol2 <policy_for_API2> --dashboard <dashboard URL> --gateway <gateway URL> --cred <dashboard credentials>')
    print("    trying to resolve a ticket issue")
    sys.exit(1)

dshb = ""
auth = ""
API1 = ""
API2 = ""
Pol1= ""
Pol2= ""
gateway= ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "API1=", "API2=", "Pol1=", "Pol2=", "gateway=", "dashboard=", "cred=", "verbose"])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--API1':
        API1 = arg
    elif opt == '--API2':
        API2 = arg
    elif opt == '--Pol1':
        Pol1 = arg
    elif opt == '--Pol2':
        Pol2 = arg
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--gateway':
        gateway = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb or API1 or API2 or Pol1 or Pol2 or gateway or auth):
    printhelp()

dashboard = tyk.dashboard(dshb, auth)

# create key based on Pol1
KeyTemplate = {
  "apply_policies": [],
  "allowance": 0,
  "per": 0,
  "quota_max": 0,
  "rate": 0,
  "meta_data": {"Created by": scriptName}
}

print(f'[INFO]Creating key from the first policy: {Pol1}')
KeyTemplate["apply_policies"].append(Pol1)
resp = dashboard.createKey(KeyTemplate)
APIKey=resp.json()["key_id"]
print(f'[INFO]Key created: {APIKey}')

# Show the key to verify it
if verbose:
    print(f'[INFO]Contents of key {APIKey} with only pol1')
    print(json.dumps(dashboard.getKey(APIKey).json(), indent=2))

# test that API1 works
print(f'[INFO]Calling {gateway}/{API1} with that key')
headers = {'Authorization' : APIKey}
resp = requests.get(f'{gateway}/{API1}', verify=False, headers=headers)
print(f'[{resp.status_code}], {resp.text}')

# add the second Policy to the key
print(f'[INFO]Adding Policy {Pol2} to key {APIKey}')
KeyTemplate = {
  "apply_policies": [],
  "allowance": 0,
  "per": 0,
  "quota_max": 0,
  "rate": 0,
  "meta_data": {"Created by": scriptName}
}
KeyTemplate["apply_policies"].append(Pol2)
KeyTemplate["apply_policies"].append(Pol1)
resp = dashboard.updateKey(json.dumps(KeyTemplate), APIKey)

# Show the key to verify it
if verbose:
    print(f'[INFO]Contents of {APIKey} after adding Pol2')
    print(json.dumps(dashboard.getKey(APIKey).json(), indent=2))

# test that the key work against API2
print(f'[INFO]Calling {gateway}/{API2} with the same keyid')
resp = requests.get(f'{gateway}/{API2}', verify=False, headers=headers)
print(f'[{resp.status_code}], {resp.text}')
