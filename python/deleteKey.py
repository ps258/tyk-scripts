#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials> --keyid <keyid>')
    print("    Will delete the key with keyid from the dashboard")
    sys.exit(1)

dshb = ""
auth = ""
keyid = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "cred=", "keyid=", "verbose"])
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
    elif opt == '--keyid':
        keyid = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and auth and keyid):
    printhelp()

tykInstance = tyk.dashboard(dshb, auth)

resp = tykInstance.deleteKey(keyid)
print(json.dumps(resp.json()))
if resp.status_code != 200:
    sys.exit(1)
