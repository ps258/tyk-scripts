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

parser = argparse.ArgumentParser(description=f'{scriptName}: Create an admin user in all orgs in the dashboard instance')

parser.add_argument('-d', '--dashboard', required=True, dest='dshb', help="URL of the dashboard")
parser.add_argument('-a', '--adminSecret', required=True, dest='adminSecret', help="Dashboard admin secret")
parser.add_argument('-e', '--userEmail', required=True, dest='userEmail', help="User email address")
parser.add_argument('-p', '--userPassword', required=True, dest='userPassword', help="User password")
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

tykInstance = tyk.dashboard(args.dshb, "", args.adminSecret)

organisations = tykInstance.getOrganisations().json()
for org in organisations["organisations"]:
    if args.verbose:
        print(f'[INFO]Creating {args.userEmail} in {org["id"]=}')
    resp = tykInstance.createAdminUser(args.userEmail, args.userpass, org["id"])
    print(json.dumps(resp.json(), indent=2))
