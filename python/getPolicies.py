#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --cred <Dashboard API key|Gateway secret> [--verbose]]')
    print("    Will list Policy Name, Policyid, and APIids of each Policy found")
    sys.exit(1)

dshb = ""
gatw = ""
auth = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "gateway=", "cred=", "verbose"])
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
    elif opt == '--verbose':
        verbose = 1

if not ((dshb or gatw) and auth):
    printhelp()

# create a new dashboard or gateway object
if dshb:
    tyk = tyk.dashboard(dshb, auth)
else:
    tyk = tyk.gateway(gatw, auth)

def printPolicy(policy):
    if policy["id"] == "":
        policy["id"] = policy["_id"] 
    print(f'{policy["name"]};{policy["id"]}',end='')
    if "access_rights" in policy and policy["access_rights"] is not None:
        firstAPI=True
        for api in policy["access_rights"]:
            if firstAPI:
                print(f';{api}',end='')
                firstAPI=False
            else:
                print(f',{api}',end='')
        print('')
    else:
        print(',')

resp = tyk.getPolicies()
if resp.status_code != 200:
    print(f'[FATAL]Tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)
policies = resp.json()

if verbose:
    print(json.dumps(policies, indent=2))
else:
    print('# Name; policyID; API, API, ...')
    for policy in policies:
        printPolicy(policy)
