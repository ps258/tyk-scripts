#!/usr/bin/python3

# The intent of this script is to check the APIs associated with policies and keys
# Checks include
# o. Do all APIs exist
# o. Are all APIs enabled
# o. Are all APIs from the same org (this needs a super admin account, one without and orgid)

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

auth_header = {'Authorization' : auth}

# get keys
# options are to call:
# /api/apis/keys/?p=-1 which just lists the key ids
# /api/keys/detailed/?p=-1 which dump the details of all the keys
resp = requests.get(f'{dshb}/api/keys/detailed/?p=-1', headers=auth_header)
keys = json.loads(resp.text)

if verbose:
    print("List of all keys:")
    for key in keys['keys']:
        print(key['key_id'])

# get policies
resp = requests.get(f'{dshb}/api/portal/policies/?p=-1', headers=auth_header)
policies = json.loads(resp.text)

if verbose:
    print("List of all policies:")
    for policy in policies['Data']:
        print(policy['name'])

# get APIs
resp = requests.get(f'{dshb}/api/apis/?p=-1', headers=auth_header)
APIs = json.loads(resp.text)

if verbose:
    print("List of all APIs:")
    for API in APIs['apis']:
        print(API['api_definition']['name'], API['api_definition']['api_id'])

# load APIs into dict indexed by API ID for easy lookup
APIdetails = {}
for API in APIs['apis']:
    api_id = API['api_definition']['api_id']
    APIdetails[api_id] = API['api_definition']

# Key checks
for key in keys['keys']:
    key_id = key['key_id']
    key_org = key['data']['org_id']
    for keyAPI in key['data']['access_rights_array']:
        api_id = keyAPI['api_id'] 

        # Check that all APIs in the keys exist
        print(f"Checking {api_id}")
        if not api_id in APIdetails:
            print(f"[FATAL]Key {key_id} refers to deleted API {api_id}")
        else:

            # Check that all APIs in the keys are enabled.
            if not APIdetails[api_id]['active']:
                print(f"[FATAL]Key {key_id} refers to inactive API {api_id}")

            # Check that all APIs in the keys from the same org
            # this is unlikely to detect anything because unless a super user (account with no org_id)
            # is used the APIs will all be from the same org and the account making the request
            api_org = APIdetails[api_id]['org_id']
            if key_org != api_org:
                print(f"[FATAL]Key is in org {key_org} but API is in org {api_org}")
# Check that access_rights_array and access_rights match?

# Policy checks
