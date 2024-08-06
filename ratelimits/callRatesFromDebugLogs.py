#!/usr/bin/python3

# find lines like the below and report totals per second
# time="Apr 15 07:58:51" level=debug msg=Finished api_id=XXX api_name="API Name # with tag" code=200 key="****" mw=RateLimitAndQuotaCheck ns=17185 org_id=XXX origin=IP.IP.IP.IP path=/api/call/v1/path

# usage ./script logfile1 logfile2



import re
import sys

rates = {}

regex=r'time=(\".*?\")\s+level=debug\s+msg=Finished\s+api_id=(\w+?)\s+api_name=(\"*\w+\"*)\s+code=(\d{3}).*mw=RateLimitAndQuotaCheck.*origin=(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})\s+path=(.*)\s*$'

for logfile in sys.argv[1:]:
    with open(logfile, 'r') as f:
        for line in f:
            match = re.search(regex, line)
            if match:
                time=match.group(1)
                apiID=match.group(2)
                apiName=match.group(3)
                httpCode=match.group(4)
                origin=match.group(5)
                path=match.group(6)
                #print(line.strip())
                #print(f'{time}, {apiID}, {apiName}, {httpCode}, {origin}, {path}')
                if time not in rates:
                    rates[time] = {}
                if apiID not in rates[time]:
                    rates[time][apiID] = {}
                if httpCode not in rates[time][apiID]:
                    rates[time][apiID][httpCode] = 0
                rates[time][apiID][httpCode] += 1

for time in sorted(rates.keys()):
    for api in sorted(rates[time].keys()):
        print(f'{time}: api={api} ',end='')
        first = True
        for response_code in sorted(rates[time][api].keys()):
            if first:
                print(f'{response_code}: {rates[time][api][response_code]}', end='')
                first = False
            else:
                print(f', {response_code}: {rates[time][api][response_code]} ', end='')
        print()
