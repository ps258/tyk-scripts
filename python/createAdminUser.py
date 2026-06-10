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

parser = argparse.ArgumentParser(description=f'{scriptName}: Create an admin or super admin user')

parser.add_argument('--dashboard', '-d', required=True, dest='dshb', help="URL of the dashboard")
parser.add_argument('--adminSecret', '-a', required=True, dest='adminSecret', help="Dashboard admin secret")
parser.add_argument('--userEmail', '-e', required=True, dest='userEmail', help="User email address")
parser.add_argument('--userPassword', '-p', required=True, dest='userPassword', help="User password")
parser.add_argument('--orgid', '-o', required=False, dest='orgID', help="Orgainisation to create the account in")
parser.add_argument('--super', '-s', action='store_true', required=False, dest='isSuper', help="Create a super admin (no orgid)")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()
if args.isSuper:
    if args.orgID:
        print('[FATAL]Super admin users have no orgid')
        sys.exit(1)
else:
    if not args.orgID:
        print('[FATAL]Must specify an orgid for a non-super-admin user')
        sys.exit(1)

tykInstance = tyk.dashboard(args.dshb, "", args.adminSecret)

if args.isSuper:
    # create super admin user
    if args.verbose:
        print(f'[INFO]Creating super admin user {args.userEmail}')
    resp = tykInstance.createAdminUser(args.userEmail, args.userPassword, "")
    print(json.dumps(resp.json(), indent=2))
else:
    # create an ordinarly admin user
    organisations = tykInstance.getOrganisations().json()
    if org in organisations["organisations"]:
        if args.verbose:
            print(f'[INFO]Creating {args.userEmail} in {org["id"]=}')
        resp = tykInstance.createAdminUser(args.userEmail, args.userPassword, org["id"])
        print(json.dumps(resp.json(), indent=2))
