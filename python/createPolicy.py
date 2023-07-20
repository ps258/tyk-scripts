#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --cred <Dashboard API key|Gateway secret> --template <Policy template file> --apiid <apiid> --verbose')
    print("    Will create a new unique policy for the API_ID given")
    sys.exit(1)

dshb = ""
gatw = ""
auth = ""
templateFile = ""
apiid = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "gateway=", "template=", "cred=", "apiid=", "verbose"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--template':
        templateFile = arg
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--gateway':
        gatw = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--apiid':
        apiid = arg
    elif opt == '--verbose':
        verbose = 1

if not ((dshb or gatw) and templateFile and auth and apiid):
    printhelp()

# create a new dashboard or gateway object
if dshb:
    tyk = tyk.dashboard(dshb, auth)
else:
    tyk = tyk.gateway(gatw, auth)

# read the policy defn
with open(templateFile) as PolicyFile:
    PolicyJSON=json.load(PolicyFile)
    PolicyFile.close()
PolicyName = "Policy"
# get the existing Policies
policies = tyk.getPolicies().json()
# create a dictionary of all policy names
allnames = dict()
for policy in policies:
    name = policy["name"]
    allnames[name] = 1

# find the first available name
i = 1
while PolicyName+str(i) in allnames:
    i += 1
PolicyJSON["name"]=PolicyName+str(i)
PolicyJSON["access_rights"][apiid] = json.loads('{ "api_id": "' + apiid + '", "versions": [ "Default" ], "allowed_urls": [], "restricted_types": [], "limit": null, "allowance_scope": "" }')

print(f'Adding policy {PolicyJSON["name"]}')
if verbose:
    print(json.dumps(PolicyJSON, indent=2))

resp = tyk.createPolicy(json.dumps(PolicyJSON))
print(resp.json())
if resp.status_code != 200:
    sys.exit(1)
