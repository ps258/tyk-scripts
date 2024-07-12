#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

adminEmail = "admin@tyk.io"
adminPassword = "ABC-123"
portalCNAME = "portal.cname.com"
waitUp = 10

parser = argparse.ArgumentParser(description=f'{scriptName}: Bootstraps a Pro install (not needed for CE or helm)')

parser.add_argument('--dashboard', '-d', required=True, dest='dshb', help="URL of the dashboard")
parser.add_argument('--adminSecret', '-s', required=True, dest='adminSecret', help="Dashboard Admin Secret")
parser.add_argument('--adminEmail', '-e', required=True, default=adminEmail, dest='adminEmail', help="Dashboard Admin email address")
parser.add_argument('--adminPassword', '-p', required=True, default=adminPassword, dest='adminPassword', help="Dashboard Admin password")
parser.add_argument('--licence', '-l', required=True, dest='licence', help="Dashboard pro licence")
parser.add_argument('--portalCNAME', '-c', required=False, default=portalCNAME, dest='portalCNAME', help="Portal CNAME")

args = parser.parse_args()

# create a new dashboard object
tykInstance = tyk.dashboard(args.dshb, "", args.adminSecret)

# Bootstrap when the dashboard is up
if tykInstance.waitUp(waitUp):
    resp = tykInstance.bootstrap(args.adminEmail, args.adminPassword, args.licence, args.portalCNAME)
    if resp.status_code != 200:
        print(f'[FATAL]Failed to bootstrap. The dashboard returned {resp.status_code}', file=sys.stderr)
        print(json.dumps(resp.json()), file=sys.stderr)
        sys.exit(1)
else:
    print(f'[FATAL]Failed to bootstrap. Dashboard ({args.dshb}) was not up after {waitUp}s', file=sys.stderr)
