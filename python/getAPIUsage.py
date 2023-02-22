#!/usr/bin/python3

import json
import os
import getopt
import sys
import time
sys.path.append(f'{os.environ.get("HOME")}/code/tyk-scripts/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials> --startdate <YYYY/MM/DD> --enddate <YYYY/MM/DD>')
    print("    returns the usage of all apis for the period")
    sys.exit(1)

dshb = ""
auth = ""
verbose = 0
startdate = ""
enddate = ""

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "cred=", "startdate=", "enddate="])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--startdate':
        startdate = arg
    elif opt == '--enddate':
        enddate = arg

if not (dshb and auth):
    printhelp()

if not startdate:
    startdate = time.strftime("%Y/%m/%d")
if not enddate:
    enddate = time.strftime("%Y/%m/%d")

dashboard = tyk.dashboard(dshb, auth)

start = startdate.split('/')
end = enddate.split('/')

resp = dashboard.getAPIUsage(startday=start[2], startmonth=start[1], startyear=start[0], endday=end[2], endmonth=end[1], endyear=end[0])
print(json.dumps(resp.json(), indent=2))
if resp.status_code != 200:
    sys.exit(1)
