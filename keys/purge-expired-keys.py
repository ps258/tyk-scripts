#!/usr/bin/python3

# This is a script to help with tidying up unwanted Tyk API keys directly from Redis.
# It does not use tyk APIs at all.
# It supports both delete or list mode. Use the --list option to explore what keys exist and what ones should
# be deleted before replacing --list with --delete to purge the unwanted keys.

# For caution the orgid of the keys to be considered must be given even when there is only one org id in redis.

# Keys have an expiery timestamp in epoch seconds. Keys which expired before the timestamp given in --epoch will
# be considered for listing or deletion.

# The selected keys can be further narrowed down using the --policy and --api options. Either or both can be given.
# Only apikeys which match the given --policy and/or --api options will be included but only at most one of each can be given.

# USE THIS OPTION WITH CAUTION:
# Keys with an expiery of 0 are set to never expire. They are dealt with as a special case and only considered
# when '--epoch 0' is given.
# Using the --api and --policy options will allow the non-expiring keys for a particular API or policy to be removed

# The script is not redis cluster aware. It must be pointed at a master redis replica (if replication is active)
# If redis is sharded the script must be used on each master in turn

import redis
import json
import sys
import getopt
import datetime


listKeys = 0
deleteKeys = 0
listedKeys = 0
deletedKeys = 0

maxAge = -1
host = ""
port = ""
delpol = None
delapi = None
orgid = None
redisPassword = None

def printhelp():
    print('purge-expired-keys.py [--delete|--list] --host <hostname> --port <portnum> --epoch <epoch> --orgid <orgid> --password <redisPassword> --api <APIID> --policy <POLICYID>')
    sys.exit(2)

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "delete", "list", "epoch=", "host=", "port=", "password=", "api=", "policy=", "orgid="])
except getopt.GetoptError:
    printhelp()

for opt, arg in opts:
    if opt == '--delete':
        deleteKeys = 1
    elif opt == '--list':
        listKeys = 1
    elif opt == '--epoch':
        maxAge = int(arg)
    elif opt == '--host':
        host = arg
    elif opt == '--port':
        port = arg
    elif opt == '--api':
        delapi = arg
    elif opt == '--policy':
        delpol = arg
    elif opt == '--orgid':
        orgid = arg
    elif opt == '--password':
        redisPassword = arg

if deleteKeys and listKeys:
    print('Cannot both list and delete keys. Choose one')
    printhelp()

if not (deleteKeys or listKeys):
    print('Must specify delete or list')
    printhelp()

if maxAge < 0:
    print('Must specify epoch second cutoff for keys to be deleted. Use 0 to target just non-expiring keys which are otherwise ignored')
    printhelp()

if not host:
    host="127.0.0.1"

if not port:
    port="6379"

if not orgid:
    print('Must specify an orgid')
    printhelp()

def shoulddel(apikey, apiid, polid, orgid):
    if orgid != apikey['org_id']:
        # print(f"Orgid mismatch: {orgid!r} != {apikey['org_id']!r}")
        return False
    if apiid is not None:
        if apiid not in apikey['access_rights']:
            # print(f"apiid mismatch: {apiid!r} not in {apikey['access_rights']!r}")
            return False
    if polid is not None:
        if polid not in apikey['apply_policies']:
            # print(f"polid mismatch: {polid} not in {apikey['apply_policies']!r}")
            return False
    return True

print(f"Attempting to connect to redis on {host}:{port}")
r = redis.StrictRedis(host=host, port=port, db=0, password=redisPassword)
rep = r.info('Replication')
if 'role' in rep:
    role=rep['role']
    if role == 'slave':
        print(f"[FATAL]Node is a replica, must connect to a master node {rep['master_host']}:{rep['master_port']}")
        sys.exit(2)

maxDateTime = datetime.datetime.fromtimestamp( maxAge )
print(f"Searching for keys that expired before {maxAge}, ({maxDateTime})")

for key in r.scan_iter("apikey-*"):
    apikey = json.loads(r.get(key))
    keyString = key.decode('utf-8')
    expires = int(apikey["expires"])
    if maxAge > 0:
        # ignore the ones with 'expires' equal to 0, they are the non-expiring apikeys
        if expires == 0:
            # skip because this is a non-expiring key
            next
        elif expires <= maxAge:
            if shoulddel(apikey, delapi, delpol, orgid):
                if listKeys:
                    expiresDateTime = datetime.datetime.fromtimestamp( expires )
                    print(f"{keyString} expires {expires} ({expiresDateTime}) <= {maxAge} ({maxDateTime})")
                    listedKeys += 1
                else:
                    # expiresDateTime = datetime.datetime.fromtimestamp( expires )
                    # print(f"Deleting: {keyString} expires {expires} ({expiresDateTime}) <= {maxAge} ({maxDateTime})")
                    r.delete(key)
                    deletedKeys += 1
    else:
        # list or delete all the non-expiring keys (maxAge == 0 and expires == 0)
        if expires == 0:
            if shoulddel(apikey, delapi, delpol, orgid):
                if listKeys:
                    print(keyString, expires, '<=', maxAge)
                    listedKeys += 1
                else:
                    # print('Deleting: ', keyString, expires, '<=', maxAge)
                    r.delete(key)
                    deletedKeys += 1

if listKeys:
    print(listedKeys, 'keys listed')
else:
    print(deletedKeys, 'keys deleted')
