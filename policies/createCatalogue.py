#!/usr/bin/python3

import json
import requests
import os
import getopt
import sys

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials> --policy <policy id> --verbose')
    print("    Will create a catalogue entry for the policy given")
    sys.exit(2)

dshb = ""
auth = ""
policyId = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "cred=", "policyId=", "verbose"])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--policyId':
        policyId = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and auth and policyId):
    printhelp()

# read the policy defn
headers = {'Authorization' : auth}
# get the existing catalogue entries
resp = requests.get(f'{dshb}/api/portal/catalogue', headers=headers)
if resp.status_code != 200:
    print(resp.text)
    sys.exit(1)
catalogue = json.loads(resp.text)
# create a dictionary of all entry names
allnames = dict()
for policy in catalogue['apis']:
    name = policy["name"]
    allnames[name] = 1

headers["Content-Type"] = "application/json"
EntryName='api'
short_description = 'Short description for '
long_description = 'Long description for '
# find the first available name
i = 1
while EntryName+str(i) in allnames:
    i += 1
catalogue["apis"].append({"name": EntryName+str(i),\
        "short_description": short_description+str(i),\
        "long_description": long_description+str(i),\
        "show": True,\
        "policy_id": policyId,\
        "version": "v2"})

if verbose:
    print('[INFO]JSON being sent')
    print(json.dumps(catalogue, indent=2))


resp = requests.put(f'{dshb}/api/portal/catalogue', data=json.dumps(catalogue), headers=headers, allow_redirects=False)
print(resp.text)
