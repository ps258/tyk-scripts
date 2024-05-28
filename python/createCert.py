#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

parser = argparse.ArgumentParser(description=f'{scriptName}: Will add the certificate to the certificate store')

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-d', '--dashboard', dest='dshb', help="URL of the dashboard")
group.add_argument('-g', '--gateway', dest='gatw', help="URL of the gateway")

parser.add_argument('-c', '--cred', required=True, dest='auth', help="Dashboard API key or Gateway secret")
parser.add_argument('-C', '--certificate', required=True, dest='certFile', help="PEM format file")
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

# create a new dashboard or gateway object
if args.dshb:
    args.dshb = args.dshb.strip('/')
    tykInstance = tyk.dashboard(args.dshb, args.auth)
else:
    args.gatw = args.gatw.strip('/')
    tykInstance = tyk.gateway(args.gatw, args.auth)


resp = tykInstance.createCert(args.certFile)
print(json.dumps(resp.json()))
if resp.status_code != 200:
    print(f'[FATAL]Tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)
