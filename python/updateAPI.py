#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.environ.get("HOME")}/code/tyk-scripts/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials> --template <API template file> --apiid <apiid> --verbose')
    print("    Will take the template apply it to the APIid given")
    sys.exit(1)

dshb = ""
auth = ""
templateFile = ""
verbose = 0
apiid = ""

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "template=", "dashboard=", "cred=", "number=", "apiid=", "verbose"])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--template':
        templateFile = arg
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--apiid':
        apiid = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and templateFile and auth and apiid):
    printhelp()

# create a new dashboard object
dashboard = tyk.dashboard(dshb, auth)

# read the API defn
with open(templateFile) as APIFile:
    APIjson=json.load(APIFile)
    APIFile.close()

# set the api_id in the definition
APIjson["api_definition"]["api_id"] = apiid

resp = dashboard.updateAPI(json.dumps(APIjson), apiid)
print(json.dumps(resp.json()))
if resp.status_code != 200:
    sys.exit(1)
