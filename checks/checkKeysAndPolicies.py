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
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/../python/module')
import tyk

# globals
dshb = ""
gatw = ""
verbose = 0
auth = ""

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --cred <Dashboard API key|Gateway secret>')
    sys.exit(2)

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

if not ((dshb or gatw) and auth ):
    printhelp()

# create a new dashboard or gateway object
if dshb:
    tyk = tyk.dashboard(dshb, auth)
else:
    tyk = tyk.gateway(gatw, auth)

# get keys
# /api/apis/keys/?p=-1 which just lists the key ids
# /api/keys/detailed/?p=-1 which dump the details of all the keys
resp = tyk.getKeys()
keys = resp.json()
# get policies
resp = tyk.getPolicies()
policies = resp.json()
# get APIs
resp = tyk.getAPIs()
APIs = resp.json()
if verbose:
    print(f'keys={keys}')
    print(f'policies={policies}')
    print(f'APIs={APIs}')

if verbose:
    print("List of all keys:")
    for key in keys["keys"]:
        print(key['key_id'])
    print("List of all policies:")
    for policy in policies:
        print(policy['name'])
    print("List of all APIs:")
    for API in APIs:
        print(API['api_definition']['name'], API['api_definition']['api_id'])

# load APIs into dict indexed by API ID for easy lookup
APIdetails = {}
for API in APIs:
    api_id = API['api_id']
    APIdetails[api_id] = API

# Key checks
for key in keys['keys']:
    key_id = key['key_id']
    key_org = key['data']['org_id']
    for keyAPI in key['data']['access_rights_array']:
        api_id = keyAPI['api_id']

        # Check that all APIs in the keys exist
        if verbose:
            print(f"[INFO]Key: {key_id}, checking API {api_id}")
        if not api_id in APIdetails:
            print(f"[FATAL]Key {key_id} refers to deleted API {api_id}")
        else:

            # Check that all APIs in the keys are enabled.
            if not APIdetails[api_id]['active']:
                print(f"[FATAL]Key {key_id} refers to inactive API {api_id}")

            # Check that all APIs in the keys are from the same org
            # this is unlikely to detect anything because unless a super user (account with no org_id)
            # is used the APIs will all be from the same org and the account making the request
            api_org = APIdetails[api_id]['org_id']
            if key_org != api_org:
                print(f"[FATAL]Key is in org {key_org} but API is in org {api_org}")


# Policy checks
for policy in policies:
    policy_id = policy['_id']
    policy_org = policy['org_id']
    #print(json.dumps(policy['access_rights'], indent=2))
    for policyAPI in policy['access_rights']:
        api_id = policy['access_rights'][policyAPI]['api_id']

        # Check that all APIs in the policy exist
        if verbose:
            print(f"[INFO]Policy: {policy_id}, checking API {api_id}")
        if not api_id in APIdetails:
            print(f"[FATAL]Policy {policy_id} refers to deleted API {api_id}")
        else:

            # Check that all APIs in the policy are enabled.
            if not APIdetails[api_id]['active']:
                print(f"[FATAL]Policy {policy_id} refers to inactive API {api_id}")

            # Check that all APIs in the policy are from the same org
            # this is unlikely to detect anything because unless a super user (account with no org_id)
            # is used the APIs will all be from the same org and the account making the request
            api_org = APIdetails[api_id]['org_id']
            if policy_org != api_org:
                print(f"[FATAL]Policy is in org {policy_org} but API is in org {api_org}")
