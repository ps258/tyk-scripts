#!/usr/bin/python3

from audioop import add
from curses import tparm
import json
import requests
import os
import getopt
import sys

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --policy <policy ID> --dashboard <dashboard URL> --cred <Dashboard API credentials> --number <number of APIs to add to the policy> --verbose')
    print("    Will add any available APIs into the policy named. There is no way to select which APIs are added")
    sys.exit(2)

dshb = ""
auth = ""
policyID = ""
toAdd = 0
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "policy=", "dashboard=", "cred=", "number=", "verbose"])
except getopt.GetoptError:
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

if not (dshb or policyID or auth or toAdd):
    printhelp()

# get the polcy
headers = {'Authorization' : auth}
resp = requests.get(f'{dshb}/api/portal/policies/{policyID}', headers=headers)
policy = json.loads(resp.text)
if verbose:
    keycount = len(policy["access_rights"])
    print(f'Policy {policyID} has {keycount} APIs attached')
# get the APIs
resp = requests.get(f'{dshb}/api/apis/?p=-1', headers=headers)
apis = json.loads(resp.text)
# print(json.dumps(apis, indent=4, sort_keys=True))
addedCount = 0
for api in apis['apis']:
    apiid=api["api_definition"]["api_id"]
    apiName = api["api_definition"]["name"]
    if addedCount < toAdd:
        if not apiid in policy["access_rights"].keys():
            if verbose:
                print(f'Adding {apiid}, {apiName}')
            policy["access_rights"][apiid] = {
                "api_name": apiName,
                "api_id": apiid,
                "versions": [
                    "Default"
                ],
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
                "versions": [
                    "Default"
                ]
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
#print(json.dumps(policy, indent=4, sort_keys=True))
print("Uploading policy to dashboard")
headers["Content-Type"] = "application/json"
resp = requests.put(f'{dshb}/api/portal/policies/{policyID}', data=json.dumps(policy, indent=4), headers=headers)
print(resp.text)