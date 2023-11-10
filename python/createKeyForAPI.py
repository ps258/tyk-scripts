#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API key or Gateway secret> --apiid <apiid> --rate <rate> --per <period in seconds>')
    print("    returns the API JSON for the given APIID")
    sys.exit(1)

dshb = ""
auth = ""
apiid = ""
verbose = 0
rate = 1000
per = 60


try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "cred=", "apiid=", "per=", "rate=", "verbose"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--apiid':
        apiid = arg
    elif opt == '--rate':
        rate = int(arg)
    elif opt == '--per':
        per = int(arg)
    elif opt == '--verbose':
        verbose = 1

if not (dshb and auth and apiid):
    printhelp()

# create a new dashboard or gateway object
if dshb:
    tyk = tyk.dashboard(dshb, auth)
else:
    tyk = tyk.gateway(gatw, auth)

KeyJson = {}
KeyJson["access_rights"] = {}

KeyJson["access_rights"][apiid] = {
        "api_id": apiid,
        "api_name": "",
        "versions": [ "Default" ],
        "allowed_urls": [],
        "restricted_types": [],
        "limit": None,
        "allowance_scope": ""
    }
KeyJson["rate"] = rate
KeyJson["per"] = per
KeyJson["alias"] = "Created by createKeyForAPI.py for " + apiid
KeyJson["last_check"] = 1421674410
KeyJson["expires"] = 0
KeyJson["quota_max"] = -1
KeyJson["quota_renews"] = 1699629658
KeyJson["quota_remaining"] = -1
KeyJson["quota_renewal_rate"] = 60
KeyJson["allowance"] = rate


if verbose:
    print(json.dumps(KeyJson, indent=2))

resp = tyk.createKey(KeyJson)
if resp.status_code != 200:
    print(resp)
    sys.exit(1)
else:
    print(json.dumps(resp.json()["key_id"]))

