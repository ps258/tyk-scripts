#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --cred <Dashboard API key or Gateway secret> --certificate <PEM format file> --verbose')
    print("    Will add the certificate to the certificate store")
    sys.exit(1)

dshb = ""
gatw = ""
auth = ""
certFile = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "certificate=", "dashboard=", "gateway=", "cred=", "verbose"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--certificate':
        certFile = arg
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--gateway':
        gatw = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--verbose':
        verbose = 1

if not ((dshb or gatw) and certFile and auth):
    printhelp()

# create a new dashboard or gateway object
if dshb:
    tykInstance = tyk.dashboard(dshb, auth)
else:
    tykInstance = tyk.gateway(gatw, auth)


resp = tykInstance.createCert(certFile)
print(json.dumps(resp.json()))
if resp.status_code != 200:
    print(f'[FATAL]Tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)
