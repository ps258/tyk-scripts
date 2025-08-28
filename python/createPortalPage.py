#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

parser = argparse.ArgumentParser(description=f'{scriptName}: Will create a old portal catalogue entry for the policy given')
parser.add_argument('--dashboard', '-d', required=True, dest='dshb', help="URL of the dashboard")
parser.add_argument('--cred', '-c', required=True, dest='auth', help="Dashboard API key")
parser.add_argument('--page', '-m', required=True, dest='pageFile', help="JSON for the page to create")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

# create the dashboard connection
tykInstance = tyk.dashboard(args.dshb, args.auth)

# read the page file JSON
with open(args.pageFile) as PAGEFILE:
    portalPage=json.load(PAGEFILE)
    PAGEFILE.close()

resp = tykInstance.createPortalPage(json.dumps(portalPage))
print(json.dumps(resp.json(), indent=2))
