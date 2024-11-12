#!/usr/bin/python3

###############################################################
# Reference for calling the dashboard.getOrganisations
# arguments are dashboard and dashboard admin secret
###############################################################

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

parser = argparse.ArgumentParser(description=f'{scriptName}: Retrieves the organisations from dashboard')

parser.add_argument('--dashboard', '-d', required=True, dest='dshb', help="URL of the dashboard")
parser.add_argument('--adminSecret', '-a', required=True, dest='adminSecret', help="Dashboard admin secret")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

tykInstance = tyk.dashboard(args.dshb, "", args.adminSecret)

resp = tykInstance.getOrganisations()
if resp.status_code != 200:
    print(f'[FATAL]Tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)

organisations = resp.json()

for org in organisations["organisations"]:
    if args.verbose:
        print(json.dumps(org, indent=2))
    else:
        print(f'{org["id"]}, {org["owner_name"]}, {org["owner_slug"]}, {org["cname_enabled"]}, {org["cname"]}')
