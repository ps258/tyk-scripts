#!/usr/bin/python3

import argparse
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

urls=""
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
    print(f'{scriptName} --url <API URL, URL, URL> --auth <auth token> --rate <rps> --per <period the rate applies to> --duration <number of seconds to run(should be a multipe of --per)> --cert <certificate file in pem format for mtls> --key <key file for the certificate in pem format> [--no-keepalive]')
    sys.exit(1)

parser = argparse.ArgumentParser(description=f'{scriptName}: Calls the given API(s) at the given rate using the given credentials')

parser.add_argument('-u', '--urls', required=True, help="URLs of the APIs to call")
parser.add_argument('-a', '--auth', required=True, help="Authorization header value")
parser.add_argument('-r', '--rate', required=True, type=int, help="The count of calls allowed in the --per period")
parser.add_argument('-p', '--per', required=True, type=int, help="The period (seconds) for --rate calls to be made")
parser.add_argument('-d', '--duration', required=True, type=int, help="The length of time (seconds) to run the load")
parser.add_argument('-c', '--cert', required=True, help="The PEM encoded file containing the certificate for mTLS")
parser.add_argument('-k', '--key', required=True, help="The PEM encoded file containing the key for the certificate")
parser.add_argument('-n', '--no-keepalive', action='store_true', dest='nokeepalive', help="Don't use keepalives (default is to use them)")
parser.add_argument('-v', '--verbose', action='store_true', help="Verbose output")

args = parser.parse_args()

urls=args.urls
auth_token = args.auth
request_rate = args.rate
request_per = args.per
duration = args.duration
cert_file = args.cert
key_file = args.key
no_keepalive = args.nokeepalive


if not (urls and auth_token and request_rate and request_per and duration and cert_file and key_file):
    print(f'A required argument is missing: URL={urls}, auth_token={auth_token}, request_rate={request_rate}, request_per={request_per}, duration={duration}, cert_file={cert_file}, key_file={key_file}')
    printhelp()

if duration % request_per:
    print(f'--duration {duration} is not a multiple of --per {request_per}')
    sys.exit(1)

@sleep_and_retry
@limits(calls=request_rate/len(urls.split(',')), period=request_per)
def make_calls(counts):
    counts[0]+=1
    headers = { 'Authorization': auth_token }
    try:
        for url in urls.split(','):
            if no_keepalive:    
                #print('Using the plain requests library so no keep alives')
                response = requests.get(url, headers=headers, verify=False, timeout=timeout_seconds, cert=(cert_file, key_file))
            else:
                #print('Using the sessions library so will have keep alives')
                response = session.get(url, headers=headers, verify=False, timeout=timeout_seconds, cert=(cert_file, key_file))
            #print(json.dumps(response.json(), indent=2))
            if not response.status_code in response_count:
                response_count[response.status_code] = 0
            response_count[response.status_code] += 1
            #print(response.status_code)
            #print(str(response.content))
    except requests.exceptions.Timeout:
        print(f"Request to {url} timedout")
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
