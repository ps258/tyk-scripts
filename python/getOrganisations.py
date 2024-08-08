#!/usr/bin/python3

###############################################################
# Reference for calling the dashboard.getOrganisations
# arguments are dashboard and dashboard admin secret
###############################################################

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --adminSecret <Dashboard Admin Secret>')
    print("    List all the organisations")
    sys.exit(1)

dshb = ""
verbose = 0
adminSecret = ""

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "adminSecret=", "verbose"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg
    elif opt == '--adminSecret':
        adminSecret = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and adminSecret):
    printhelp()

tykInstance = tyk.dashboard(dshb, "", adminSecret)

resp = tykInstance.getOrganisations()
if resp.status_code != 200:
    print(f'[FATAL]Tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)
organisations = resp.json()
for org in organisations["organisations"]:
    if verbose:
        print(json.dumps(org, indent=2))
    else:
        print(f'{org["id"]}, {org["owner_name"]}, {org["owner_slug"]}, {org["cname_enabled"]}, {org["cname"]}')
