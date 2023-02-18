#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.environ.get("HOME")}/code/tyk-scripts/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials>')
    print("    Will list Policyid, name and apiids of each Policy found")
    sys.exit(1)

dshb = ""
auth = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "cred=", "verbose"])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and auth):
    printhelp()

dashboard = tyk.dashboard(dshb, auth)

# get the existing Policies
policies = dashboard.getPolicies().json()
print('# Name, policyID, APIs')
for policy in policies['Data']:
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
