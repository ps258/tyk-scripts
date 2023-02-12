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
import tyk
# Suppress the warnings from urllib3 when using a self signed certs
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --API1 <API1_listen_path> --API2 <API2_listen_path> --Pol1 <policy_for_API1> --Pol2 <policy_for_API2> --dashboard <dashboard URL> --gateway <gateway URL> --cred <dashboard credentials>')
    print("    trying to resolve a ticket issue")
    sys.exit(2)

dshb = ""
auth = ""
policyID = ""
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

if not (dshb or policyID or auth):
    printhelp()

dashboard = tyk.dashboard(dshb, auth)

# fetch Policies in preparation for updating the key after the first API call
pol1JSON = dashboard.getPolicy(Pol1)
pol2JSON = dashboard.getPolicy(Pol2)

# create key based on Pol1
KeyTemplate = {
  "apply_policies": [],
  "allowance": 0,
  "per": 0,
  "quota_max": 0,
  "rate": 0,
  "meta_data": {"Created by": scriptName}
}

KeyTemplate["apply_policies"].append(Pol1)
resp = dashboard.createKey(json.dumps(KeyTemplate))
APIKey=resp["key_id"]
print(f'Key created: {APIKey}')

# test that API1 works
print(f'Calling {gateway}/{API1}')
headers = {'Authorization' : APIKey}
resp = requests.get(f'{gateway}/{API1}', verify=False, headers=headers)
print(resp.text)

# add the second Policy to the key
KeyTemplate = {
  "apply_policies": [],
  "allowance": 0,
  "per": 0,
  "quota_max": 0,
  "rate": 0,
  "meta_data": {"Created by": scriptName}
}
KeyTemplate["apply_policies"].append(Pol1)
KeyTemplate["apply_policies"].append(Pol2)
resp = dashboard.updateKey(json.dumps(KeyTemplate), APIKey)

# show the results
#TykKey = dashboard.getKey(APIKey)
#print(json.dumps(TykKey, indent=2))
#resp = requests.get(f'{gateway}/{API1}', verify=False, headers=headers)

# test that the key work against API2
print(f'Calling {gateway}/{API2}')
resp = requests.get(f'{gateway}/{API2}', verify=False, headers=headers)
print(resp.text)
