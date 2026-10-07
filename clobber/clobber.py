#!/usr/bin/python3

import json
import os
import getopt
import sys
import redis
import pymongo        # pip3 install pymongo
from bson import ObjectId

scriptName = os.path.basename(__file__)
mongoDatabase = "tyk_analytics"

def printhelp():
    print(f'{scriptName} [--setOrgID <orgid>|--api <api.json>|--policy <policy.json>|--key <key.json>] [--mongo <URL>|--redis<IP:port>')
    print(f"    --database The mongo database (not the connection string, the database) to use, Defaults to '{mongoDatabase}'")
    print(f"    --setOrgID <orgid> sets the orgid in the mongo collections {mongoDatabase}/tyk_organisations and {mongoDatabase}/tyk_analytics_users. There must be only one org in the existing install.")
    print("    --analytics sets the orgid in the mongo analytics collections")
    print("    --policiesApis sets the orgid in all of the APIs and policies")
    print("    --api <api.json> publishes the api directly into the mongodb instance specified with --mongo")
    print("    --policy <policy.json> publishes the policy directly into the mongodb instance specified with --mongo")
    print("    --key <key.json> publishes the key directly into the redis instance specified with --redis")
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
updateAnalytics = False
updateAPIsPolicies = False

try:
    opts, args = getopt.getopt(sys.argv[1:], "", ["help", "setOrgID=", "api=", "policy=", "key=", "mongo=", "redis=", "database=", "analytics", "policiesApis"])
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
            print("Must specify exactly one of --setOrgID --api --policy --key")
            printhelp()
    elif opt == '--api':
        apiFile = arg
        if (policyFile or keyFile or newOrgID):
            print("--api must be run alone")
            print("Must specify exactly one of --setOrgID --api --policy --key")
            printhelp()
    elif opt == '--policy':
        policyFile = arg
        if (apiFile or keyFile or newOrgID):
            print("--policy must be run alone")
            print("Must specify exactly one of --setOrgID --api --policy --key")
            printhelp()
    elif opt == '--key':
        keyFile = arg
        if (policyFile or apiFile or newOrgID):
            print("--key must be run alone")
            print("Must specify exactly one of --setOrgID --api --policy --key")
            printhelp()
    elif opt == '--mongo':
        mongoConnectionString = arg
    elif opt == '--redis':
        redisIPandPort = arg
        redisHost,redisPort = arg.split(':')
    elif opt == '--database':
        mongoDatabase = arg
    elif opt == '--analytics':
        updateAnalytics = True
    elif opt == '--policiesApis':
        updateAPIsPolicies = True

if ((newOrgID or apiFile or policyFile) and not mongoConnectionString):
    print("Must specify --mongo when using --setOrgID or --api or --policy")
    printhelp()
if (keyFile and not (redisHost and redisPort)):
    print("Must specify --redis when using --key")
    printhelp()
if not (newOrgID or apiFile or policyFile or keyFile):
    print("Must specify exactly one of --setOrgID --api --policy --key")
    printhelp()
if (updateAnalytics or updateAPIsPolicies) and not newOrgID:
    print("Must provide a new organisation id if updating analytics or APIs and policies")
    printhelp()

