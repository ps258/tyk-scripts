#!/usr/bin/python3

import json
import os
import getopt
import sys
import time
import requests
import datetime

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API key or Gateway secret> --start <start epoch second> --end <end epoch second> --apiid <apiid>')
    print("    prints the number of http response codes issued per second")
    sys.exit(1)

dshb = ""
auth = ""
apiid = ""
verbose = 0
start = int(time.time())
end = int(time.time()) - 600 # the last 10 minutes

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "cred=", "apiid=", "start=", "end=", "verbose"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--start':
        start = int(arg)
    elif opt == '--end':
        end = int(arg)
    elif opt == '--apiid':
        apiid = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and auth and start and end and apiid):
    printhelp()

if end <= start:
    print('[FATAL]--end must be after --start')


print(f'Calling {dshb}/api/logs?start={start}&end={end}&p=-1&api={apiid}')
resp = requests.get(f'{dshb}/api/logs?start={start}&end={end}&p=-1&api={apiid}', headers={'Authorization': auth}, verify=False)
if resp.status_code != 200:
    print(resp)
    sys.exit(1)

analytics = resp.json()['data']
results = dict()
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

for epoch_time in sorted(results.keys()):
    first = True
    print(f'{epoch_time}: ',end='')
    for response_code in sorted(results[epoch_time].keys()):
        if first:
            print(f'{response_code}: {results[epoch_time][response_code]}', end='')
            first = False
        else:
            print(f', {response_code}: {results[epoch_time][response_code]} ', end='')
    print()


#print(json.dumps(resp.json(), indent=2))
