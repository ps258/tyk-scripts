#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --policy <policy ID> --dashboard <dashboard URL> --cred <Dashboard API credentials> --number <number of APIs to add to the policy> --verbose')
    print("    Will add any available APIs into the policy named. There is no way to select which APIs are added")
    sys.exit(1)

dshb = ""
auth = ""
policyID = ""
toAdd = 0
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "policy=", "dashboard=", "cred=", "number=", "verbose"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--policy':
        policyID = arg
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--number':
        toAdd = int(arg)
    elif opt == '--verbose':
        verbose = 1

if not (dshb and policyID and auth and toAdd):
    printhelp()

tykInstance = tyk.dashboard(dshb, auth)

# get the polcy
policy = tykInstance.getPolicy(policyID).json()
if verbose:
    keycount = len(policy["access_rights"])
    print(f'Policy {policyID} has {keycount} APIs attached')
# get the APIs
apis = tykInstance.getAPIs()
#print(json.dumps(apis.json(), indent=2, sort_keys=True))
if verbose:
    keycount = len(apis.json())
    print(f'A total of {keycount} APSs are defined')
addedCount = 0
for api in apis.json()["apis"]:
    api=api["api_definition"]
    #print(json.dumps(api, indent=2, sort_keys=True))
    apiid=api["api_id"]
    apiName = api["name"]
    if addedCount < toAdd:
        if not apiid in policy["access_rights"]:
            #print(json.dumps(policy["access_rights"], indent=2, sort_keys=True))
            if verbose:
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
            if verbose:
                print(f'Skipping {apiid}, {apiName}, already attached')
    else:
        continue
if addedCount < toAdd:
    print(f'Only able to add {addedCount} APIs because because there too fews APIs defined')
print(f'Policy {policyID} will have a total of {len(policy["access_rights"])} APIs attached')
if verbose:
    print(json.dumps(policy, indent=2, sort_keys=True))
print("Uploading policy to dashboard")
resp = tykInstance.updatePolicy(json.dumps(policy), policyID)
print(json.dumps(resp.json()))
if resp.status_code != 200:
    sys.exit(1)
