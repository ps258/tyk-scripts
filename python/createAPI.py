#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --cred <Dashboard API key or Gateway secret> --template <API template file> --name <base name of API> --verbose')
    print("    Will take the template apply the name (if given) then add it as an API to the dashboard or gateway")
    sys.exit(1)

dshb = ""
gatw = ""
auth = ""
templateFile = ""
name = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "template=", "dashboard=", "gateway=", "cred=", "name=", "verbose"])
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
    elif opt == '--name':
        name = arg
    elif opt == '--verbose':
        verbose = 1

if not ((dshb or gatw) and templateFile and auth):
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
    if name:
        if 'api_definition' in APIjson:
            APIjson["api_definition"]["name"] = name
            APIjson["api_definition"]["slug"] = name
            APIjson["api_definition"]["proxy"]["listen_path"] = '/'+name+'/'
            if verbose:
                print(f'[INFO]Creating API with name: {APIjson["api_definition"]["name"]}, slug:{APIjson["api_definition"]["slug"]}, listen_path {APIjson["api_definition"]["proxy"]["listen_path"]}')
        else:
            APIjson["name"] = name
            APIjson["slug"] = name
            APIjson["proxy"]["listen_path"] = '/'+name+'/'
            if verbose:
                print(f'[INFO]Creating API with name: {APIjson["name"]}, slug:{APIjson["slug"]}, listen_path {APIjson["proxy"]["listen_path"]}')

resp = tykInstance.createAPI(APIjson)
print(json.dumps(resp.json(), indent=2))
if resp.status_code != 200:
    print(f'[FATAL]Tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)
