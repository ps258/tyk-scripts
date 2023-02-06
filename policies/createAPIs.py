#!/usr/bin/python3

import json
import os
import getopt
import sys
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials> --number <number of APIs to add generate> --template <API template file> --verbose')
    print("    Will take the template and increment its name and listen path so that they do not clash, then add it as an API to the dashboard")
    sys.exit(2)

dshb = ""
auth = ""
templateFile = ""
toAdd = 0
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "template=", "dashboard=", "cred=", "number=", "verbose"])
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
    elif opt == '--number':
        toAdd = int(arg)
    elif opt == '--verbose':
        verbose = 1

if not (dshb and templateFile and auth and toAdd):
    printhelp()

# create a new dashboard object
dashboard = tyk.dashboard(dshb, auth)

# read the API defn
with open(templateFile) as APIFile:
    APIjson=json.load(APIFile)
    APIFile.close()
APIName = APIjson["api_definition"]["name"]

# get the existing APIs
apis = dashboard.getAPIs()

# create a dictionary of all API names
allnames = dict()
for api in apis['apis']:
    name = api["api_definition"]["name"]
    allnames[name] = 1

# find the first available name
i = 1
for apiIndex in range(1, toAdd+1):
    while APIName+str(i) in allnames:
        i += 1
    # create the API with the first available index
    newname=APIName+str(i)
    allnames[newname] = 1
    APIjson["api_definition"]["name"] = newname
    APIjson["api_definition"]["proxy"]["listen_path"] = '/'+newname+'/'
    print(f'Adding API {APIjson["api_definition"]["name"]}, {APIjson["api_definition"]["proxy"]["listen_path"]}')
    resp = dashboard.createAPI(json.dumps(APIjson))
    print(json.dumps(resp))
