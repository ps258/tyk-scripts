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

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API key or Gateway secret> --start <start epoch second> --end <end epoch second> --apiid <apiid,apiid,apiid...>')
    print("    prints the number of http response codes issued per second")
    sys.exit(1)

dshb = ""
auth = ""
apiids = ""
verbose = 0
start = int(time.time())
end = int(time.time()) - 600 # the last 10 minutes

parser = argparse.ArgumentParser(description=f'{scriptName}: Verifies that the given rate limit has been applied correctly by using analytics records')

parser.add_argument('-d', '--dashboard', required=True, help="URL of the dashboard")
parser.add_argument('-c', '--credential', required=True, help="Admin access key")
parser.add_argument('-a', '--apiids', required=True, help="API or list of APIs to retrieve analytics of")
parser.add_argument('-s', '--start', required=True, type=int, help="Start epoch second")
parser.add_argument('-e', '--end', required=True, type=int, help="End epoch second")
parser.add_argument('-v', '--verbose', help="Verbose output")

args = parser.parse_args()
args.dashboard = args.dashboard.strip('/')

start = args.start
end = args.end
dshb = args.dashboard
auth = args.credential
apiids = args.apiids

if end <= start:
    print('[FATAL]--end must be after --start')

def recordHits(analytics, results):
    for log in analytics:
        try:
            timestamp = datetime.datetime.strptime(log['TimeStamp'], "%Y-%m-%dT%H:%M:%S.%fZ")
        except:
            timestamp = datetime.datetime.strptime(log['TimeStamp'], "%Y-%m-%dT%H:%M:%SZ")
        epoch_time = int(timestamp.timestamp())
        # it might be an idea to make sure that there upstream latency is 0 here.
        # non-zero latencies come from upstream so 429s should all have 0 latency
        if not epoch_time in results:
            results[epoch_time] = dict()
        if not log['ResponseCode'] in results[epoch_time]:
            results[epoch_time][log['ResponseCode']] = 0
        results[epoch_time][log['ResponseCode']] += 1

results = dict()
if apiids:
    # restrict search to the given API IDs
    for apiid in apiids.split(','):
        print(f'Calling {dshb}/api/logs?start={start}&end={end}&p=-1&api={apiid}')
        resp = requests.get(f'{dshb}/api/logs?start={start}&end={end}&p=-1&api={apiid}', headers={'Authorization': auth}, verify=False)
        if resp.status_code != 200:
            print(resp)
            sys.exit(1)
        recordHits(resp.json()['data'], results)
else:
    # No API IDs given, get all
    print(f'Calling {dshb}/api/logs?start={start}&end={end}&p=-1')
    resp = requests.get(f'{dshb}/api/logs?start={start}&end={end}&p=-1', headers={'Authorization': auth}, verify=False)
    if resp.status_code != 200:
        print(resp)
        sys.exit(1)
    recordHits(resp.json()['data'], results)

#for epoch_time in range(start, end+1):
for epoch_time in sorted(results.keys()):
    first = True
    print(f'{epoch_time}: ',end='')
    if epoch_time in results:
        for response_code in sorted(results[epoch_time].keys()):
            if first:
                print(f'{response_code}: {results[epoch_time][response_code]}', end='')
                first = False
            else:
                print(f', {response_code}: {results[epoch_time][response_code]} ', end='')
    print()


