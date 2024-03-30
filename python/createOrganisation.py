#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --adminsecret <Dashboard Admin Secret> --name <org name> --slug <slug name> --portalcname <portal CNAME>')
    print("    Will create a new org with the given org name")
    sys.exit(1)

dshb = ""
adminsecret = ""
name = ""
slug = ""
verbose = 0
cname = "portal.cname.com"

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "adminsecret=", "name=", "slug=", "portalcname=", "verbose"])
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
    elif opt == '--name':
        name = arg
    elif opt == '--portalcname':
        cname = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and adminsecret and name):
    print(f'{scriptName}: must specify --dashboard, --adminsecret and --name')
    printhelp()

if not slug:
    slug = name

# create a new dashboard object
tykInstance = tyk.dashboard(dshb, "", adminsecret)

# Create the org data structure
orgDef = { "owner_name": name, "owner_slug": slug, "cname_enabled": True, "cname": cname}

resp = tykInstance.createOrganisation(orgDef)
print(json.dumps(resp.json()))
if resp.status_code != 200:
    sys.exit(1)
