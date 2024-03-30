#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

dshb = ""
adminsecret = ""
adminEmail = "admin@tyk.io"
adminPassword = "ABC-123"
licence = ""
verbose = 0
portalCNAME = "portal.cname.com"

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --adminsecret <Dashboard Admin Secret> --adminEmail <admin email address> --adminPassword <admin password in plain text> --licence <dashboard licence> --portalcname <portal CNAME>')
    print('    Will create a new org with the given org name')
    print(f'    Default admin user email: {adminEmail}')
    print(f'    Default admin user password: {adminPassword}')
    sys.exit(1)

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "adminsecret=", "adminEmail=", "adminPassword=", "licence=", "portalcname=", "verbose"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--adminsecret':
        adminsecret = arg
    elif opt == '--adminEmail':
        adminEmail = arg
    elif opt == '--adminPassword':
        adminPassword = arg
    elif opt == '--licence':
        licence = arg
    elif opt == '--portalcname':
        portalCNAME = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and adminsecret and licence):
    print(f'{scriptName}: must specify --dashboard, --adminsecret and --licence')
    printhelp()

# create a new dashboard object
tykInstance = tyk.dashboard(dshb, "", adminsecret)

# Bootstrap when the dashboard is up
if tykInstance.waitUp(10):
    resp = tykInstance.bootstrap(adminEmail, adminPassword, licence, portalCNAME)
    if resp.status_code != 200:
        print(f'[FATAL]Failed to bootstrap. The dashboard returned {resp.status_code}', file=sys.stderr)
        print(json.dumps(resp.json()), file=sys.stderr)
        sys.exit(1)
else:
    print(f'[FATAL]Failed to bootstrap. Dashboard did not respond', file=sys.stderr)
