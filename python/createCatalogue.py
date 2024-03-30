#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials> --policy <policy id> --verbose')
    print("    Will create a catalogue entry for the policy given")
    sys.exit(1)

dshb = ""
auth = ""
policyId = ""
verbose = 0
show = True

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "cred=", "policyId=", "noShow", "verbose"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--noShow':
        show = False
    elif opt == '--policyId':
        policyId = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and auth and policyId):
    printhelp()

tykInstance = tyk.dashboard(dshb, auth)

catalogue = tykInstance.getCatalogue().json()
# create a dictionary of all entry names
allnames = dict()
for policy in catalogue['apis']:
    name = policy["name"]
    allnames[name] = 1

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
        "show": show,\
        "policy_id": policyId,\
        "version": "v2"})

if verbose:
    print('[INFO]JSON being sent')
    print(json.dumps(catalogue, indent=2))


print(f'Adding catalogue entry {EntryName+str(i)}')
resp = tykInstance.updateCatalogue(json.dumps(catalogue))
print(resp)
