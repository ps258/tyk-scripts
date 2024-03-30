#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials> --template <Polcy template file> --policyid <polid> --verbose')
    print("    Will take the template apply it to the policy id given")
    sys.exit(1)

dshb = ""
auth = ""
templateFile = ""
verbose = 0
policyid = ""

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "template=", "dashboard=", "cred=", "number=", "policyid=", "verbose"])
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
    elif opt == '--cred':
        auth = arg
    elif opt == '--policyid':
        policyid = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and templateFile and auth and policyid):
    printhelp()

# create a new dashboard object
tykInstance = tyk.dashboard(dshb, auth)

# read the policy defn
with open(templateFile) as PolicyFile:
    PolicyJSON=json.load(PolicyFile)
    PolicyFile.close()

resp = tykInstance.updatePolicy(json.dumps(PolicyJSON), policyid)
print(json.dumps(resp.json()))
if resp.status_code != 200:
    sys.exit(1)
