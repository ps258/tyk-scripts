#!/usr/bin/python3

import json
import os
import getopt
import sys
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials> --policy <policy id to fetch>')
    print("    Retrieve and print the policy")
    sys.exit(2)

dshb = ""
auth = ""
policy = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "cred=", "policy=", "verbose"])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--policy':
        policy = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and auth):
    printhelp()

dashboard = tyk.dashboard(dshb, auth)
policyJSON = dashboard.getPolicy(policy)
print(json.dumps(policyJSON, indent=2))
