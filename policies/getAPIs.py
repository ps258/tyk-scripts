#!/usr/bin/python3

#from audioop import add
#from curses import tparm
import json
import requests
import os
import getopt
import sys

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials>')
    print("    Will list APIID and name of each API found")
    sys.exit(2)

dshb = ""
auth = ""
verbose = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "cred=", "verbose"])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--verbose':
        verbose = 1

if not (dshb and auth):
    printhelp()

headers = {'Authorization' : auth}
# get the existing APIs
resp = requests.get(f'{dshb}/api/apis/?p=-1', headers=headers)
if resp.status_code != 200:
    print(resp.text)
    sys.exit(1)
apis = json.loads(resp.text)
for api in apis['apis']:
    print(f'{api["api_definition"]["name"]},{api["api_definition"]["api_id"]}')
