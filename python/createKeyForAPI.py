#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)
defaultRate = 1000
defaultPer = 60

parser = argparse.ArgumentParser(description=f'{scriptName}: Will create a new authentication key for the API_ID given or from the json key file given')

DashboardOrGateway = parser.add_mutually_exclusive_group(required=True)
DashboardOrGateway.add_argument('-d', '--dashboard', dest='dshb', help="URL of the dashboard")
DashboardOrGateway.add_argument('-g', '--gateway', dest='gatw', help="URL of the gateway")

parser.add_argument('-a', '--apiid', dest='apiids', nargs='+', help="List of API IDs which the key can access")
parser.add_argument('-c', '--cred', required=True, dest='auth', help="Dashboard API key or Gateway secret")
parser.add_argument('-C', '--customKeyName', dest='keyName', help="Custom key name")
parser.add_argument('-k', '--keyFile', dest='keyFileName', help="JSON key file")
parser.add_argument('-p', '--per', dest='per', type=int, help="Per period in seconds")
parser.add_argument('-r', '--rate', dest='rate', type=int, help="Rate: the number of requests allowed in the 'per' period")
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

if not (args.keyFileName or args.apiids):
    print('Error: Either --apiid or --keyFile must be given')
if (args.rate or args.per) and not (args.rate and args.per):
    print('Error: Both --rate and --pre must be given if either is')

# create a new dashboard or gateway object
if args.dshb:
    tykInstance = tyk.dashboard(args.dshb, args.auth)
else:
    tykInstance = tyk.gateway(args.gatw, args.auth)

if args.keyFileName:
    key = tyk.authKey(args.keyFileName)
else:
    key = tyk.authKey()

if rate:
    key.setRate(args.rate)
    key.setPer(args.per)
else:
    key.setRate(defaultRate)
    key.setPer(defaultPer)

if apiids:
    for apiid in args.apiids:
        key.addAPI(args.apiid)

if args.verbose:
    print(key)

if args.keyName:
    resp = tykInstance.createCustomKey(key.json(), args.keyName)
else:
    resp = tykInstance.createKey(key.json())

if resp.status_code != 200:
    print(resp)
    sys.exit(1)
else:
    if args.verbose:
        print(json.dumps(resp.json(), indent=2))
    else:
        if "key_id" in resp.json():
            # dashboard
            print(json.dumps(resp.json()["key_id"]))
        else:
            # gateway
            print(json.dumps(resp.json()["key"]))

