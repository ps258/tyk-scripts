#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --cred <Dashboard API key or Gateway secret> --policy <policy ID> --number = <number of keys to create> --verbose')
    print("    Will create keys from the given policy or policies taking the defaults from them")
    sys.exit(1)

dshb = ""
gatw = ""
auth = ""
policyID = ""
verbose = 0
number = 1

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "gateway=", "cred=", "policy=", "number=", "verbose"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--gateway':
        gatw = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--policy':
        policyID = arg
    elif opt == '--number':
        number = int(arg)
    elif opt == '--verbose':
        verbose = 1

if not ((dshb or gatw) and policyID):
    printhelp()

# create a new dashboard or gateway object
if dshb:
    tyk = tyk.dashboard(dshb, auth)
else:
    tyk = tyk.gateway(gatw, auth)

TykKey = {
  "apply_policies": [],
  "allowance": 0,
  "per": 0,
  "quota_max": 0,
  "rate": 0,
  "meta_data": {"Created by": scriptName}
}

for pol in policyID.split(","):
    TykKey["apply_policies"].append(pol)

for x in range(number):
    resp = tyk.createKey(json.dumps(TykKey))

    if verbose:
        print(json.dumps(resp.json(), indent=2))
    else:
        respJSON = resp.json()
        if "key_id" in respJSON:
            print(json.dumps(respJSON()["key_id"], indent=2))
        else:
            print(json.dumps(respJSON["key"]))
    if resp.status_code != 200:
        sys.exit(1)
