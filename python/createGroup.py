#!/usr/bin/python3

###############################################################
# Reference for calling the dashboard.createGroup
# arguments are dashboard, dashboard admin secret, group name, group description
###############################################################

import argparse
import json
import os
import sys
import time
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

parser = argparse.ArgumentParser(description=f'{scriptName}: Create a user in all orgs in the dashboard instance')

parser.add_argument('--dashboard', '-d', required=True, dest='dshb', help="URL of the dashboard")
parser.add_argument('--adminSecret', '-a', required=True, dest='adminSecret', help="Dashboard admin secret")
parser.add_argument('--groupName', '-n', required=True, dest='groupName', help="Group name")
parser.add_argument('--groupDesc', '-D', required=True, dest='groupDesc', help="Group description")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

tykInstance = tyk.dashboard(args.dshb, "", args.adminSecret)

resp = tykInstance.getOrganisations()
#if resp.status_code != 200:
#    print(f'[FATAL]Unable to fetch organisations tyk returned {resp.status_code}', file=sys.stderr)
#    sys.exit(1)
#organisations = resp.json()
#for org in organisations["organisations"]:
#    if args.verbose:
#        print(f'[INFO]Creating {args.userEmail} in {org["id"]=}')
resp = tykInstance.createGroup(args.groupName, args.groupDesc)
if resp.status_code != 200:
    print(f'[FATAL]Tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)
print(json.dumps(resp.json(), indent=2))
