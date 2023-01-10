#!/usr/bin/python3

# The intent of this script is to check the CORS headers returned
# Checks include
#  That the origin specified in the Origin header matches the returned on in Access-Control-Allow-Origin
#  That the method specified in Access-Control-Request-Method matches the one returned in Access-Control-Allow-Methods
#  the headers specified in Access-Control-Request-Headers matches the ones returned in Access-Control-Allow-Headers
# Some Tyk specific notes.
#  Tyk will proxy upstream if 'Access-control-request-method: ' is not set even when CORS pass through is off
#  Sample curl CORS request for tyk when proxying to http://httpbin.org/anything
#   curl -X OPTIONS -I https://10.0.0.23:5003/api1/ -H 'Origin: http://fred.com' -H 'Access-Control-Request-Headers: Fred' -H 'Access-control-request-method: GET'

# Note that Tyk changes headers to be canonical values so "--headers fred" gets returned as "Access-Control-Allow-Headers: Fred" (if it's allowed) so this code checks responses in a case insensitive way

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
Allowed = True
reason = ""
requestHeaders = ""

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} --url <Rest URL> --origins <list of origins to try> [--verbose]')
    sys.exit(2)

def checkOrigin(origin, headers) :
    return headers['Access-Control-Allow-Origin'] == origin

def checkMethod(method, headers) :
    return method in headers['Access-Control-Allow-Methods']

def checkRequestHeader(header, headers) :
    return header.lower() == headers['Access-Control-Allow-Headers'].lower()

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "url=", "origins=", "headers=", "verbose"])
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
    elif opt == '--headers':
        requestHeaders = arg.split(",")

if not (url or len(origins)):
    printhelp()

for origin in origins:
    print(f'Testing Origin: {origin}')
    for method in ['GET', 'PUT', 'POST', 'OPTIONS', 'DELETE', 'HEAD', 'CONNECT', 'TRACE']:
        Allowed = True
        reason = ''
        resp = requests.options(f'{url}', headers={'Origin' : origin, 'Access-Control-Request-Method': method}, verify=False)
        code = resp.status_code

        # Current understading only, might be wrong:
        #  if Access-Control-Allow-Origin is populated, it has to contain the domain from Origin, '*' isn't good enough
        if 'Access-Control-Allow-Origin' in resp.headers:
            if not checkOrigin(origin, resp.headers):
                Allowed = False
                reason = f'Origin {origin} not in Access-Control-Allow-Origin: '
        else:
            Allowed = False
            reason = f'Header Access-Control-Allow-Origin not present: '
        if 'Access-Control-Allow-Methods' in resp.headers:
            # if Access-Control-Allow-Origin doesn't exist, just go with the answer in Access-Control-Allow-Methods
            # I don't know if this is correct or not
            if not checkMethod(method, resp.headers):
                Allowed = False
                reason = f'{reason}Method {method} not in Access-Control-Allow-Methods: '
        else:
            Allowed = False
            reason = f'{reason}Header Access-Control-Allow-Methods not present: '
        if len(requestHeaders):
            # if there are reqest headers we need to recheck an OPTIONS call setting Access-Control-Request-Headers
            for requestHeader in requestHeaders:
                #print(f'Request header is: {requestHeader}')
                resp = requests.options(f'{url}', headers={'Origin': origin, 'Access-Control-Request-Method': method, 'Access-Control-Request-Headers': requestHeader}, verify=False)
                code = resp.status_code
                #print(f'code: {code}')
                if 'Access-Control-Allow-Headers' in resp.headers:
                    if not checkRequestHeader(requestHeader, resp.headers):
                        Allowed = False
                        reason = f'{reason}Request header {requestHeader} is not in Access-Control-Allow-Headers: '

                else:
                    Allowed = False
                    reason = f'{reason} Header Access-Control-Allow-Headers not present for "{requestHeader}": '
        if Allowed:
            print(f'    {method} allowed:')
        else:
            if verbose:
                print(f'    {method} disallowed by CORS: {reason}')
