#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials>')
    print("    Will list APIID and name of each API found")
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

resp = dashboard.getAPIs()
if resp.status_code != 200:
    print(json.dumps(resp.json()))
    sys.exit(1)
for api in resp.json()['apis']:
    if verbose:
        print(json.dumps(api, indent=2))
    else:
        print(f'{api["api_definition"]["name"]},{api["api_definition"]["api_id"]}')
