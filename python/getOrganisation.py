#!/usr/bin/python3

###############################################################
# Reference for calling the dashboard.getOrganisation
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
    print(f'{scriptName} --dashboard <dashboard URL> --adminsecret <Dashboard Admin Secret> --orgid <organisation id>')
    print("    Get the named org")
    sys.exit(1)

dshb = ""
verbose = 0
adminsecret = ""
orgid = ""

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "adminsecret=", "verbose", "orgid="])
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
    elif opt == '--orgid':
        orgid = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and adminsecret and orgid):
    print(f'dshb = {dshb}, adminsecret = {adminsecret}, orgid = {orgid}')
    printhelp()

tykInstance = tyk.dashboard(dshb, "", adminsecret)

resp = tykInstance.getOrganisation(orgid)
organisation = resp.json()
print(json.dumps(organisation, indent=2))
if resp.status_code != 200:
    sys.exit(1)
