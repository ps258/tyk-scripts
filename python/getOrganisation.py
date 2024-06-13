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

parser.add_argument('-d', '--dashboard', required=True, dest='dshb', help="URL of the dashboard")
parser.add_argument('-a', '--adminsecret', required=True, dest='adminsecret', help="Dashboard admin secret")
parser.add_argument('-o', '--orgid', required=True, dest='orgid', help="Orgid to retrieve")
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

tykInstance = tyk.dashboard(args.dshb, "", args.adminsecret)

resp = tykInstance.getOrganisation(args.orgid)
if resp.status_code != 200:
    sys.exit(1)

organisation = resp.json()
print(json.dumps(organisation, indent=2))
