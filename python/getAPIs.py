#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --cred <Dashboard API key or Gateway secret>')
    print("    Will list APIID and name of each API found")
    sys.exit(1)

dshb = ""
gatw   = ""
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
