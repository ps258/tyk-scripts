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
adminEmail = "tyk@admin.com"
adminPassword = "ABC-123"
licence = ""
verbose = 0
cname = "portal.cname.com"

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --adminsecret <Dashboard Admin Secret> --adminEmail <admin email address> --adminPassword <admin password in plain text> --licence <dashboard licence> --portalcname <portal CNAME>')
    print(f'    Default admin user email: {adminEmail}')
    print(f'    Default admin user password: {adminPassword}')
    print("     Will create a new org with the given org name")
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
        cname = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and adminsecret and licence):
    print(f'{scriptName}: must specify --dashboard, --adminsecret and --licence')
    printhelp()

# create a new dashboard object
dashboard = tyk.dashboard(dshb, "", adminsecret)

# Create the org data structure

resp = dashboard.bootstrap(adminEmail, adminPassword, licence, cname)
if resp.status_code != 200:
    print("[FATAL]Failed to bootstrap")
    print(json.dumps(resp.json()))
    sys.exit(1)
