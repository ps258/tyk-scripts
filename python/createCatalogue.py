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
parser.add_argument('--policyId', '-p', required=True, dest='policyId', help="Policy ID to publish")
parser.add_argument('--noShow', '-n', action='store_true', dest='noShow', help="Set show to false")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

show = not args.noShow
# create the dashboard connection
tykInstance = tyk.dashboard(args.dshb, args.auth)

catalogue = tykInstance.getCatalogue().json()
# create a dictionary of all entry names
allnames = dict()
for policy in catalogue['apis']:
    name = policy["name"]
    allnames[name] = 1

EntryName='api'
short_description = 'Short description for '
long_description = 'Long description for '
# find the first available name
i = 1
while EntryName+str(i) in allnames:
    i += 1
catalogue["apis"].append({"name": EntryName+str(i),\
        "short_description": short_description+str(i),\
        "long_description": long_description+str(i),\
        "show": show,\
        "policy_id": args.policyId,\
        "version": "v2"})

if args.verbose:
    print('[INFO]JSON being sent')
    print(json.dumps(catalogue, indent=2))


print(f'Adding catalogue entry {EntryName+str(i)}')
resp = tykInstance.updateCatalogue(json.dumps(catalogue))
print(resp)
