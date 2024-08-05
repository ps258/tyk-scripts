#!/usr/bin/python3

# a script to create a specified load.
# python isn't great at this sort of timing so the script isn't as useful asit might be

import time
import requests
import json
import signal
import sys
import os
import getopt
from ratelimit import limits, RateLimitException, sleep_and_retry

scriptName = os.path.basename(__file__)

session = requests.Session()
timeout_count = 0

URL=""
auth_token=""
request_rate=0
request_per=1
duration=0
cert_file=""
key_file=""
no_keepalive = 0

response_count = {}
timeout_seconds = 4
counts = [0,0]

# Suppress the warnings from urllib3 when using a self signed certs
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def signal_handler(sig, frame):
    print()
    duration = int(time.time()) - start_timestamp
    count = counts[0]
    timeout_count = counts[1]
    if 200 not in response_count:
        response_count[200] = 0
    print(f"A total of {count} calls with {timeout_count} timeouts. {response_count[200]/duration} rps 200s for {duration} seconds")
    for code in response_count:
        print(f"{response_count[code]} responses of {code}")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def printhelp():
    print(f'{scriptName} --url <API URL> --auth <auth token> --rate <rps> --per <period the rate applies to> --duration <number of seconds to run(should be a multipe of --per)> --cert <certificate file in pem format for mtls> --key <key file for the certificate in pem format> [--no-keepalive]')
    sys.exit(1)

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "url=", "auth=", "rate=", "per=", "duration=", "cert=", "key=", "no-keepalive"])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--url':
        URL = arg
    elif opt == '--auth':
        auth_token = arg
    elif opt == '--rate':
        request_rate = int(arg)
    elif opt == '--per':
        request_per = int(arg)
    elif opt == '--duration':
        duration = int(arg)
    elif opt == '--cert':
        cert_file = arg
    elif opt == '--key':
        key_file = arg
    elif opt == '--no-keepalive':
        no_keepalive = 1

if not (URL and auth_token and request_rate and request_per and duration and cert_file and key_file):
    print(f'A required argument is missing: URL={URL}, auth_token={auth_token}, request_rate={request_rate}, request_per={request_per}, duration={duration}, cert_file={cert_file}, key_file={key_file}')
    printhelp()

if duration % request_per:
    print(f'--duration {duration} is not a multiple of --per {request_per}')
    sys.exit(1)

@sleep_and_retry
@limits(calls=request_rate, period=request_per)
def make_calls(counts):
    counts[0]+=1
    headers = { 'Authorization': auth_token }
    try:
        if no_keepalive:    
            #print('Using the plain requests library so no keep alives')
            response = requests.get(URL, headers=headers, verify=False, timeout=timeout_seconds, cert=(cert_file, key_file))
        else:
            #print('Using the sessions library so will have keep alives')
            response = session.get(URL, headers=headers, verify=False, timeout=timeout_seconds, cert=(cert_file, key_file))
        #print(json.dumps(response.json(), indent=2))
        if not response.status_code in response_count:
            response_count[response.status_code] = 0
        response_count[response.status_code] += 1
        #print(response.status_code)
        #print(str(response.content))
    except requests.exceptions.Timeout:
        print(f"Request to {URL} timedout")
        counts[1]+=1


start_timestamp = int(time.time())
end_timestamp = start_timestamp + duration
while int(time.time()) < end_timestamp:
    make_calls(counts)

count = counts[0]
timeout_count = counts[1]

if 200 not in response_count:
    response_count[200] = 0
print(f"A total of {count} calls with {timeout_count} timeouts. {response_count[200]/duration} rps 200s")
for code in response_count:
    print(f"{response_count[code]} responses of {code}")
