#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API key>')
    print("    Will list the users that are visible with the credentials")
    sys.exit(1)

dshb = ""
auth = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "cred=", "verbose"])
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
    elif opt == '--verbose':
        verbose = 1

if not (dshb and auth):
    printhelp()

# create a new dashboard
tykInstance = tyk.dashboard(dshb, auth)

resp = tykInstance.getUsers()
if resp.status_code != 200:
    print(f'[FATAL]Tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)
if resp.json()['users'] is not None:
    if verbose:
        print(json.dumps(resp.json(), indent=2))
    else:
        tykInstance.printUserSummaryHeader()
        for user in resp.json()['users']:
            tykInstance.printUserSummary(user)
