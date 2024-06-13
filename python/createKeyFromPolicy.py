#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

parser = argparse.ArgumentParser(description=f'{scriptName}: Will create a key from the given policies')

DashboardOrGateway = parser.add_mutually_exclusive_group(required=True)
DashboardOrGateway.add_argument('-d', '--dashboard', dest='dshb', help="URL of the dashboard")
DashboardOrGateway.add_argument('-g', '--gateway', dest='gatw', help="URL of the gateway")

parser.add_argument('-c', '--cred', required=True, dest='auth', help="Dashboard API key or Gateway secret")
parser.add_argument('-C', '--customKeyName', dest='keyName', help="Custom key name")
parser.add_argument('-p', '--policy', required=True, dest='policyID', nargs='+', help="List of policy IDs which the key is based on")
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

# create a new dashboard or gateway object
if args.dshb:
    tykInstance = tyk.dashboard(args.dshb, args.auth)
else:
    tykInstance = tyk.gateway(args.gatw, args.auth)

key = tyk.authKey()

for pol in args.policyID:
    key.addPolicy(pol)

if args.keyName:
    resp = tykInstance.createCustomKey(key.json(), args.keyName)
else:
    resp = tykInstance.createKey(key.json())

if args.verbose:
    print(json.dumps(resp.json(), indent=2))
else:
    respJSON = resp.json()
    if "key_id" in respJSON:
        print(respJSON["key_id"])
    else:
        print(respJSON["key"])
if resp.status_code != 200:
    sys.exit(1)
