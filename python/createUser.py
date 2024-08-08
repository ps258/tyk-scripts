#!/usr/bin/python3

###############################################################
# Reference for calling the dashboard.createAdminUser
# arguments are dashboard, dashboard admin secret, username, user password
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
parser.add_argument('--userEmail', '-e', required=True, dest='userEmail', help="User email address")
parser.add_argument('--userPassword', '-p', required=True, dest='userPassword', help="User password")
parser.add_argument('--userFirst', '-f', required=True, dest='userFirst', help="User first name")
parser.add_argument('--userLast', '-l', required=True, dest='userLast', help="User user last name")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

tykInstance = tyk.dashboard(args.dshb, "", args.adminSecret)

resp = tykInstance.getOrganisations()
if resp.status_code != 200:
    print(f'[FATAL]Unable to fetch organisations tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)
organisations = resp.json()
for org in organisations["organisations"]:
    if args.verbose:
        print(f'[INFO]Creating {args.userEmail} in {org["id"]=}')
    resp = tykInstance.createUser(args.userFirst, args.userLast, args.userEmail, args.userPassword, org["id"])
    print(json.dumps(resp.json(), indent=2))
