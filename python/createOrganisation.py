#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

parser = argparse.ArgumentParser(description=f'{scriptName}: Will create a new org with the given org name')

parser.add_argument('-d', '--dashboard', required=True, dest='dshb', help="URL of the dashboard")
parser.add_argument('-a', '--adminsecret', required=True, dest='adminsecret', help="Dashboard admin secret")
parser.add_argument('-c', '--cname', required=False, dest='cname', default='portal.cname.com', help="Portal CNAME")
parser.add_argument('-n', '--name', required=True, dest='ownerName', help="Organisation Name")
parser.add_argument('-s', '--slug', required=False, dest='slug', help="Organisation Slug")
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

if not args.slug:
    args.slug = args.ownerName

# create a new dashboard object
tykInstance = tyk.dashboard(args.dshb, "", args.adminsecret)

# Create the org data structure
orgDef = { "owner_name": args.ownerName, "owner_slug": args.slug, "cname_enabled": True, "cname": args.cname}

resp = tykInstance.createOrganisation(orgDef)
print(json.dumps(resp.json()))
if resp.status_code != 200:
    sys.exit(1)
