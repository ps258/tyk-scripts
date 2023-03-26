#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials> --template <Policy template file> --apiid <apiid> --verbose --number <number to receate>')
    print("    Will create a new policies for the API_ID given")
    sys.exit(1)

dshb = ""
auth = ""
templateFile = ""
apiid = ""
verbose = 0
toAdd = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "template=", "dashboard=", "cred=", "apiid=", "number=", "verbose"])
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
    elif opt == '--number':
        toAdd = int(arg)
    elif opt == '--verbose':
        verbose = 1

if not (dshb and templateFile and auth and apiid and toAdd):
    printhelp()

dashboard = tyk.dashboard(dshb, auth)

# read the policy defn
with open(templateFile) as PolicyFile:
    PolicyJSON=json.load(PolicyFile)
    PolicyFile.close()

numberCreated = dashboard.createPolicies(PolicyJSON, apiid, toAdd)

if numberCreated == toAdd:
    print(f'Success: {numberCreated} Policies created')
else:
    print(f'Failure: Only {numberCreated} of {toAdd} policies created')
    sys.exit(1)
