#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

description = "Returns the JSON for the given keyid"
parser = argparse.ArgumentParser(description=f'{scriptName}: {description}')

DashboardOrGateway = parser.add_mutually_exclusive_group(required=True)
DashboardOrGateway.add_argument('--dashboard', '-d', dest='dshb', help="URL of the dashboard")
DashboardOrGateway.add_argument('--gateway', '-g', dest='gatw', help="URL of the gateway")

parser.add_argument('--cred', '-c', required=True, dest='auth', help="Dashboard API key or Gateway secret")
parser.add_argument('--keyid', '-k', required=True, dest='keyid', help="Certificate ID")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")
args = parser.parse_args()

# create a dashboard or gateway object
if args.dshb:
    tykInstance = tyk.dashboard(args.dshb, args.auth)
else:
    tykInstance = tyk.gateway(args.gatw, args.auth)

resp = tykInstance.getKey(args.keyid)
if resp.status_code != 200:
    print(f'[FATAL]{scriptName}: Tyk returned {resp.status_code}', file=sys.stderr)
    print(json.dumps(resp.json()))
    sys.exit(1)
 
if args.verbose:
    print(json.dumps(resp.json(), indent=2))
else:
    tykInstance.printKeySummaryHeader()
    tykInstance.printKeySummary(resp.json())