if mongoConnectionString:
    # we're doing something with mongo
    mongoClient = pymongo.MongoClient(mongoConnectionString)
    if mongoDatabase in mongoClient.list_database_names():
        tykDB = mongoClient[mongoDatabase]
        collections = tykDB.list_collection_names()
        if newOrgID:    # Update org and users to new orgid
            if not "tyk_organisations" in collections:
                print(f"'tyk_organisations' not found in '{mongoDatabase}' in {mongoConnectionString}")
                sys.exit(1)
            if not "tyk_analytics_users" in collections:
                print(f"'tyk_analytics_users' not found in '{mongoDatabase}' in {mongoConnectionString}")
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
            oldOrgIDstr = str(org["_id"])

            # create a copy of the existing org, but with the new orgid
            print(f"Copying Org {oldOrgIDstr} to {newOrgID}")
            org["_id"] = ObjectId(newOrgID)
            tyk_organisations.insert_one(org)

            # Delete the old organisation entry
            print(f"Removing old Org {oldOrgIDstr}")
            tyk_organisations.delete_one({"_id": oldOrgID})

            # update the users to the new orgid
            print(f"Migrating users to {newOrgID}")
            tyk_analytics_users = tykDB["tyk_analytics_users"]
            oldOrgUsersQuery = { "orgid": f"{oldOrgIDstr}" }
            users = tyk_analytics_users.find(oldOrgUsersQuery)
            for user in users:
                print(f"Found user {user['emailaddress']} in org {oldOrgIDstr}. You will need to reset their access key")
            tyk_analytics_users.update_many(oldOrgUsersQuery, { "$set": { "orgid": newOrgID } })
            if updateAnalytics:
                # Analytics records also carry the orgid in an "org-<orgid>" tag, so update pipelines (MongoDB 4.2+) are used to rewrite that too
                oldOrgTag = f"org-{oldOrgIDstr}"
                newOrgTag = f"org-{newOrgID}"
                # raw records: tags is an array of strings
                rawAnalyticsUpdate = [ { "$set": {
                    "orgid": newOrgID,
                    "tags": { "$cond": [ { "$isArray": "$tags" },
                        { "$map": { "input": "$tags", "as": "t", "in": { "$cond": [ { "$eq": [ "$$t", oldOrgTag ] }, newOrgTag, "$$t" ] } } },
                        "$tags" ] } } } ]
                # aggregate records: tags is a map keyed by tag (with identifier and humanidentifier set to the tag)
                # and lists.tags is an array of the same objects
                aggregateAnalyticsUpdate = [ { "$set": {
                    "orgid": newOrgID,
                    "tags": { "$cond": [ { "$eq": [ { "$type": "$tags" }, "object" ] },
                        { "$arrayToObject": { "$map": { "input": { "$objectToArray": "$tags" }, "as": "t", "in": { "$cond": [ { "$eq": [ "$$t.k", oldOrgTag ] },
                            { "k": newOrgTag, "v": { "$mergeObjects": [ "$$t.v", { "identifier": newOrgTag, "humanidentifier": newOrgTag } ] } },
                            "$$t" ] } } } },
                        "$tags" ] },
                    "lists.tags": { "$cond": [ { "$isArray": "$lists.tags" },
                        { "$map": { "input": "$lists.tags", "as": "t", "in": { "$cond": [ { "$eq": [ "$$t.identifier", oldOrgTag ] },
                            { "$mergeObjects": [ "$$t", { "identifier": newOrgTag, "humanidentifier": newOrgTag } ] },
                            "$$t" ] } } },
                        "$lists.tags" ] } } } ]
                analyticsCollections = {
                    "tyk_analytics": rawAnalyticsUpdate,
                    f"z_tyk_analyticz_{oldOrgIDstr}": rawAnalyticsUpdate,
                    "tyk_analytics_aggregates": aggregateAnalyticsUpdate,
                    f"z_tyk_analyticz_aggregate_{oldOrgIDstr}": aggregateAnalyticsUpdate }
                for analyticsCollection, analyticsUpdate in analyticsCollections.items():
                    if analyticsCollection in collections:
                        print(f"Updating {analyticsCollection} with {newOrgID}")
                        result = tykDB[analyticsCollection].update_many(oldOrgUsersQuery, analyticsUpdate)
                        print(f"    {result.modified_count} records updated")
                for analyticsCollection in [ f"z_tyk_analyticz_{oldOrgIDstr}", f"z_tyk_analyticz_aggregate_{oldOrgIDstr}" ]:
                    if analyticsCollection in collections:
                        print(f"Renaming collection {analyticsCollection} to {analyticsCollection.replace(oldOrgIDstr, newOrgID)}")
                        tykDB[analyticsCollection].rename(analyticsCollection.replace(oldOrgIDstr, newOrgID))
            if updateAPIsPolicies:
                oldOrgUsersQuery = { "org_id": f"{oldOrgIDstr}" }
                for collection in [ "tyk_apis", "tyk_policies"]:
                    if collection in collections:
                        print(f"Updating org_id in {collection}")
                        tykDB[collection].update_many(oldOrgUsersQuery, { "$set": { "org_id": newOrgID } })
                # OAS APIs also hold the orgid inside the OAS document
                if "tyk_apis" in collections:
                    oasOrgIDField = "oas_doc.x-tyk-api-gateway.info.orgId"
                    print(f"Updating {oasOrgIDField} in tyk_apis")
                    tykDB["tyk_apis"].update_many({ oasOrgIDField: oldOrgIDstr }, { "$set": { oasOrgIDField: newOrgID } })
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
        print(f"'{mongoDatabase}' DB not found in {mongoConnectionString}")
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
