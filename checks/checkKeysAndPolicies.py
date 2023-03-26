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
verbose = 0
auth = ""

scriptName = os.path.basename(__file__)

def check_access_rights(name, ID, access_rights_array, access_rights):
    API_IDs = {}
    # check that all APIs in access_rights_array also exist in access_rights
    for API in access_rights_array:
        api_id = API['api_id']
        if not api_id in access_rights:
            print(f"[WARN]{name} {ID}: API {api_id} in access_rights_array but not in access_rights")
        # keep the api_id to make checking in reverse easier
        API_IDs[api_id] = 1
    # check that all APIs in access_rights are present in access_rights_array (actually API_IDs since that's easier)
    for api_id in access_rights:
        if not api_id in API_IDs:
            print(f"[WARN]{name} {ID}: API {api_id} in access_rights but not in access_rights_array")


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

dashboard = tyk.dashboard(dshb, auth)

# get keys
# /api/apis/keys/?p=-1 which just lists the key ids
# /api/keys/detailed/?p=-1 which dump the details of all the keys
resp = dashboard.getKeys()
keys = resp.json()
# get policies
resp = dashboard.getPolicies()
policies = resp.json()
# get APIs
resp = dashboard.getAPIs()
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
    for policy in policies['Data']:
        print(policy['name'])
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

    # Check that Key access_rights_array and access_rights match?
    check_access_rights("Key", key_id, key['data']['access_rights_array'], key['data']['access_rights'])

# Policy checks
for policy in policies['Data']:
    policy_id = policy['_id']
    policy_org = policy['org_id']
    for policyAPI in policy['access_rights_array']:
        api_id = policyAPI['api_id'] 

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

    # Check that policy access_rights_array and access_rights match?
    check_access_rights("Policy", policy_id, policy['access_rights_array'], policy['access_rights'])
