# A module to speed up writing scripts to do stuff with the tyk dashboard
# This is not supported by anyone at any level but is just my efforts to make my life easier
# USE AT YOUR OWN RISK

import json
import requests
import sys

class dashboard:
    def __init__(self, URL, authKey, adminSecret = "N/A" , description = "N/A"):
        self.URL = URL.strip('/')       # The dashboard URL
        self.authKey = authKey          # User key to authenticate API calls
        self.description = description  # description of this dashboard
        self.adminSecret = adminSecret  # The admin secret for the admin API (admin_secret in tyk_analytics.conf, AdminSecret in tyk.conf)

    def __str__(self):
        return f"Dashboard URL: {self.URL}, Auth token: {self.authkey}, Admin Secret: {self.adminSecret}, Description: {self.description}"

    def url(self):
        return self.URL

    def authkey(self):
        return self.authkey

    def setAuthkey(self, authkey):
        self.authkey = authkey
        return self.authkey

    def description(self):
        return self.description

    def adminSecret(self):
        return self.adminSecret

    def setAdminSecret(self, adminSecret):
        self.adminSecret = adminSecret
        return adminSecret


    # API functions
    def getAPI(self, APIid):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/apis/{APIid}', headers=headers)
        if resp.status_code != 200:
            print(resp.json())
        return resp

    def getAPIs(self):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/apis/?p=-1', headers=headers)
        if resp.status_code != 200:
            print(resp.json())
        return resp

    def createAPI(self, APIdefinition):
        if type(APIdefinition) is dict:
            APIdefinition = json.dumps(APIdefinition)
        headers = {'Authorization' : self.authKey}
        headers["Content-Type"] = "application/json"
        resp = requests.post(f'{self.URL}/api/apis', data=APIdefinition, headers=headers)
        if resp.status_code != 200:
            print(resp.json())
        return resp

    def createAPIs(self, APIdefinition, numberToCreate):
        apis = self.getAPIs().json()
        # create a dictionary of all API names
        APIName = APIdefinition["api_definition"]["name"]
        allnames = dict()
        for api in apis['apis']:
            allnames[api["api_definition"]["name"]] = 1
        i = 1
        numberCreated = 0
        while numberCreated < numberToCreate:
            # work out the next free name (format is name-i)
            while APIName+str(i) in allnames:
                i += 1
            newname=APIName+str(i)
            allnames[newname] = 1
            APIdefinition["api_definition"]["name"] = newname
            APIdefinition["api_definition"]["slug"] = newname
            APIdefinition["api_definition"]["proxy"]["listen_path"] = '/'+newname+'/'
            print(f'Adding API {APIdefinition["api_definition"]["name"]}, {APIdefinition["api_definition"]["proxy"]["listen_path"]}')
            resp = self.createAPI(APIdefinition)
            if resp.status_code == 200:
                print(json.dumps(resp.json()))
                numberCreated += 1
        return numberCreated

    def updateAPI(self, APIdefinition, APIid):
        if type(APIdefinition) is dict:
            APIdefinition = json.dumps(APIdefinition)
        headers = {'Authorization' : self.authKey}
        headers["Content-Type"] = "application/json"
        resp = requests.put(f'{self.URL}/api/apis/{APIid}', data=APIdefinition, headers=headers)
        if resp.status_code != 200:
            print(resp.json())
        return resp

    def deleteAPI(self, APIid):
        headers = {'Authorization' : self.authKey}
        resp = requests.delete(f'{self.URL}/api/apis/{APIid}', headers=headers)
        if resp.status_code != 200:
            print(resp.json())
        return resp

    def deleteAllAPIs(self):
        allDeleted = True
        apis = self.getAPIs().json()
        for api in apis['apis']:
            print(f'Deleting API: {api["api_definition"]["name"]}: {api["api_definition"]["api_id"]}')
            resp = self.deleteAPI(api["api_definition"]["api_id"])
            print(resp.json())
            if resp.status_code != 200:
                allDeleted = False
        return allDeleted


    # Policy function
    def getPolicy(self, policyID):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/portal/policies/{policyID}', headers=headers)
        if resp.status_code != 200:
            print(resp.text)
        return resp

    def getPolicies(self):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/portal/policies/?p=-1', headers=headers)
        if resp.status_code != 200:
            print(resp.json())
        return resp

    def createPolicy(self, policyDefinition):
        if type(policyDefinition) is dict:
            policyDefinition = json.dumps(policyDefinition)
        headers = {'Authorization' : self.authKey}
        headers["Content-Type"] = "application/json"
        resp = requests.post(f'{self.URL}/api/portal/policies', data=policyDefinition, headers=headers)
        if resp.status_code != 200:
            print(resp.json())
        return resp

    def createPolicies(self, policyDefinition, APIid, numberToCreate):
        policies = self.getPolicies().json()
        # create a dictionary of all policy names
        PolicyName = policyDefinition["name"]
        allnames = dict()
        for policy in policies['Data']:
            allnames[policy["name"]] = 1
        i = 1
        numberCreated = 0
        while numberCreated < numberToCreate:
            # work out the next free name (format is name-i)
            while PolicyName+str(i) in allnames:
                i += 1
            newname=PolicyName+str(i)
            allnames[newname] = 1
            policyDefinition["name"]=PolicyName+str(i)
            policyDefinition["access_rights_array"] = json.loads('[{ "api_id": "' + APIid + '", "versions": [ "Default" ], "allowed_urls": [], "restricted_types": [], "limit": null, "allowance_scope": "" }]')
            print(f'Creating policy: {policyDefinition["name"]}')
            resp = self.createPolicy(json.dumps(policyDefinition))
            if resp.status_code == 200:
                print(json.dumps(resp.json()))
                numberCreated += 1
        return numberCreated

    def updatePolicy(self, policyDefinition, policyID):
        if type(policyDefinition) is dict:
            policyDefinition = json.dumps(policyDefinition)
        headers = {'Authorization' : self.authKey}
        headers["Content-Type"] = "application/json"
        resp = requests.put(f'{self.URL}/api/portal/policies/{policyID}', data=policyDefinition, headers=headers)
        if resp.status_code != 200:
            print(resp.json())
        return resp

    def deletePolicy(self, policyID):
        headers = {'Authorization' : self.authKey}
        resp = requests.delete(f'{self.URL}/api/portal/policies/{policyID}', headers=headers)
        if resp.status_code != 200:
            print(resp.text)
        return resp

    def deleteAllPolicies(self):
        allDeleted = True
        policies = self.getPolicies().json()
        for policy in policies['Data']:
            print(f'Deleting policy: {policy["_id"]}')
            resp = self.deletePolicy(policy["_id"])
            print(resp.json())
            if resp.status_code != 200:
                allDeleted = False
        return allDeleted


    # Key functions
    def getKeys(self):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/apis/-/keys?p=-1', headers=headers)
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
        if type(keyDefinition) is dict:
            keyDefinition = json.dumps(keyDefinition)
        headers = {'Authorization' : self.authKey}
        headers["Content-Type"] = "application/json"
        resp = requests.post(f'{self.URL}/api/keys', data=keyDefinition, headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def updateKey(self, keyDefinition, KeyID):
        if type(keyDefinition) is dict:
            keyDefinition = json.dumps(keyDefinition)
        headers = {'Authorization' : self.authKey}
        headers["Content-Type"] = "application/json"
        resp = requests.put(f'{self.URL}/api/apis/-/keys/{KeyID}', data=keyDefinition, headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def deleteKey(self, keyID):
        headers = {'Authorization' : self.authKey}
        headers["Content-Type"] = "application/json"
        # not sure where ?auto_guess=true comes from but it works when keys are encrypted
        resp = requests.delete(f'{self.URL}/api/keys/{keyID}/?auto_guess=true', headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def deleteAllKeys(self):
        keys = self.getKeys()
        for keyID in keys['data']['keys']:
            print(f'Deleting key: {keyID}')
            resp = self.deleteKey(keyID)
            print(json.dumps(resp))


    # Portal Catalogue functions
    def getCatalogue(self):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/portal/catalogue', headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def updateCatalogue(self, catalogue):
        if type(catalogue) is dict:
            catalogue = json.dumps(catalogue)
        headers = {'Authorization' : self.authKey}
        resp = requests.put(f'{self.URL}/api/portal/catalogue', data=catalogue, headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)


    # Organisation functions
    def getOrganisations(self):
        headers = {'admin-auth': self.adminSecret}
        headers["Content-Type"] = "application/json"
        resp = requests.get(f'{self.URL}/admin/organisations?p=-1', headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def getOrganisation(self, orgID):
        headers = {'admin-auth': self.adminSecret}
        headers["Content-Type"] = "application/json"
        resp = requests.get(f'{self.URL}/admin/organisations/{orgID}', headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def createOrganisation(self, orgDefinition):
        if type(orgDefinition) is dict:
            orgDefinition = json.dumps(orgDefinition)
        headers = {'admin-auth': self.adminSecret}
        headers["Content-Type"] = "application/json"
        resp = requests.post(f'{self.URL}/admin/organisations', data=orgDefinition, headers=headers)
        if resp.status_code != 200:
            print(resp.text)
            sys.exit(1)
        return json.loads(resp.text)

    def createOrganisations(self, orgDefinition, numberToCreate):
        orgs = self.getOrganisations()
        # create a dictionary of all policy names
        orgSlug = orgDefinition["owner_slug"]
        orgOwner = orgDefinition["owner_name"]
        allSlugs = dict()
        for org in orgs['organisations']:
            allSlugs[org["owner_slug"]] = 1
        i = 1
        numberCreated = 0
        while numberCreated < numberToCreate:
            # work out the next free name (format is name-i)
            while orgSlug+str(i) in allSlugs:
                i += 1
            newSlug=orgSlug+str(i)
            allSlugs[newSlug] = 1
            orgDefinition["owner_name"]=orgOwner+str(i)
            orgDefinition["owner_slug"]=orgSlug+str(i)
            print(f'Creating Organisation: {orgDefinition["owner_slug"]}')
            resp = self.createOrganisation(json.dumps(orgDefinition))
            print(json.dumps(resp))
            numberCreated += 1
        if numberCreated == numberToCreate:
            return True
        else:
            return False


    # Users
    def createAdminUser(self, userEmail, userPass, orgID):
        headers = {'admin-auth': self.adminSecret}
        headers["Content-Type"] = "application/json"
        userDefinition = {
                "first_name": "Tyk",
                "last_name": "Admin",
                "email_address": userEmail,
                "password": userPass,
                "active": True,
                "org_id": orgID,
                "user_permissions": { "ResetPassword" : "admin", "IsAdmin": "admin" }}
        createResp = requests.post(f'{self.URL}/admin/users', data=json.dumps(userDefinition), headers=headers)
        if createResp.status_code != 200:
            print(createResp.text)
            return json.loads(createResp.text)
        # need to send a reset to for the user
        userdata = json.loads(createResp.text)
        headers = {'Authorization' : userdata["Meta"]["access_key"]}
        headers["Content-Type"] = "application/json"
        resetResp = requests.post(f'{self.URL}/api/users/{userdata["Meta"]["id"]}/actions/reset', data='{"new_password":"'+userPass+'"}', headers=headers)
        if resetResp.status_code != 200:
            print(resetResp.text)
        return json.loads(createResp.text)
