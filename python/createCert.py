#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.environ.get("HOME")}/code/tyk-scripts/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials> --certificate <PEM format file> --verbose')
    print("    Will add the certificate to the Dashboard certificate store")
    sys.exit(1)

dshb = ""
auth = ""
certFile = ""
name = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "certificate=", "dashboard=", "cred=", "number=", "name=", "verbose"])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--certificate':
        certFile = arg
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--name':
        name = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and certFile and auth):
    printhelp()

# create a new dashboard object
dashboard = tyk.dashboard(dshb, auth)

resp = dashboard.createCert(certFile)
print(json.dumps(resp.json()))
if resp.status_code != 200:
    sys.exit(1)
