#!/usr/bin/python3

# looks in the debug logs for the time difference between
# level=debug msg="Pulling JWK"
# and
# level=debug msg="Caching JWK"
# in the gateway logs.
# Assumes that there will be matching pairs of these log lines and that the JWKS will reply in the order of the requests

import re
import sys
from datetime import datetime, timedelta

JWK_Fetch_TimeStamp = []
JWK_Fetch_Line = []

found_pulling_line = False

def extract_TS(linestring):
    # "Aug 02 16:04:30"
    ts =  re.findall(r"time=\"(\w{3}\s+\d{2}\s+\d{2}:\d{2}:\d{2})\"", linestring)[0]
    return datetime.strptime(ts, '%b %d %H:%M:%S')

for logfile in sys.argv[1:]:
    with open(logfile, 'r') as file:
        # Iterate over each line in the file
        for line in file:
            if 'Pulling JWK' in line:
                timestamp = extract_TS(line)
                JWK_Fetch_TimeStamp.append(timestamp)
                JWK_Fetch_Line.append(line)
                found_pulling_line = True
            if found_pulling_line and 'Caching JWK' in line:
                timestamp = extract_TS(line)
                # this can fail if we get a "Caching JWK" before a "Pulling JWK"
                delta = timestamp - JWK_Fetch_TimeStamp[0]
                if delta.total_seconds():
                    print(f"'Pulling JWK' at {JWK_Fetch_TimeStamp[0].strftime('%b %d %H:%M:%S')} 'Caching JWK' at {timestamp.strftime('%b %d %H:%M:%S')} delta is {delta.total_seconds()}")
                JWK_Fetch_TimeStamp.pop(0)
                JWK_Fetch_Line.pop(0)

