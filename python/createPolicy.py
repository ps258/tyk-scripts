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
parser.add_argument('--name', '-n', default="Default policy name", dest='name', help="Base name of policy")
parser.add_argument('--apiid', '-a', dest='apiids', nargs='+', help="List of API IDs to be added to the policy")
parser.add_argument('--template', '-t', required=False, dest='templateFile', help="API template file")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")
args = parser.parse_args()

# create a new dashboard or gateway object
if args.dshb:
    tykInstance = tyk.dashboard(args.dshb, args.auth)
else:
    tykInstance = tyk.gateway(args.gatw, args.auth)

# read the policy defn
if args.templateFile:
    policy = tyk.policy(args.templateFile)
else:
    policy = tyk.policy()
PolicyName = args.name
# get the existing Policies
policies = tykInstance.getPolicies()
if policies.status_code == 200:
    # create a dictionary of all policy names
    allnames = dict()
    for pol in policies.json()["policies"]:
        name = pol["name"]
        allnames[name] = 1

    # find the first available name
    if PolicyName in allnames:
        i = 1
        while PolicyName+str(i) in allnames:
            i += 1
        policy.setName(PolicyName+str(i))
    else:
        policy.setName(PolicyName)
    for apiid in args.apiids:
        policy.addAPI(apiid)
else:
    # Just use the existing json
    policy.setName(PolicyName)
    for apiid in args.apiids:
        policy.addAPI(apiid)

if args.verbose:
    print(policy)

resp = tykInstance.createPolicy(policy.json())
if resp.status_code != 200:
    print(f'[FATAL]{scriptName}: Tyk returned {resp.status_code}', file=sys.stderr)
print(json.dumps(resp.json(), indent=2))
