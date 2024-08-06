#!/usr/bin/python3

# looks in the debug logs for lines like the following which indicate slow middleware
# time="Aug 02 11:06:13" level=debug msg=Finished api_id=1234567890 api_name=api1 code=200 mw=JWTMiddleware ns=6010 org_id=66b08f9c411022008d302aec origin=10.0.0.1 path=/listen/path

# by default it ignores the mw=ReverseProxy lines because the are the upstream delay
# you can specify the middleware to check for with the --mw option

# it will print the largest delay found in the file as it comes across it.
# which will help with tracking down at least some of the problems

import argparse
import re
import sys
import os
from datetime import datetime, timedelta

scriptName = os.path.basename(__file__)
max_delay = 0
middleware_search_string = 'mw='
proxy = False

description = "Will search a gateway debug log file for middleware timings and point out large ones. The default behavour is to record the largest delay yet found as it is found but with --threshold you can show any delay greater than the threshold"
parser = argparse.ArgumentParser(description=f'{scriptName}: {description}')

parser.add_argument('--logs', '-l', required=True, dest='logs', nargs='+', help="List of log files to parse")
parser.add_argument('--mw', '-m', required=False, dest='middleware', help="The middleware name to search for. Defaults to all except mw=ReverseProxy")
parser.add_argument('--threshold', '-t', default = 0, type = int, required=False, dest='threshold', help="Show any record that took more than this many nanoseconds")
parser.add_argument('--proxy', '-p', action='store_true', dest='proxy', help="Include ReverseProxy, which will be large")
parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help="Verbose output")

args = parser.parse_args()

if args.middleware:
    middleware_search_string = args.middleware

if args.proxy:
    proxy = True

def extract_middleware(linestring):
    # "Aug 02 16:04:30"
    return re.findall("mw=(\w+)\s", linestring)[0]

def extract_TS(linestring):
    # "Aug 02 16:04:30"
    return re.findall(r"time=\"(\w{3}\s+\d{2}\s+\d{2}:\d{2}:\d{2})\"", linestring)[0]

def extract_delay(linestring):
    # ns=6010
    return int(re.findall(r"ns=(\d+)", linestring)[0])

for logfile in args.logs:
    with open(logfile, 'r') as file:
        # Iterate over each line in the file
        for line in file:
            if middleware_search_string in line and 'ns=' in line:
                if not proxy and 'mw=ReverseProxy' in line:
                    continue
                timestamp = extract_TS(line)
                delay = extract_delay(line)
                middleware_name = extract_middleware(line)
                if args.threshold:
                    if delay > args.threshold:
                        print(f"T{timestamp=}, {middleware_name}, {delay=} ({delay/1_000_000_000:.3f} s)")
                        if args.verbose:
                            print(line)
                elif delay > max_delay:
                    print(f"M{timestamp=}, {middleware_name}, {delay=} ({delay/1_000_000_000:.3f} s)")
                    if args.verbose:
                        print(line)
                    max_delay = delay
