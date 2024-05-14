#!/usr/bin/python3

import json
import os
import getopt
import sys
import time
import requests
import datetime
import argparse

scriptName = os.path.basename(__file__)


dshb = ""
auth = ""
apiids = ""
verbose = 0
start = int(time.time())
end = int(time.time()) - 600 # the last 10 minutes

parser = argparse.ArgumentParser(description=f'{scriptName}: Retrieves all of the tags out of the analytics and summarises them with the respose code counts')

parser.add_argument('-d', '--dashboard', required=True, help="URL of the dashboard")
parser.add_argument('-c', '--credential', required=True, help="Admin access key")
parser.add_argument('-a', '--apiids', help="API or list of APIs to retrieve analytics of")
parser.add_argument('-s', '--start', required=True, type=int, help="Start epoch second")
parser.add_argument('-e', '--end', required=True, type=int, help="End epoch second")
parser.add_argument('-v', '--verbose', action='store_true', help="Verbose output")

args = parser.parse_args()
args.dashboard = args.dashboard.strip('/')

start = args.start
end = args.end
dshb = args.dashboard
auth = args.credential
apiids = args.apiids

if end <= start:
    print('[FATAL]--end must be after --start')

# filter the results and store them by 10E-6 seconds
def recordHits(analytics, results):
    for log in analytics:

        # keep track of the keys and policies mentioned in the analytics records
        responseCode = log['ResponseCode']
        for tag in log["Tags"]:
            # ignore x-request-id etc because they're unique
            if tag.startswith('x-request-id'):
                continue
            if not tag in results["tags"]:
                results["tags"][tag] = dict()
            if not responseCode in results['tags'][tag]:
                results['tags'][tag][responseCode] = 0
            results['tags'][tag][responseCode] += 1


# some globals to keep track of things
results = dict()
results['tags'] = dict()
if apiids:
    # restrict search to the given API IDs
    for apiid in apiids.split(','):
        if args.verbose:
            print(f'Calling {dshb}/api/logs?start={start}&end={end}&p=-1&api={apiid}')
        resp = requests.get(f'{dshb}/api/logs?start={start}&end={end}&p=-1&api={apiid}', headers={'Authorization': auth}, verify=False)
        if resp.status_code != 200:
            print(resp)
            sys.exit(1)
        recordHits(resp.json()['data'], results)
else:
    # No API IDs given, get all
    if args.verbose:
        print(f'Calling {dshb}/api/logs?start={start}&end={end}&p=-1')
    resp = requests.get(f'{dshb}/api/logs?start={start}&end={end}&p=-1', headers={'Authorization': auth}, verify=False)
    if resp.status_code != 200:
        print(resp)
        sys.exit(1)
    recordHits(resp.json()['data'], results)

# once the data is loaded analyse the results

for tag in sorted(results['tags'].keys()):
    first = True
    for response_code in sorted(results['tags'][tag].keys()):
        if first:
            print(f'{tag}: ',end='')
            print(f'{response_code}: {results["tags"][tag][response_code]}', end='')
            first = False
        else:
            print(f', {response_code}: {results["tags"][tag][response_code]}', end='')
    print()
