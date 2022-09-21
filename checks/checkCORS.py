#!/usr/bin/python3

# The intent of this script is to check the CORS headers returned
# Checks include
#import json

import requests
import sys
import getopt
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# globals
url = ""
origins = ""
verbose = 0

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --url <Rest URL> --origins <list of origins to try> [--verbose]')
    sys.exit(2)

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "url=", "origins=", "verbose"])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--url':
        #url = arg.strip().strip('/')
        url = arg
    elif opt == '--verbose':
        verbose = 1
    elif opt == '--origins':
        origins = arg.split(",")

if not (url or len(origins)):
    printhelp()

for origin in origins:
    print(f'Testing Origin: {origin}')
    for method in ['GET', 'PUT', 'POST', 'OPTIONS', 'DELETE', 'HEAD', 'CONNECT', 'TRACE']:
        resp = requests.options(f'{url}', headers={'Origin' : origin, 'Access-control-request-method': method}, verify=False)
        code = resp.status_code

        # Current understading only, might be wrong:
        #  if Access-Control-Allow-Origin is populated, it has to contain the domain from Origin, '*' isn't good enough
        if 'Access-Control-Allow-Origin' in resp.headers:
            if resp.headers['Access-Control-Allow-Origin'] == origin:
                if 'Access-Control-Allow-Methods' in resp.headers:
                    if verbose:
                        print(f'    Method allowed: {method} , OPTIONS call status:{code}')
                    else:
                        print(f'    Method allowed: {method}')
        elif 'Access-Control-Allow-Methods' in resp.headers:
            # if Access-Control-Allow-Origin doesn't exist, just go with the answer in Access-Control-Allow-Methods
            # I don't know if this is correct or not
            if verbose:
                print(f'    Method allowed: {method} , OPTIONS call status:{code}')
            else:
                print(f'    Method allowed: {method}')
        elif verbose:
                print(f"    Disallowed by CORS: {method}")
