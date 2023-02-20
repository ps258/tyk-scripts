#!/usr/bin/python3

###############################################################
# create 200 Organisations and create the same user in each
###############################################################

import json
import requests
import os
import getopt
import sys
import time
sys.path.append(f'{os.environ.get("HOME")}/code/tyk-scripts/module')
import tyk

# Suppress the warnings from urllib3 when using a self signed certs
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> URL> --cred <dashboard credentials> --adminsecret <admin secret> --useremail <user email> --userpass <user password> --number <number of orgs to create>')
    print("    create <count> Organisations and create the same user in each")
    sys.exit(1)

dshb = ""
auth = ""
useremail = ""
userpass = ""
verbose = 0
adminsecret = ""
toAdd = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "adminsecret=", "cred=", "useremail=", "userpass=", "number=", "verbose"])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--adminsecret':
        adminsecret = arg
    elif opt == '--cred':
        auth = arg
    elif opt == '--useremail':
        useremail = arg
    elif opt == '--userpass':
        userpass = arg
    elif opt == '--number':
        toAdd = int(arg)
    elif opt == '--verbose':
        verbose = 1

if not (dshb or useremail or userpass or adminsecret):
    printhelp()

dashboard = tyk.dashboard(dshb, auth, adminsecret)

#print(json.dumps(dashboard.getOrganisations(), indent=2))

orgJson = {"owner_name": "Default Org.","owner_slug": "default", "cname_enabled": True, "cname": ""}

dashboard.createOrganisations(orgJson, toAdd)
organisations = dashboard.getOrganisations().json()
for org in organisations["organisations"]:
    resp = dashboard.createAdminUser(useremail, userpass, org["id"])
    print(resp.json())
