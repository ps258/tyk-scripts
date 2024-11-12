#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

description = "Will take the template, apply the name (if given) then add it as a policy to the dashboard or gateway"
parser = argparse.ArgumentParser(description=f'{scriptName}: {description}')
DashboardOrGateway = parser.add_mutually_exclusive_group(required=True)
DashboardOrGateway.add_argument('--dashboard', '-d', dest='dshb', help="URL of the dashboard")
DashboardOrGateway.add_argument('--gateway', '-g', dest='gatw', help="URL of the gateway")
parser.add_argument('--cred', '-c', required=True, dest='auth', help="Dashboard API key or Gateway secret")
parser.add_argument('--apiid', '-a', dest='apiid', help="API ID")
parser.add_argument('--template', '-t', required=True, dest='templateFile', help="API template file")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")
args = parser.parse_args()

# create a new dashboard or gateway object
if args.dshb:
    tykInstance = tyk.dashboard(args.dshb, args.auth)
else:
    tykInstance = tyk.gateway(args.gatw, args.auth)

# read the policy defn
with open(args.templateFile) as PolicyFile:
    policy = json.load(PolicyFile)
    PolicyFile.close()
PolicyName = "Policy"
# get the existing Policies
policies = tykInstance.getPolicies()
if policies.status_code == 200:
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
    policy["access_rights"][args.apiid] = {
            "api_id": "' + args.apiid + '",
            "versions": [ "Default" ],
            "allowed_urls": [],
            "restricted_types": [],
            "limit": None,
            "allowance_scope": ""
        }
    policy["access_rights_array"].append({
            "allowance_scope": "",
            "allowed_urls": [],
            "api_id": args.apiid,
            "api_name": "",
            "limit": None,
            "restricted_types": [],
            "versions": [ "Default" ]
        })
else:
    # Just use the existing json
    policy["access_rights"][args.apiid] = {
        "api_id": "' + args.apiid + '",
        "versions": [ "Default" ],
        "allowed_urls": [],
        "restricted_types": [],
        "limit": None,
        "allowance_scope": ""
        }
    policy["access_rights_array"].append({
        "allowance_scope": "",
        "allowed_urls": [],
        "api_id": args.apiid,
        "api_name": "",
        "limit": None,
        "restricted_types": [],
        "versions": [ "Default" ]
        })

if args.verbose:
    print(json.dumps(policy, indent=2))

resp = tykInstance.createPolicy(policy)
if resp.status_code != 200:
    print(f'[FATAL]{scriptName}: Tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)
print(json.dumps(resp.json(), indent=2))
