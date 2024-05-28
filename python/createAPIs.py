#!/usr/bin/python3

import argparse
import json
import os
import sys
sys.path.append(f'{os.path.abspath(os.path.dirname(__file__))}/module')
import tyk

scriptName = os.path.basename(__file__)

parser = argparse.ArgumentParser(description=f'{scriptName}: Will take the template and increment its name and listen path so that they do not clash, then add it as an API to the dashboard or gateway')

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-d', '--dashboard', dest='dshb', help="URL of the dashboard")
group.add_argument('-g', '--gateway', dest='gatw', help="URL of the gateway")

parser.add_argument('-c', '--cred', required=True, dest='auth', help="Dashboard API key or Gateway secret")
parser.add_argument('-n', '--name', dest='name', help="Base name of API")
parser.add_argument('-N', '--number', default=1, type=int, dest='toAdd', help="Numer of APIs to generate")
parser.add_argument('-t', '--template', required=True, dest='templateFile', help="API template file")
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

# create a new dashboard or gateway object
if args.dshb:
    args.dshb = args.dshb.strip('/')
    tykInstance = tyk.dashboard(args.dshb, args.auth)
else:
    args.gatw = args.gatw.strip('/')
    tykInstance = tyk.gateway(args.gatw, args.auth)

# read the API defn
with open(args.templateFile) as APIFile:
    APIjson=json.load(APIFile)
    APIFile.close()
    if args.name:
        # if we've been given a name then apply that
        if 'api_definition' in APIjson:
            APIjson["api_definition"]["name"] = args.name
            APIjson["api_definition"]["slug"] = args.name
            APIjson["api_definition"]["proxy"]["listen_path"] = '/'+args.name+'/'
            if args.verbose:
                print(f'[INFO]Creating API with name: {APIjson["api_definition"]["name"]}, slug:{APIjson["api_definition"]["slug"]}, listen_path {APIjson["api_definition"]["proxy"]["listen_path"]}')
        else:
            APIjson["name"] = args.name
            APIjson["slug"] = args.name
            APIjson["proxy"]["listen_path"] = '/'+args.name+'/'
            if args.verbose:
                print(f'[INFO]Creating API with name: {APIjson["name"]}, slug:{APIjson["slug"]}, listen_path {APIjson["proxy"]["listen_path"]}')

numberCreated = tykInstance.createAPIs(APIjson, args.toAdd)

if args.verbose:
    if numberCreated == args.toAdd:
        print(f'Success: {numberCreated} APIs created')
    else:
        print(f'Failure: Only {numberCreated} of {args.toAdd} APIs created')
        sys.exit(1)
else:
    print(numberCreated)
