#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --cred <Dashboard API key or Gateway secret> --number <number of APIs to add generate> --template <API template file> --name <base name of API> --verbose')
    print("    Will take the template and increment its name and listen path so that they do not clash, then add it as an API to the dashboard or gateway")
    sys.exit(1)

dshb = ""
gatw = ""
auth = ""
templateFile = ""
name = ""
verbose = 0
toAdd = 1

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "gateway=", "cred=", "template=", "number=", "name=", "verbose"])
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
    elif opt == '--number':
        toAdd = int(arg)
    elif opt == '--verbose':
        verbose = 1

if not ((dshb or gatw) and templateFile and auth and toAdd):
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
        # if we've been given a name then apply that
        if 'api_definition' in APIjson:
            APIjson["api_definition"]["name"] = name
        else:
            APIjson["name"] = name

numberCreated = tykInstance.createAPIs(APIjson, toAdd)

if verbose:
    if numberCreated == toAdd:
        print(f'Success: {numberCreated} APIs created')
    else:
        print(f'Failure: Only {numberCreated} of {toAdd} APIs created')
        sys.exit(1)
else:
    print(numberCreated)
