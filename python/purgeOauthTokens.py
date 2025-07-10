#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

parser = argparse.ArgumentParser(description=f'{scriptName}: Trims the expired OAuth tokens the zset that tracks them')

parser.add_argument('--gateway', '-g', required=True, dest='gatw', help="URL of the gateway")
parser.add_argument('--cred', '-c', required=True, dest='auth', help="Gateway secret")
parser.add_argument('--verbose', '-v', required=False, action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

# create a new dashboard or gateway object
tyk = tyk.gateway(args.gatw, args.auth)

resp = tyk.purgeOauthTokens()
if resp.status_code != 200:
    print(f'[FATAL]{scriptName}: Tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)

print(json.dumps(resp.json(), indent=2))
