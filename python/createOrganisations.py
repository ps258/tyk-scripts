#!/usr/bin/python3

###############################################################
# Reference for calling the dashboard.createOrganisations
###############################################################

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

parser = argparse.ArgumentParser(description=f'{scriptName}: Will create a number of new orgs with the given org name')

parser.add_argument('--dashboard', '-d', required=True, dest='dshb', help="URL of the dashboard")
parser.add_argument('--adminSecret', '-a', required=True, dest='adminSecret', help="Dashboard admin secret")
parser.add_argument('--cname', '-c', required=False, dest='cname', default='portal.cname.com', help="Portal CNAME")
parser.add_argument('--name', '-n', required=True, dest='ownerName', help="Organisation Name")
parser.add_argument('--number', '-N', required=True, dest='toAdd', type=int, help="Number of orgs to create")
parser.add_argument('--slug', '-s', required=False, dest='slug', help="Organisation Slug")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

if not args.slug:
    args.slug = args.ownerName

# create a new dashboard object
tykInstance = tyk.dashboard(args.dshb, "", args.adminSecret)

# Create the org data structure
orgDef = { "owner_name": args.ownerName, "owner_slug": args.slug, "cname_enabled": True, "cname": args.cname}

numberCreated = tykInstance.createOrganisations(orgDef, args.toAdd)
if numberCreated == args.toAdd:
    print(f'Success: {numberCreated} Orgs created')
else:
    print(f'Failure: Only {numberCreated} of {args.toAdd} Orgs created')
    sys.exit(1)
