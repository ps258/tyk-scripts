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
    print("    Will create policy for the API_ID given")
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
    tykInstance = tyk.dashboard(dshb, auth)
else:
    tykInstance = tyk.gateway(gatw, auth)

# read the policy defn
with open(templateFile) as PolicyFile:
    policy = json.load(PolicyFile)
    PolicyFile.close()
PolicyName = "Policy"
# get the existing Policies
policies = tykInstance.getPolicies()
if policies.status_code == 200:
    #print(f'[FATAL]{scriptName}: Tyk returned {policies.status_code}', file=sys.stderr)
    # create a dictionary of all policy names
    allnames = dict()
    for pol in policies.json()["policies"]:
        name = pol["name"]
        allnames[name] = 1

    # find the first available name
    i = 1
    while PolicyName+str(i) in allnames:
        i += 1
    policy["name"]=PolicyName+str(i)
    policy["access_rights"][apiid] = {
            "api_id": "' + apiid + '",
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
            "api_name": "",
            "limit": None,
            "restricted_types": [],
            "versions": [ "Default" ]
        })
else:
    # Just use the existing json
    policy["access_rights"][apiid] = {
        "api_id": "' + apiid + '",
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
        "api_name": "",
        "limit": None,
        "restricted_types": [],
        "versions": [ "Default" ]
        })

if verbose:
    print(json.dumps(policy, indent=2))

resp = tykInstance.createPolicy(policy)
if resp.status_code != 200:
    print(f'[FATAL]{scriptName}: Tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)
else:
    print(json.dumps(resp.json(), indent=2))
