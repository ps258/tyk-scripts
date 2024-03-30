#!/usr/bin/python3

import json
import os
import getopt
import sys
import time
from datetime import datetime, timedelta
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --dashboard <dashboard URL> --cred <Dashboard API credentials> --startdate <YYYY/MM/DD> --enddate <YYYY/MM/DD>')
    print("    returns the usage of all apis for the period")
    sys.exit(1)

dshb = ""
auth = ""
verbose = 0
startdate = (datetime.now() - timedelta(days=1)).strftime("%Y/%m/%d")
enddate = (datetime.now()).strftime("%Y/%m/%d")

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "cred=", "startdate=", "enddate="])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
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

tykInstance = tyk.dashboard(dshb, auth)

start = startdate.split('/')
end = enddate.split('/')
# symbols for the contents of 'start' and 'end' for readability
year = 0
day = 2
month = 1

resp = tykInstance.getAPIUsage(startday=start[day], startmonth=start[month], startyear=start[year], endday=end[day], endmonth=end[month], endyear=end[year])
print(json.dumps(resp.json(), indent=2))
if resp.status_code != 200:
    sys.exit(1)
