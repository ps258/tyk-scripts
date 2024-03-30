#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --cred <Dashboard API key|Gateway secret> --policy <Policy json file> --verbose')
    print("    Will simply publish the policy to the dashboard or gateway unchanged")
    sys.exit(1)

dshb = ""
gatw = ""
auth = ""
policyJSON = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "gateway=", "policy=", "cred=", "verbose"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--policy':
        policyJSON = arg
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--gateway':
        gatw = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--verbose':
        verbose = 1

if not ((dshb or gatw) and policyJSON and auth):
    printhelp()

# create a new dashboard or gateway object
if dshb:
    tykInstance = tyk.dashboard(dshb, auth)
else:
    tykInstance = tyk.gateway(gatw, auth)

# read the policy defn
with open(policyJSON) as PolicyFile:
    policy = json.load(PolicyFile)
    PolicyFile.close()

print(f'Adding policy {policy["name"]}')
if verbose:
    print(json.dumps(policy, indent=2))

resp = tykInstance.createPolicy(policy)
print(json.dumps(resp.json(), indent=2))
if resp.status_code != 200:
    sys.exit(1)
