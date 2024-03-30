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
    tykInstance = tyk.dashboard(dshb, auth)
else:
    tykInstance = tyk.gateway(gatw, auth)

if keyFileName:
    key = tyk.authKey(keyFileName)
else:
    key = tyk.authKey()

if rate:
    key.setRate(rate)
    key.setPer(per)
else:
    key.setRate(defaultRate)
    key.setPer(defaultPer)

if apiids:
    for apiid in apiids.split(','):
        key.addAPI(apiid)

if verbose:
    print(key)

if keyName:
    resp = tykInstance.createCustomKey(key.json(), keyName)
else:
    resp = tykInstance.createKey(key.json())

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

