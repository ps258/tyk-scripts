#!/usr/bin/python3

###############################################################
# Reference for calling the dashboard.getOrganisation
# arguments are dashboard and dashboard admin secret
###############################################################

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

parser = argparse.ArgumentParser(description=f'{scriptName}: Get the org with the given orgid')

parser.add_argument('--dashboard', '-d', required=True, dest='dshb', help="URL of the dashboard")
parser.add_argument('--adminSecret', '-a', required=True, dest='adminSecret', help="Dashboard admin secret")
parser.add_argument('--orgid', '-o', required=True, dest='orgid', help="Orgid to retrieve")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

tykInstance = tyk.dashboard(args.dshb, "", args.adminSecret)

resp = tykInstance.getOrganisation(args.orgid)
if resp.status_code != 200:
    sys.exit(1)

print(json.dumps(resp.json(), indent=2))
