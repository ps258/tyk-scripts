#!/usr/bin/python3

import json
import os
import getopt
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

dshb = ""
gatw = ""
max_wait_time = 10

def printhelp():
    print(f'{scriptName} [--dashboard <dashboard URL>|--gateway <gateway URL>] --time max_wait_time')
    print('    Will wait until the dashboard or gateway is up. Waiting at most max_wait_time seconds')
    sys.exit(1)

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "dashboard=", "gateway=", "time="])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--gateway':
        gatw = arg.strip().strip('/')
    elif opt == '--time':
        max_wait_time = int(arg)

if not (dshb or gatw):
    printhelp()

# create a dashboard or gateway object
if dshb:
    tykInstance = tyk.dashboard(dshb)
else:
    tykInstance = tyk.gateway(gatw)

if not tykInstance.waitUp(max_wait_time):
    print(f'[FATAL]Tyk is not up after waiting {max_wait_time}s', file=sys.stderr)
    sys.exit(1)
