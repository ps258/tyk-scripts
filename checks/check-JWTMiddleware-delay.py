#!/usr/bin/python3

# looks for lines like the following which indicate slow JWKs
# time="Aug 02 11:06:13" level=debug msg=Finished api_id=1234567890 api_name=api1 code=200 mw=JWTMiddleware ns=6010 org_id=66b08f9c411022008d302aec origin=10.0.0.1 path=/listen/path

# it will print the largest delay found in the file as it comes across it.
# which will help with tracking down at least some of the problems

import re
import sys
from datetime import datetime, timedelta

max_delay = 0

def extract_TS(linestring):
    # "Aug 02 16:04:30"
    return re.findall(r"time=\"(\w{3}\s+\d{2}\s+\d{2}:\d{2}:\d{2})\"", linestring)[0]

def extract_delay(linestring):
    # ns=6010
    return int(re.findall(r"ns=(\d+)", linestring)[0])

for logfile in sys.argv[1:]:
    with open(logfile, 'r') as file:
        # Iterate over each line in the file
        for line in file:
            if 'mw=JWTMiddleware' in line and 'ns=' in line:
                timestamp = extract_TS(line)
                delay = extract_delay(line)
                if delay > max_delay:
                    print(f"{timestamp=}, {delay=} ({delay/1_000_000_000:.3f} s)")
                    max_delay = delay
