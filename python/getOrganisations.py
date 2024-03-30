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
    print(f'{scriptName} --dashboard <dashboard URL> --adminsecret <Dashboard Admin Secret>')
    print("    List all the organisations")
    sys.exit(1)

dshb = ""
verbose = 0
adminsecret = ""

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "adminsecret=", "verbose"])
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
    elif opt == '--verbose':
        verbose = 1

if not (dshb and adminsecret):
    printhelp()

tykInstance = tyk.dashboard(dshb, "", adminsecret)

organisations = tykInstance.getOrganisations().json()
for org in organisations["organisations"]:
    if verbose:
        print(json.dumps(org, indent=2))
    else:
        print(f'{org["id"]}, {org["owner_name"]}, {org["owner_slug"]}, {org["cname_enabled"]}, {org["cname"]}')
