#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --cred <Dashboard API key|Gateway secret> --template <Policy template file> --apiid <apiid> --verbose --number <number to receate>')
    print("    Will create policies for the API_ID given")
    sys.exit(1)

dshb = ""
gatw = ""
auth = ""
templateFile = ""
apiid = ""
verbose = 0
toAdd = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "gateway=", "template=", "cred=", "apiid=", "number=", "verbose"])
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
    elif opt == '--number':
        toAdd = int(arg)
    elif opt == '--verbose':
        verbose = 1

if not ((dshb or gatw) and templateFile and auth and apiid and toAdd):
    printhelp()

# create a new dashboard or gateway object
if dshb:
    tykInstance = tyk.dashboard(dshb, auth)
else:
    tykInstance = tyk.gateway(gatw, auth)

# read the policy defn
with open(templateFile) as PolicyFile:
    PolicyJSON=json.load(PolicyFile)
    PolicyFile.close()

numberCreated = tykInstance.createPolicies(PolicyJSON, apiid, toAdd)

if numberCreated == toAdd:
    print(f'Success: {numberCreated} Policies created')
else:
    print(f'Failure: Only {numberCreated} of {toAdd} policies created')
    sys.exit(1)
