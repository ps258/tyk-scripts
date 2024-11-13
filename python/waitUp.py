#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

max_wait_time = 10

description = f"Will wait until the dashboard or gateway is up. Waiting at most --time seconds (Defaults to {max_wait_time}s)"
parser = argparse.ArgumentParser(description=f'{scriptName}: {description}')

DashboardOrGateway = parser.add_mutually_exclusive_group(required=True)
DashboardOrGateway.add_argument('--dashboard', '-d', dest='dshb', help="URL of the dashboard")
DashboardOrGateway.add_argument('--gateway', '-g', dest='gatw', help="URL of the gateway")

parser.add_argument('--time', '-t', default=max_wait_time, dest='max_wait_time', type=int, help="Max wait time")

args = parser.parse_args()

# create a dashboard or gateway object
if args.dshb:
    tykInstance = tyk.dashboard(args.dshb)
else:
    tykInstance = tyk.gateway(args.gatw)

if not tykInstance.waitUp(args.max_wait_time):
    print(f'[FATAL]Tyk is not up after waiting {max_wait_time}s', file=sys.stderr)
    sys.exit(1)
