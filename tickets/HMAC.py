#!/usr/bin/python3

import time
import hmac
import hashlib
import base64
#from urllib.parse import urlparse, quote
import urllib.parse
import argparse
import json
import os
import sys
import requests

# Suppress the warnings from urllib3 when using a self signed certs
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

scriptName = os.path.basename(__file__)

description = "Will generate the correct HMAC http headers and call the API"
parser = argparse.ArgumentParser(description=f'{scriptName}: {description}')

parser.add_argument('--url', '-u', required=True, dest='url', help="The API URL to call")
parser.add_argument('--secret', '-s', required=True, dest='HmacSecret', help="HMAC secret")
parser.add_argument('--key', '-k', required=True, dest='ApiKey', help="API Key")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

# Reference date format
ref_date = "%a, %d %b %Y %H:%M:%S %Z"

# Prepare the request headers
timeNow = time.strftime(ref_date)
headers = {
    "Date": timeNow,
    "X-Test-1": "hello",
    "X-Test-2": "world"
}

# extract the url API path
parsed_url = urllib.parse.urlparse(args.url)

# Prepare the signature to include those headers
signature_string = f"(request-target): get {parsed_url.path}\n"
signature_string += f"date: {timeNow}\n"
signature_string += "x-test-1: hello\n"
signature_string += "x-test-2: world"
urllib.parse
if (args.verbose):
    print(f'{signature_string=}')

# HMAC-SHA1 Encode the signature
hmac_secret = args.HmacSecret
key = hmac_secret.encode('utf-8')
h = hmac.new(key, signature_string.encode('utf-8'), hashlib.sha1)

# Base64 and URL Encode the string
sig_string = base64.b64encode(h.digest()).decode('utf-8')
encoded_string = urllib.parse.quote(sig_string)

# Add the Authorization header
auth_header = f'Signature keyId="{args.ApiKey}",algorithm="hmac-sha1",headers="(request-target) date x-test-1 x-test-2",signature="{encoded_string}"'

headers["Authorization"] = auth_header
if (args.verbose):
    print(f'{headers=}')
    print(f'{auth_header=}')

resp = requests.get(args.url, headers=headers, verify=False)
if resp.status_code != 200:
    print(f'[FATAL]Tyk returned {resp.status_code}', file=sys.stderr)
    sys.exit(1)

print(json.dumps(resp.json(), indent=2))
