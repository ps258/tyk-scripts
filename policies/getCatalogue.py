#!/usr/bin/python3

import json
import requests
import os
import getopt
import sys

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials>')
    print("    Will retrieve the catalogue from the portal")
    sys.exit(2)

dshb = ""
auth = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "cred=", "verbose"])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and auth):
    printhelp()

# read the policy defn
headers = {'Authorization' : auth}
# get the existing catalogue entries
resp = requests.get(f'{dshb}/api/portal/catalogue', headers=headers)
if resp.status_code != 200:
    print(resp.text)
    sys.exit(1)
catalogue = json.loads(resp.text)
print(json.dumps(catalogue, indent=2))
