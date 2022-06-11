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
    print(f'{scriptName} --policy <policy ID> --dashboard <dashboard URL> --cred <Dashboard API credentials> --number <number of APIs to add to the policy>')
    sys.exit(2)

#dshb = "http://10.0.0.21:3002"
#auth = "c384aaccf24242165405dac097248dca"
#policyID = "62a487c4411022005169806e"
#toAdd = 100

dshb = ""
auth = ""
policyID = ""
toAdd = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "policy=", "dashboard=", "cred=", "number="])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--policy':
        policyID = arg
    elif opt == '--dashboard':
        dshb = arg
    elif opt == '--cred':
        auth = arg
    elif opt == '--number':
        toAdd = int(arg)

if not (dshb or policyID or auth or toAdd):
    printhelp()

# get the polcy
headers = {'Authorization' : auth}
resp = requests.get(f'{dshb}/api/portal/policies/{policyID}', headers=headers)
policy = json.loads(resp.text)
#print(json.dumps(policy, indent=4, sort_keys=True))
# get the APIs
resp = requests.get(f'{dshb}/api/apis/?p=-1', headers=headers)
apis = json.loads(resp.text)
# print(json.dumps(apis, indent=4, sort_keys=True))
addedCount = 0
for api in apis['apis']:
    #print(json.dumps(api['api_definition'], indent=4, sort_keys=True))
    apiid=api["api_definition"]["api_id"]
    apiName = api["api_definition"]["name"]
    #print(f'ID: {apiid}')
    #print(f'Name: {apiName}')
    #for key in policy["access_rights"].keys():
    #    print(f'Key = {key}')
    if addedCount < toAdd:
        if not apiid in policy["access_rights"].keys():
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
            print(f'Skipping {apiid}, {apiName}')
if addedCount < toAdd:
    print(f'Only able to add {addedCount} APIs because because there too fews APIs defined')
#print(json.dumps(policy, indent=4, sort_keys=True))
print("Uploading policy to dashboard")
headers["Content-Type"] = "application/json"
resp = requests.put(f'{dshb}/api/portal/policies/{policyID}', data=json.dumps(policy, indent=4), headers=headers)
print(json.dumps(resp.text, indent=4, sort_keys=True))
exit(0)