#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials> --policyid <polid>')
    print("    Will delete ALL policies from the dashboard")
    sys.exit(1)

dshb = ""
auth = ""
policyid = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "cred=", "policyid=", "verbose"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--policyid':
        policyid = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and auth and policyid):
    printhelp()

dashboard = tyk.dashboard(dshb, auth)

resp = dashboard.deletePolicy(policyid)
print(json.dumps(resp.json(), indent=2))
if resp.status_code != 200:
    sys.exit(1)
