#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --cred <Dashboard API credentials>')
    print("    Will list APIID and name of each API found")
    sys.exit(1)

dshb = ""
gw   = ""
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
        gw = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--verbose':
        verbose = 1

if not ((bool(dshb) ^ bool(gw)) and auth):
    printhelp()

if (dshb):
    tyk = tyk.dashboard(dshb, auth)
else:
    tyk = tyk.gateway(gw, auth)

resp = tyk.getAPIs()
if resp.status_code != 200:
    print(json.dumps(resp.json()))
    sys.exit(1)

if 'apis' in resp.json():
    # dashboard
    for api in resp.json()['apis']:
        if verbose:
            print(json.dumps(api, indent=2))
        else:
            print(f'{api["api_definition"]["name"]},{api["api_definition"]["api_id"]}')
else:
    # gateway
    for api in resp.json():
        if verbose:
            print(json.dumps(api, indent=2))
        else:
            print(f'{api["name"]},{api["api_id"]}')
