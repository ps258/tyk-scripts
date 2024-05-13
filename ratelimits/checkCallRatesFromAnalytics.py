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
parser.add_argument('-r', '--rate', required=True, type=int, help="Number per interval")
parser.add_argument('-p', '--per', required=True, type=int, help="Per interval in seconds")
parser.add_argument('-t', '--tag', required=False, help="Analytics tag to restrict the results by")
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

def intags(tag, tags):
    return tag in tags

# filter the results and store them by 10E-6 seconds
def recordHits(analytics, results):
    for log in analytics:

        # check if we've got a filter and ignore any analytics records with a matching tag
        if args.tag:
            if not intags(args.tag, log["Tags"]):
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
            timestamp = datetime.datetime.strptime(log['TimeStamp'], "%Y-%m-%dT%H:%M:%SZ")
        epoch_time = int(timestamp.timestamp()*1_000_000)
        # non-zero latencies come from upstream so 429s should all have 0 latency
        if log["ResponseCode"] == 429 and log["RequestTime"] > 0:
            print(f'[WARN] at {log["RequestTime"]} a 429 had a latency of {log["RequestTime"]}')
        if not epoch_time in results['timestamps']:
            results['timestamps'][epoch_time] = dict()
        if not log['ResponseCode'] in results['timestamps'][epoch_time]:
            results['timestamps'][epoch_time][log['ResponseCode']] = 0
        results['timestamps'][epoch_time][log['ResponseCode']] += 1

# create a list of the events in the last 'per' seconds
# to make sure we're not missing our rate limit
def updateRate(rate, timestamp, response_code):
    delete = dict()
    for i in rate:
        if i != 'count' and i < (timestamp - args.per*1_000_000):
            # need to save this to another dict because we can't change this one underneath the loop
            delete[i] = 1
    # remove the entries in the rate dict that are older than the 'per' ago
    for i in delete:
        for response_code in rate[i]:
            # keep a running tally of the number of responses in the per span
            rate['count'] -= rate[i][response_code]
        del rate[i]
    if not timestamp in rate:
        rate[timestamp] = dict()
    if not response_code in rate[timestamp]:
        rate[timestamp][response_code] = 0
    rate[timestamp][response_code] += 1
    # keep a running tally of the number of responses in the per span
    rate['count'] += 1


# some globals to keep track of things
results = dict()
results['timestamps'] = dict()
results['policies'] = dict()
results['keys'] = dict()
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

# once the data is loaded analyse the results
# we could do this while loading the data if we were sure it always came in time order.
# but it won't when we check against multiple APIs
if True:
    rate = dict()
    rate['count'] = 0
    for epoch_time in sorted(results['timestamps'].keys()):
        first = True
        for response_code in sorted(results['timestamps'][epoch_time].keys()):
            updateRate(rate,epoch_time,response_code)
            #if response_code == 429:
            if first:
                print(f'{epoch_time/1_000_000}: ',end='')
                print(f'{response_code}: {results["timestamps"][epoch_time][response_code]}', end='')
                first = False
            else:
                print(f', {response_code}: {results["timestamps"][epoch_time][response_code]} ', end='')
            print(f' rate: {rate["count"]}')

for policy in sorted(results['policies'].keys()):
    print(f'Policy {policy} -> {results["policies"][policy]}')
for key in sorted(results['keys'].keys()):
    print(f'Key {key} -> {results["keys"][key]}')

