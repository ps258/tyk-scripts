# A mmodule to speed up writing scripts to do stuff with the tyk dashboard
# This is not supported by anyone at any level but is just my efforts to make my life easier
# USE AT YOUR OWN RISK

import json
import requests
import sys

class dashboard:
    def __init__(self, URL, authKey, description = "N/A"):
        self.URL = URL.strip('/')
        self.authKey = authKey
        self.description = description

    def __str__(self):
        return f"Dashboard URL: {self.URL}, Auth token: {self.authkey}, Description: {self.description}"

    def url(self):
        return self.URL

    def authkey(self):
        return self.authkey

    def description(self):
        return self.description

    # API functions
    def getAPIs(self):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/apis/?p=-1', headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def getAPI(self, APIid):
        resp = requests.get(f'{self.URL}/api/apis/{APIid}', headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def createAPI(self, APIdefinition):
        headers = {'Authorization' : self.authKey}
        headers["Content-Type"] = "application/json"
        resp = requests.post(f'{self.URL}/api/apis', data=APIdefinition, headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def createAPIs(self, APIdefinition, numberToCreate):
        apis = self.getAPIs()
        # create a dictionary of all API names
        APIName = APIdefinition["api_definition"]["name"]
        allnames = dict()
        for api in apis['apis']:
            name = api["api_definition"]["name"]
            allnames[name] = 1
        i = 1
        while numberCreated < numberToCreate:
            # work out the next free name (format is name-i)
            while APIName+str(i) in allnames:
                i += 1
            newname=APIName+str(i)
            allnames[newname] = 1
            APIdefinition["api_definition"]["name"] = newname
            APIdefinition["api_definition"]["slug"] = newname
            APIjson["api_definition"]["proxy"]["listen_path"] = '/'+newname+'/'
            print(f'Adding API {APIjson["api_definition"]["name"]}, {APIjson["api_definition"]["proxy"]["listen_path"]}')
            resp = self.createAPI(json.dumps(APIjson))
            print(json.dumps(resp))
            numberCreated += 1

    def updateAPI(self, APIid, APIdefinition):
        headers = {'Authorization' : self.authKey}
        headers["Content-Type"] = "application/json"
        resp = requests.put(f'{self.URL}/api/apis/{APIid}', data=APIdefinition, headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def deleteAPI(self, APIid):
        headers = {'Authorization' : self.authKey}
        resp = requests.delete(f'{self.URL}/api/apis/{APIid}', headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    # Policy function
    def getPolicies(self):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/portal/policies/?p=-1', headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def getPolicy(self, policyID):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/portal/policies/{policyID}', headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def createPolicy(self, policyDefinition):
        headers = {'Authorization' : self.authKey}
        headers["Content-Type"] = "application/json"
        resp = requests.post(f'{self.URL}/api/portal/policies', data=policyDefinition, headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def createPolicies(self, policyDefinition, APIid, numberToCreate):
        policies = self.getPoliciesi()
        # create a dictionary of all policy
        PolicyName = policyDefinition["name"]
        allnames = dict()
        for policy in policies['data']:
            allnames[policy["name"]] = 1
        i = 1
        while numberCreated < numberToCreate:
            # work out the next free name (format is name-i)
            while PolicyName+str(i) in allnames:
                i += 1
            newname=PolicyName+str(i)
            allnames[newname] = 1
            PolicyJSON["name"]=PolicyName+str(i)
            PolicyJSON["access_rights_array"] = json.loads('[{ "api_id": "' + Apiid + '", "versions": [ "Default" ], "allowed_urls": [], "restricted_types": [], "limit": null, "allowance_scope": "" }]')
            resp = self.createAPI(json.dumps(PolicyJSON))
            print(json.dumps(resp))
            numberCreated += 1

    def updatePolicy(self, policyID, policyDefinition):
        headers = {'Authorization' : self.authKey}
        headers["Content-Type"] = "application/json"
        resp = requests.put(f'{self.URL}/api/portal/policies/{policyID}', data=policyDefinition, headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def deletePolicy(self, policyID):
        headers = {'Authorization' : self.authKey}
        headers["Content-Type"] = "application/json"
        resp = requests.delete(f'{self.URL}/api/portal/policies/{policyID}', headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    # Key functions
    def getKeys(self):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/apis/-/keys', headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def getKey(self, keyID):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/apis/-/keys/{keyID}', headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def createKey(self, keyDefinition):
        headers = {'Authorization' : self.authKey}
        headers["Content-Type"] = "application/json"
        resp = requests.post(f'{self.URL}/api/keys', data=keyDefinition, headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    # Portal Catalogue functions
    def getCatalogue(self):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/portal/catalogue', headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def updateCatalogue(self, catalogue):
        headers = {'Authorization' : self.authKey}
        resp = requests.put(f'{self.URL}/api/portal/catalogue', data=catalogue, headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)
