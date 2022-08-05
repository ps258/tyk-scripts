#!/usr/bin/python3

# The intent of this script is to check the APIs associated with policies and keys
# Checks are
# o. Do all APIs exist
# o. Are all APIs enabled

import json
import requests
import sys
import getopt
import os

# globals
dshb = ""
verbose = 0
auth = ""

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard_URL> --cred <Dashboard API credentials> [--verbose]')
    sys.exit(2)

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

if not (dshb or auth ):
    printhelp()

# get keys
# options are to call:
# /api/apis/keys/?p=-1 which just lists the key ids
# /api/keys/detailed/?p=-1 which dump the details of all the keys
auth_header = {'Authorization' : auth}
resp = requests.get(f'{dshb}/api/keys/detailed/?p=-1', headers=auth_header)
keys = json.loads(resp.text)

if verbose:
    print("List of all keys:")
    for keyid in keys['keys']:
        print(keyid['key_id'])
sys.exit(1)

# get policies

# get APIs
