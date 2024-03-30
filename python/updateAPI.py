#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --cred <Dashboard API key or Gateway secret> --template <API template file> --apiid <apiid> --verbose')
    print("    Will take the template and apply it to the APIid given")
    sys.exit(1)

dshb = ""
gatw = ""
auth = ""
templateFile = ""
verbose = 0
apiid = ""

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "template=", "dashboard=", "gateway=", "cred=", "apiid=", "verbose"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--template':
        templateFile = arg
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--gateway':
        gatw = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--apiid':
        apiid = arg
    elif opt == '--verbose':
        verbose = 1

if not ((dshb or gatw) and templateFile and auth and apiid):
    printhelp()

# create a new dashboard or gateway object
if dshb:
    tykInstance = tyk.dashboard(dshb, auth)
else:
    tykInstance = tyk.gateway(gatw, auth)

# read the API defn
with open(templateFile) as APIFile:
    APIjson=json.load(APIFile)
    APIFile.close()

# set the api_id in the definition
if "api_definition" in APIjson:
    APIjson["api_definition"]["api_id"] = apiid
elif "api_id" in APIjson:
    APIjson["api_id"] = apiid
else:
    print('[FATAL]Unable to find "api_id" to update')

resp = tykInstance.updateAPI(json.dumps(APIjson), apiid)
print(json.dumps(resp.json()))
if resp.status_code != 200:
    print(f'[FATAL]Tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)
