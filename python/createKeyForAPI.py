#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --cred <Dashboard API key or Gateway secret> --apiid <apiid,apiid> --rate <rate> --per <period in seconds> --customKeyName <Custom key name> --keyFile <key json file> --verbose')
    print("    Will create a new authentication key for the API_ID given")
    sys.exit(1)

dshb = ""
gatw = ""
auth = ""
apiids = ""
keyName = ""
keyFileName = ""
verbose = 0
rate = 0
per = 0
defaultRate = 1000
defaultPer = 60


try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "gateway=", "cred=", "apiid=", "per=", "rate=", "customKeyName=", "keyFile=", "verbose"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--gateway':
        gatw = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--apiid':
        apiids = arg
    elif opt == '--rate':
        rate = int(arg)
    elif opt == '--per':
        per = int(arg)
    elif opt == '--customKeyName':
        keyName = arg
    elif opt == '--keyFile':
        keyFileName = arg
    elif opt == '--verbose':
        verbose = 1

if not ((dshb or gatw) and auth):
    print('Error: Either --dashboard or --gateway and --cred must be given')
    printhelp()
if not (keyFileName or apiids):
    print('Error: Either --apiid or --keyFile must be given')
    printhelp()
if (rate and not per) or (per and not rate):
    print('Error: Both --rate and --pre must be given if either is')
    printhelp()

# create a new dashboard or gateway object
if dshb:
    tyk = tyk.dashboard(dshb, auth)
else:
    tyk = tyk.gateway(gatw, auth)

if keyFileName:
    with open(keyFileName) as keyFile:
        KeyJson=json.load(keyFile)
else:
    KeyJson = {}
    KeyJson["access_rights"] = {}

if rate:
    KeyJson["rate"] = rate
    KeyJson["per"] = per
    KeyJson["allowance"] = rate
else:
    KeyJson["rate"] = defaultRate
    KeyJson["per"] = defaultPer
    KeyJson["allowance"] = defaultRate

if apiids:
    for apiid in apiids.split(','):
        KeyJson["access_rights"][apiid] = {
                "api_id": apiid,
                "api_name": "",
                "versions": [ "Default" ],
                "allowed_urls": [],
                "restricted_types": [],
                "limit": None,
                "allowance_scope": ""
            }

if not 'alias' in KeyJson:
    KeyJson["alias"] = "Created by createKeyForAPI.py for " + apiid
if not 'last_check' in KeyJson:
    KeyJson["last_check"] = 1421674410
if not 'expires' in KeyJson:
    KeyJson["expires"] = 0
if not 'quota_max' in KeyJson:
    KeyJson["quota_max"] = -1
if not 'quota_renews' in KeyJson:
    KeyJson["quota_renews"] = 1699629658
if not 'quota_remaining' in KeyJson:
    KeyJson["quota_remaining"] = -1
if not 'quota_renewal_rate' in KeyJson:
    KeyJson["quota_renewal_rate"] = 60

if verbose:
    print(json.dumps(KeyJson, indent=2))

if keyName:
    resp = tyk.createCustomKey(KeyJson, keyName)
else:
    resp = tyk.createKey(KeyJson)

if resp.status_code != 200:
    print(resp)
    sys.exit(1)
else:
    if verbose:
        print(json.dumps(resp.json(), indent=2))
    else:
        if "key_id" in resp.json():
            # dashboard
            print(json.dumps(resp.json()["key_id"]))
        else:
            # gateway
            print(json.dumps(resp.json()["key"]))

