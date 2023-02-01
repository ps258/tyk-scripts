#!/usr/bin/python3

import json
import requests
import os
import getopt
import sys

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials> --template <Policy template file> --apiid --verbose')
    print("    Will create a new unique policy for the API_ID given")
    sys.exit(2)

dshb = ""
auth = ""
templateFile = ""
apiid = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "template=", "dashboard=", "cred=", "apiid=", "verbose"])
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

# read the policy defn
with open(templateFile) as PolicyFile:
    PolicyJSON=json.load(PolicyFile)
    PolicyFile.close()
PolicyName = "Policy"
headers = {'Authorization' : auth}
# get the existing Policies
resp = requests.get(f'{dshb}/api/portal/policies/?p=-1', headers=headers)
if resp.status_code != 200:
    print(resp.text)
    sys.exit(1)
policies = json.loads(resp.text)
#print(policies)
# create a dictionary of all policy names
allnames = dict()
for policy in policies['Data']:
    name = policy["name"]
    allnames[name] = 1

headers["Content-Type"] = "application/json"
# find the first available name
i = 1
while PolicyName+str(i) in allnames:
    i += 1
PolicyJSON["name"]=PolicyName+str(i)
PolicyJSON["access_rights_array"] = json.loads('[{ "api_id": "' + apiid + '", "versions": [ "Default" ], "allowed_urls": [], "restricted_types": [], "limit": null, "allowance_scope": "" }]')

print(f'Adding policy {PolicyJSON["name"]}')
if verbose:
    print(json.dumps(PolicyJSON, indent=2))

resp = requests.post(f'{dshb}/api/portal/policies', data=json.dumps(PolicyJSON), headers=headers, allow_redirects=False)
print(resp.text)
