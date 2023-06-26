#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --policy <policy ID> --dashboard <dashboard URL> --cred <Dashboard API credentials> --verbose')
    print("    Will create a key from the given policy taking the defaults from it")
    sys.exit(1)

dshb = ""
auth = ""
policyID = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "policy=", "dashboard=", "cred=", "verbose"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
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

dashboard = tyk.dashboard(dshb, auth)

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
resp = dashboard.createKey(json.dumps(TykKey))

if verbose:
    print(json.dumps(resp.json()), indent=2)
else:
    print(resp.json()["key_id"])
if resp.status_code != 200:
    sys.exit(1)
