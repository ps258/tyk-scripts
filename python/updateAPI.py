#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

description = "Will take the template and apply it to the APIid given"
parser = argparse.ArgumentParser(description=f'{scriptName}: {description}')

DashboardOrGateway = parser.add_mutually_exclusive_group(required=True)
DashboardOrGateway.add_argument('--dashboard', '-d', dest='dshb', help="URL of the dashboard")
DashboardOrGateway.add_argument('--gateway', '-g', dest='gatw', help="URL of the gateway")

parser.add_argument('--cred', '-c', required=True, dest='auth', help="Dashboard API key or Gateway secret")
parser.add_argument('--apiid', '-a', required=True, dest='apiid', help="API ID")
parser.add_argument('--template', '-t', required=True, dest='templateFile', help="Template to apply")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

# create a new dashboard or gateway object
if args.dshb:
    tykInstance = tyk.dashboard(args.dshb, args.auth)
else:
    tykInstance = tyk.gateway(args.gatw, args.auth)

# read the API defn
with open(args.templateFile) as APIFile:
    APIjson=json.load(APIFile)
    APIFile.close()

# set the api_id in the definition
if "api_definition" in APIjson:
    APIjson["api_definition"]["api_id"] = args.apiid
elif "api_id" in APIjson:
    APIjson["api_id"] = args.apiid
else:
    print('[FATAL]Unable to find "api_id" to update')

resp = tykInstance.updateAPI(json.dumps(APIjson), args.apiid)
print(json.dumps(resp.json()))
if resp.status_code != 200:
    print(f'[FATAL]{scriptName}: Tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)
