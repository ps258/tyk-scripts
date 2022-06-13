#!/usr/bin/python3

from audioop import add
from curses import tparm
import json
import requests
import os
import getopt
import sys

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --policy <policy ID> --dashboard <dashboard URL> --cred <Dashboard API credentials> --verbose')
    print("    Will create a key from the given policy taking the defaults from it")
    sys.exit(2)

dshb = ""
auth = ""
policyID = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "policy=", "dashboard=", "cred=", "verbose"])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--policy':
        policyID = arg
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb or policyID or auth):
    printhelp()

TykKey = {
  "apply_policies": [],
  "allowance": 0,
  "per": 0,
  "quota_max": 0,
  "rate": 0,
  "meta_data": {"Created by": scriptName}
}

TykKey["apply_policies"].append(policyID)
headers = {'Authorization' : auth}
headers["Content-Type"] = "application/json"
resp = requests.post(f'{dshb}/api/keys', data=json.dumps(TykKey, indent=4), headers=headers)
print(resp.text)