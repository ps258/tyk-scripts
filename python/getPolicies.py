#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --cred <Dashboard API key|Gateway secret>')
    print("    Will list Policyid, name and apiids of each Policy found")
    sys.exit(1)

dshb = ""
gatw   = ""
auth = ""
verbose = 0

def printPolicy(policy):
    if verbose:
        print(json.dumps(policy, indent=2))
    else:
        print(f'{policy["name"]},{policy["_id"]}',end='')
        firstAPI=True
        for api in policy["access_rights"]:
            if firstAPI:
                print(f',{api}',end='')
                firstAPI=False
            else:
                print(f':{api}',end='')
        print('')

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

# get the existing Policies
policies = tyk.getPolicies().json()
if not verbose:
    print('# Name, policyID, APIs')
if 'Data' in policies:
    # dashboard format
    for policy in policies['Data']:
        printPolicy(policy)
else:
    # gateway format
    for policy in policies:
        printPolicy(policy)

