#!/usr/bin/python3

import argparse
import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

adminEmail = "admin@tyk.io"
adminPassword = "ABC-123"
portalCNAME = "portal.cname.com"

parser = argparse.ArgumentParser(description=f'{scriptName}: Bootstraps a Pro install (not needed for CE or helm)')

parser.add_argument('-d', '--dashboard', required=True, dest='dshb', help="URL of the dashboard")
parser.add_argument('-s', '--adminSecret', required=True, dest='adminSecret', help="Dashboard Admin Secret")
parser.add_argument('-e', '--adminEmail', required=True, default=adminEmail, dest='adminEmail', help="Dashboard Admin email address")
parser.add_argument('-p', '--adminPassword', required=True, default=adminPassword, dest='adminPassword', help="Dashboard Admin password")
parser.add_argument('-l', '--licence', required=True, dest='licence', help="Dashboard pro licence")
parser.add_argument('-c', '--portalCNAME', required=False, default=portalCNAME, dest='portalCNAME', help="Portal CNAME")

args = parser.parse_args()
args.dshb = args.dshb.strip('/')

# create a new dashboard object
tykInstance = tyk.dashboard(args.dshb, "", args.adminSecret)

# Bootstrap when the dashboard is up
if tykInstance.waitUp(10):
    resp = tykInstance.bootstrap(args.adminEmail, args.adminPassword, args.licence, args.portalCNAME)
    if resp.status_code != 200:
        print(f'[FATAL]Failed to bootstrap. The dashboard returned {resp.status_code}', file=sys.stderr)
        print(json.dumps(resp.json()), file=sys.stderr)
        sys.exit(1)
else:
    print(f'[FATAL]Failed to bootstrap. Dashboard ({args.dshb}) did not respond', file=sys.stderr)
