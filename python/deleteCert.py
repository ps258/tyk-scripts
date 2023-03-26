#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials> --certid <certid>')
    print("    Deletes the certificate from the certificate store")
    sys.exit(1)

dshb = ""
auth = ""
certid = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "cred=", "certid=", "verbose"])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--certid':
        certid = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and auth and certid):
    printhelp()

dashboard = tyk.dashboard(dshb, auth)

resp = dashboard.deleteCert(certid)
print(json.dumps(resp.json(), indent=2))
if resp.status_code != 200:
    sys.exit(1)
