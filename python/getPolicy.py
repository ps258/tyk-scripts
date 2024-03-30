#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --cred <Dashboard API key|Gateway secret> --policy <policy id to fetch>')
    print("    Retrieve and print the policy")
    sys.exit(1)

dshb = ""
gatw = ""
auth = ""
policy = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "gateway=", "cred=", "policy=", "verbose"])
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
        policy = arg
    elif opt == '--verbose':
        verbose = 1

if not ((dshb or gatw) and auth and policy):
    printhelp()

# create a new dashboard or gateway object
if dshb:
    tykInstance = tyk.dashboard(dshb, auth)
else:
    tykInstance = tyk.gateway(gatw, auth)

resp = tykInstance.getPolicy(policy)
print(json.dumps(resp.json(), indent=2))
if resp.status_code != 200:
    sys.exit(1)
