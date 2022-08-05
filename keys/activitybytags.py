#!/usr/bin/python3

# the intent of this script is to enumerate the the number of successful uses made by the tags in keys.
# imagine you have 2 customers. You issue 3 keys to each and add tags for each customer to each key
# then you want to know the total consumption by each customer.

import json
import requests
import sys
import getopt
import os
from datetime import datetime

# mine
startDate = ""
endDate = ""
dshb = ""
tagUse = {}
verbose = 0
tags = ()
auth = ""

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --startDate <yyyy/mm/dd> --endDate <yyyy/mm/dd> --dashboard <dashboard_URL> --cred <Dashboard API credentials> --tags <tag1,tag2,..>')
    sys.exit(2)

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "startDate=", "endDate=", "dashboard=", "cred=", "tags=", "verbose"])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--startDate':
        startDate = arg
    elif opt == '--endDate':
        endDate = arg
    elif opt == '--dashboard':
        dshb = arg.strip().strip('/')
    elif opt == '--cred':
        auth = arg
    elif opt == '--tags':
        tags = tuple(arg.split(","))
    elif opt == '--verbose':
        verbose = 1

for tag in tags:
    tagUse[tag] = 0

if not (dshb or startDate or endDate or tags or auth ):
    printhelp()

# split out startDate and endDate
try:
    startDate = datetime.strptime(startDate, "%Y/%m/%d")
except ValueError as ve:
    print(f'Unable to parse startDate {startDate}:', ve)
    printhelp()
try:
    endDate = datetime.strptime(endDate, "%Y/%m/%d")
except ValueError as ve:
    print(f'Unable to parse endDate {endDate}:', ve)
    printhelp()

startDay = startDate.day
startMon = startDate.month
startYr = startDate.year
endDay = endDate.day
endMon = endDate.month
endYr = endDate.year

# get keys
auth_header = {'Authorization' : auth}
resp = requests.get(f'{dshb}/api/activity/keys/{startDay}/{startMon}/{startYr}/{endDay}/{endMon}/{endYr}?p=-1', headers=auth_header)
keys = json.loads(resp.text)

if verbose:
    print("List of all keys:")
    for keyid in keys['data']:
        print(keyid['id']['key'])

if verbose:
    print("API use by each key:")
    for keyid in keys['data']:
        key = keyid['id']['key']
        resp = requests.get(f'{dshb}/api/activity/keys/{key}/{startDay}/{startMon}/{startYr}/{endDay}/{endMon}/{endYr}?res=day&p=-1', headers=auth_header)
        keyUse = json.loads(resp.text)
        print(f'Key {key}: Success {keyUse["data"][0]["success"]}')
        print(f'Key {key}: Failed  {keyUse["data"][0]["error"]}')
        print(f'Key {key}: Total   {keyUse["data"][0]["hits"]}')

if verbose:
    print("Tag success by key:")
for keyid in keys['data']:
    key = keyid['id']['key']
    for tag in tags:
        url=f'{dshb}/api/activity/keys/{key}/{startDay}/{startMon}/{startYr}/{endDay}/{endMon}/{endYr}?res=day&p=-1&tags={tag}'
        #print(url)
        resp = requests.get(url, headers=auth_header)
        keyUse = json.loads(resp.text)
        try:
            hits = keyUse["data"][0]["success"]
        except:
            hits = 0
        if verbose:
            print(f'Key {key}: Tag {tag}, Success {hits}')
        tagUse[tag] += hits

print("Use by tag across all keys:")
for tag in tags:
    print(tag, " -> ", tagUse[tag])
