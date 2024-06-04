#!/usr/bin/python3

import json
import os
import sys
import time
import requests
import datetime
import argparse

scriptName = os.path.basename(__file__)

dshb = ""
auth = ""
apiids = ""
verbose = False
start = int(time.time())
end = int(time.time()) - 600 # the last 10 minutes
timeoffset = round((datetime.datetime.now()-datetime.datetime.utcnow()).total_seconds())

parser = argparse.ArgumentParser(description=f'{scriptName}: prints the number of http response codes issued per second')

parser.add_argument('-d', '--dashboard', required=True, help="URL of the dashboard")
parser.add_argument('-c', '--credential', required=True, help="Admin access key")
parser.add_argument('-a', '--apiids', help="API or list of APIs to retrieve analytics of")
parser.add_argument('-s', '--start', required=True, type=int, help="Start epoch second")
parser.add_argument('-e', '--end', required=True, type=int, help="End epoch second")
parser.add_argument('-t', '--tag', required=False, help="Analytics tag to restrict the results by")
parser.add_argument('-m', '--multiplier', type=int, default=1, help="The timestamp multiplier. Defaults to 1, but can be up to 1000000")
parser.add_argument('-o', '--GMToffset', type=int, default=timeoffset, help="The number of seconds from GMT that is localtime")
parser.add_argument('-v', '--verbose', action='store_true', help="Verbose output")

args = parser.parse_args()
args.dashboard = args.dashboard.strip('/')

start = args.start
end = args.end
dshb = args.dashboard
auth = args.credential
apiids = args.apiids
GMToffset = args.GMToffset
multiplier = args.multiplier

if end <= start:
    print('[FATAL]--end must be after --start')

# filter the results and store them by 10E-6 seconds
def recordHits(analytics, results):
    for log in analytics:

        # check if we've got a filter and ignore any analytics records with a matching tag
        if args.tag:
            if not args.tag in log["Tags"]:
                continue

        # keep track of the keys and policies mentioned in the analytics records
        # so we can give a summary at the end
        for tag in log["Tags"]:
            if tag.startswith('pol-'):
                if not tag in results["policies"]:
                    results["policies"][tag] = 0
                results["policies"][tag] += 1
            if tag.startswith('key-'):
                if not tag in results["keys"]:
                    results["keys"][tag] = 0
                results["keys"][tag] += 1

        # read the analytics record and save its timestamp with the number of each ResponseCode
        # given that we're dealing with 10E-6 second accuracy there will probably only be one in a timestamp
        #  but don't assume that
        try:
            timestamp = datetime.datetime.strptime(log['TimeStamp'], "%Y-%m-%dT%H:%M:%S.%fZ")
        except:
            try:
                timestamp = datetime.datetime.strptime(log['TimeStamp'], "%Y-%m-%dT%H:%M:%SZ")
            except:
                print(f"[FATAL]Still couldn't pars {log['TimeStamp']=}")
                sys.exit(1)
        epoch_time = int(timestamp.timestamp()*multiplier)
        # non-zero latencies come from upstream so 429s should all have 0 latency
        if log["ResponseCode"] == 429 and log["RequestTime"] > 0:
            print(f'[WARN] at {log["RequestTime"]} a 429 had a latency of {log["RequestTime"]}')
        if not epoch_time in results['timestamps']:
            results['timestamps'][epoch_time] = dict()
        if not log['ResponseCode'] in results['timestamps'][epoch_time]:
            results['timestamps'][epoch_time][log['ResponseCode']] = 0
        results['timestamps'][epoch_time][log['ResponseCode']] += 1

# some globals to keep track of things
results = dict()
results['timestamps'] = dict()
results['policies'] = dict()
results['keys'] = dict()
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

for epoch_time in sorted(results['timestamps'].keys()):
    first = True
    for response_code in sorted(results['timestamps'][epoch_time].keys()):
        if first:
            print(f'{(epoch_time/multiplier)+GMToffset}: ',end='')
            print(f'{response_code}: {results["timestamps"][epoch_time][response_code]}', end='')
            first = False
        else:
            print(f', {response_code}: {results["timestamps"][epoch_time][response_code]} ', end='')
    print()


