#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.environ.get("HOME")}/code/tyk-scripts/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials> --number <number of APIs to add generate> --template <API template file> --name <base name of API> --verbose')
    print("    Will take the template and increment its name and listen path so that they do not clash, then add it as an API to the dashboard")
    sys.exit(1)

dshb = ""
auth = ""
templateFile = ""
toAdd = 0
verbose = 0
name = ""

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "template=", "dashboard=", "cred=", "number=", "name=", "verbose"])
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
    elif opt == '--name':
        name = arg
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
    if name:
        APIjson["api_definition"]["name"] = name

numberCreated = dashboard.createAPIs(APIjson, toAdd)

if numberCreated == toAdd:
    print("Success")
else:
    print(f'Failure only created {numberCreated}')
    sys.exit(1)
