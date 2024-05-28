#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

parser = argparse.ArgumentParser(description=f'{scriptName}: Will add any available APIs into the policy named. There is no way to select which APIs are added')

parser.add_argument('-d', '--dashboard', required=True, dest='dshb', help="URL of the dashboard")
parser.add_argument('-p', '--policy', required=True, dest='policy', help="Policy ID to add APIs to")
parser.add_argument('-c', '--cred', required=True, dest='auth', help="Access credential")
parser.add_argument('-n', '--number', required=True, type=int, dest='toAdd', help="Number of APIs to add to the policy")
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()
args.dshb = args.dshb.strip().rstrip('/')

tykInstance = tyk.dashboard(args.dshb, args.auth)

# get the polcy
policy = tykInstance.getPolicy(args.policyID).json()
if args.verbose:
    keycount = len(policy["access_rights"])
    print(f'Policy {policyID} has {keycount} APIs attached')
# get the APIs
apis = tykInstance.getAPIs()
#print(json.dumps(apis.json(), indent=2, sort_keys=True))
if args.verbose:
    keycount = len(apis.json())
    print(f'A total of {keycount} APSs are defined')
addedCount = 0
for api in apis.json()["apis"]:
    api=api["api_definition"]
    #print(json.dumps(api, indent=2, sort_keys=True))
    apiid=api["api_id"]
    apiName = api["name"]
    if addedCount < args.toAdd:
        if not apiid in policy["access_rights"]:
            #print(json.dumps(policy["access_rights"], indent=2, sort_keys=True))
            if args.verbose:
                print(f'Adding {apiid}, {apiName}')
            policy["access_rights"][apiid] = {
                "api_name": apiName,
                "api_id": apiid,
                "versions": [ "Default" ],
                "allowed_urls": [],
                "restricted_types": [],
                "limit": None,
                "allowance_scope": ""
            }
            policy["access_rights_array"].append({
                "allowance_scope": "",
                "allowed_urls": [],
                "api_id": apiid,
                "api_name": apiName,
                "limit": None,
                "restricted_types": [],
                "versions": [ "Default" ]
            })
            addedCount+=1
        else:
            if args.verbose:
                print(f'Skipping {apiid}, {apiName}, already attached')
    else:
        continue
if addedCount < args.toAdd:
    print(f'Only able to add {addedCount} APIs because because there too fews APIs defined')
print(f'Policy {policyID} will have a total of {len(policy["access_rights"])} APIs attached')
if args.verbose:
    print(json.dumps(policy, indent=2, sort_keys=True))
print("Uploading policy to dashboard")
resp = tykInstance.updatePolicy(json.dumps(policy), policyID)
print(json.dumps(resp.json()))
if resp.status_code != 200:
    sys.exit(1)
