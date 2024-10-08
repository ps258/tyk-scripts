#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

parser = argparse.ArgumentParser(description=f'{scriptName}: Will create enable hybrid mode on the given orgid. Note that a dashboard restart is needed to activate the change')

parser.add_argument('--dashboard', '-d', required=True, dest='dshb', help="URL of the dashboard")
parser.add_argument('--adminSecret', '-a', required=True, dest='adminSecret', help="Dashboard admin secret")
parser.add_argument('--org', '-o', required=True, dest='orgID', help="Orgainisation ID")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

# create a new dashboard object
tykInstance = tyk.dashboard(args.dshb, "", args.adminSecret)

# Enable hybrid for the org
resp = tykInstance.enableHybrid(args.orgID)
if resp.status_code != 200:
    print(resp.status_code)
    sys.exit(1)
print(json.dumps(resp.json()))
