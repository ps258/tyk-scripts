#!/usr/bin/python3

# may not work with gateway because of the policy id field

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

parser = argparse.ArgumentParser(description=f'{scriptName}: Will take the template and apply it to the policy id given')

DashboardOrGateway = parser.add_mutually_exclusive_group(required=True)
DashboardOrGateway.add_argument('--dashboard', '-d', dest='dshb', help="URL of the dashboard")
DashboardOrGateway.add_argument('--gateway', '-g', dest='gatw', help="URL of the gateway")

parser.add_argument('--cred', '-c', required=True, dest='auth', help="Dashboard API key or Gateway secret")
parser.add_argument('--template', '-t', required=True, dest='policyJSON', help="File containing the Policy JSON")
parser.add_argument('--policyid', '-p', required=True, dest='policyid', help="ID of the policy")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

# create a dashboard or gateway object
if args.dshb:
    tykInstance = tyk.dashboard(args.dshb, args.auth)
else:
    tykInstance = tyk.gateway(args.gatw, args.auth)

# read the policy defn
with open(args.policyJSON) as PolicyFile:
    policy = json.load(PolicyFile)
    PolicyFile.close()

print(f'Adding policy {policy["name"]}')
if args.verbose:
    print(json.dumps(policy, indent=2))

resp = tykInstance.updatePolicy(policy, args.policyid)
print(json.dumps(resp.json(), indent=2))
if resp.status_code != 200:
    print(f'[FATAL]{scriptName}: Tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)
