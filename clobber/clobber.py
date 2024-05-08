#!/usr/bin/python3

import json
import os
import getopt
import sys
import redis
import pymongo        # pip3 install pymongo
from bson import ObjectId

scriptName = os.path.basename(__file__)

def printhelp():
    print(f'{scriptName} [--setOrgID <orgid>|--api <api.json>|--policy <policy.json>|--key <key.json>] [--mongo <URL>|--redis<IP:port>')
    print("    --setOrgID <orgid> sets the orgid in the mongo collections tyk_analytics/tyk_organisations and tyk_analytics/tyk_analytics_users. There must be only one org defined.")
    print("    --api <api.json> publishes the api directly into the mongodb instance specified with --mongo")
    print("    --policy <policy.json> publishes the api directly into the mongodb instance specified with --mongo")
    print("    --key <key.json> publishes the api directly into the mongodb instance specified with --mongo")
    print("    --mongo <mongoURL> the mongo DB connection string")
    print("    --redis <IP:port> the redis IP address and port")
    sys.exit(1)

newOrgID = ""
apiFile = ""
policyFile = ""
keyFile = ""
mongoConnectionString = ""
redisHost = ""
redisPort = ""

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "setOrgID=", "api=", "policy=", "key=", "mongo=", "redis="])
except getopt.GetoptError as opterr:
    print(f'Error in option: {opterr}')
    printhelp()

for opt, arg in opts:
    if opt == '--help':
        printhelp()
    elif opt == '--setOrgID':
        newOrgID = arg
        if (apiFile or policyFile or keyFile):
            print("--setOrgID must be run alone")
            printhelp()
    elif opt == '--api':
        apiFile = arg
        if (policyFile or keyFile or newOrgID):
            pring("--api must be run alone")
    elif opt == '--policy':
        policyFile = arg
        if (apiFile or keyFile or newOrgID):
            pring("--policy must be run alone")
    elif opt == '--key':
        keyFile = arg
        if (policyFile or apiFile or newOrgID):
            pring("--key must be run alone")
    elif opt == '--mongo':
        mongoConnectionString = arg
    elif opt == '--redis':
        redisIPandPort = arg
        redisHost,redisPort = arg.split(':')

if ((newOrgID or apiFile or policyFile) and not mongoConnectionString):
    print("Must specify --mongo when using --setOrgID or --api or --policy")
    printhelp()
if (keyFile and not (redisHost and redisPort)):
    print("Must specify --redis when using --key")
    printhelp()

if not (newOrgID or apiFile or policyFile or keyFile):
    print("Must specify exactly one of --setOrgID --api --policy --key")
    printhelp()

if mongoConnectionString:
    # we're doing something with mongo
    mongoClient = pymongo.MongoClient(mongoConnectionString)
    if "tyk_analytics" in mongoClient.list_database_names():
        tykDB = mongoClient["tyk_analytics"]
        collections = tykDB.list_collection_names()
        if newOrgID:    # Update org and users to new orgid
            if not "tyk_organisations" in collections:
                print(f"'tyk_organisations' not found in 'tyk_analytics' in {mongoConnectionString}")
                sys.exit(1)
            if not "tyk_analytics_users" in collections:
                print(f"'tyk_analytics_users' not found in 'tyk_analytics' in {mongoConnectionString}")
                sys.exit(1)
            # Fetch the org, checking that there's only one
            tyk_organisations = tykDB["tyk_organisations"]
            orgCount = 0
            for org in tyk_organisations.find():
                orgCount += 1
            if orgCount != 1:
                print(f"Must be exactly 1 organisation. Found {orgCount}")
                sys.exit(1)
            oldOrgID = org["_id"]

            # create a copy of the existing org, but with the new orgid
            print(f"Copying Org {oldOrgID} to {newOrgID}")
            org["_id"] = ObjectId(newOrgID)
            tyk_organisations.insert_one(org)

            # Delete the old organisation entry
            print(f"Removing old Org {oldOrgID}")
            tyk_organisations.delete_one({"_id": oldOrgID})

            # update the users to the new orgid
            print(f"Migrating users to {newOrgID}")
            tyk_analytics_users = tykDB["tyk_analytics_users"]
            oldOrgUsersQuery = { "orgid": f"{oldOrgID}" }
            users = tyk_analytics_users.find(oldOrgUsersQuery)
            for user in users:
                print(f"Found user {user['emailaddress']} in org {oldOrgID}. You will need to reset their access key")
            tyk_analytics_users.update_many(oldOrgUsersQuery, { "$set": { "orgid": newOrgID } })
        if apiFile:
            # this isn't really worth doing since there are too many things that are base64 encoded.
            # you would need to read in the API, replace all the text strings with base64 ones
            # then delete the old strings
            # too error prone.
            with open(apiFile, 'r') as apiJSONFile:
                API = json.load(apiJSONFile)
            if "api_definition" in API:
                API = API["api_definition"]
            API["_id"] = ObjectId(API["id"])
            #API.pop("id", None)
            tyk_apis = tykDB["tyk_apis"]
            tyk_apis.insert_one(API)
        if policyFile:
            with open(policyFile, 'r') as policyJSONFile:
                policy = json.load(policyJSONFile)
            tyk_policies = tykDB["tyk_policies"]
            tyk_policies.insert_one(policy)
    else:
        print(f"'tyk_analytics' DB not found in {mongoConnectionString}")
        sys.exit(1)

elif redisIPandPort:
    # we're doing something with redis
    keyCount = 0
    r = redis.Redis(host=redisHost, port=redisPort, db=0)
    if keyFile:
        with open(keyFile, 'r') as keyJSONFile:
            keydict = json.load(keyJSONFile)
        if "keys" in keydict:
            for key in keydict["keys"]:
                keyID = f'apikey-{key["key_id"]}'
                print(f'Adding {keyID}')
                keyData = key["data"]
                r.set(keyID, json.dumps(key["data"]))
                keyCount += 1
        else:
            keyID = keydict["key_id"]
            keyData = keydict["data"]
            r.set(keyID, json.dumps(keydict["data"]))
            keyCount += 1
        print(f'{keyCount} keys created/updated')
