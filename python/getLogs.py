#!/usr/bin/python3

import json
import os
import getopt
import sys
import time
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API key or Gateway secret> --start <start epoch second> --end <end epoch second> --apiid <apiid>')
    print("    returns the logs for the API")
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

if not (dshb and auth):
    printhelp()

# create a new dashboard or gateway object
if dshb:
    tykInstance = tyk.dashboard(dshb, auth)

resp = tykInstance.getLogs(start = start, end = end, apiid = apiid)
print(json.dumps(resp.json(), indent=2))
if resp.status_code != 200:
    sys.exit(1)
