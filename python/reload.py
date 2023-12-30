#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --gateway <gateway URL>] --cred Gateway secret --group')
    print("    Triggers a gateway reload or gateway group reload if --group is used")
    sys.exit(1)

gatw = ""
auth = ""
group = False

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "gateway=", "cred=", "group"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--gateway':
        gatw = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--group':
        group = True

if not (gatw and auth):
    printhelp()

# create a new dashboard or gateway object
tyk = tyk.gateway(gatw, auth)

if group:
    resp = tyk.reloadGroup()
else:
    resp = tyk.reload()
print(json.dumps(resp.json(), indent=2))
if resp.status_code != 200:
    sys.exit(1)
