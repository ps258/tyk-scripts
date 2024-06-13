#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

parser = argparse.ArgumentParser(description=f'{scriptName}: Will create policies for the API_ID given')

DashboardOrGateway = parser.add_mutually_exclusive_group(required=True)
DashboardOrGateway.add_argument('-d', '--dashboard', dest='dshb', help="URL of the dashboard")
DashboardOrGateway.add_argument('-g', '--gateway', dest='gatw', help="URL of the gateway")

parser.add_argument('-a', '--apiid', required=True, dest='apiid', help="API ID to use")
parser.add_argument('-c', '--cred', required=True, dest='auth', help="Dashboard API key or Gateway secret")
parser.add_argument('-n', '--name', dest='name', help="Base name of policy")
parser.add_argument('-N', '--number', default=1, type=int, dest='toAdd', help="Numer of policies to generate")
parser.add_argument('-t', '--template', required=True, dest='templateFile', help="Policy template file")
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

if not ((args.dshb or args.gatw) and args.templateFile and args.auth and args.apiid and args.toAdd):
    print("Invalid options")
    sys.exit(1)

# create a new dashboard or gateway object
if args.dshb:
    tykInstance = tyk.dashboard(args.dshb, args.auth)
else:
    tykInstance = tyk.gateway(args.gatw, args.auth)

# read the policy defn
with open(args.templateFile) as PolicyFile:
    PolicyJSON=json.load(PolicyFile)
    PolicyFile.close()

numberCreated = tykInstance.createPolicies(PolicyJSON, args.apiid, args.toAdd)

if numberCreated == args.toAdd:
    print(f'Success: {numberCreated} Policies created')
else:
    print(f'Failure: Only {numberCreated} of {args.toAdd} policies created')
    sys.exit(1)
