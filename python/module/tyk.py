# A module to speed up writing scripts to do stuff with the tyk dashboard
# This is not supported by anyone at any level but is just my efforts to make my life easier
# USE AT YOUR OWN RISK

import json
import requests
import sys
import time


###################### DASHBOARD CLASS ######################
class dashboard:
    def __init__(self, URL, authKey, adminSecret = 'N/A' , description = 'N/A'):
        self.URL = URL.strip('/')       # The dashboard URL
        self.authKey = authKey          # User key to authenticate API calls
        self.description = description  # description of this dashboard
        self.adminSecret = adminSecret  # The admin secret for the admin API (admin_secret in tyk_analytics.conf, AdminSecret in tyk.conf)

    def __str__(self):
        return f'Dashboard URL: {self.URL}, Auth token: {self.authkey}, Admin Secret: {self.adminSecret}, Description: {self.description}'

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
        return resp

    def getAPIs(self):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/apis/?p=-1', headers=headers)
        return resp

    def createAPI(self, APIdefinition):
        if type(APIdefinition) is dict:
            APIdefinition = json.dumps(APIdefinition)
        headers = {'Authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        resp = requests.post(f'{self.URL}/api/apis', data=APIdefinition, headers=headers)
        return resp

    def createAPIs(self, APIdefinition, numberToCreate):
        apis = self.getAPIs().json()
        # create a dictionary of all API names
        APIName = APIdefinition['api_definition']['name']
        allnames = dict()
        for api in apis['apis']:
            allnames[api['api_definition']['name']] = 1
        i = 1
        numberCreated = 0
        while numberCreated < numberToCreate:
            # work out the next free name (format is name-i)
            while APIName+str(i) in allnames:
                i += 1
            newname=APIName+str(i)
            allnames[newname] = 1
            APIdefinition['api_definition']['name'] = newname
            APIdefinition['api_definition']['slug'] = newname
            APIdefinition['api_definition']['proxy']['listen_path'] = '/'+newname+'/'
            print(f'Adding API {APIdefinition["api_definition"]["name"]}, {APIdefinition["api_definition"]["proxy"]["listen_path"]}')
            resp = self.createAPI(APIdefinition)
            print(resp.json())
            # if a call fails, stop and return the number of successes
            if resp.status_code != 200:
                break
            numberCreated += 1
        return numberCreated

    def updateAPI(self, APIdefinition, APIid):
        if type(APIdefinition) is dict:
            APIdefinition = json.dumps(APIdefinition)
        headers = {'Authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        resp = requests.put(f'{self.URL}/api/apis/{APIid}', data=APIdefinition, headers=headers)
        return resp

    def deleteAPI(self, APIid):
        headers = {'Authorization' : self.authKey}
        resp = requests.delete(f'{self.URL}/api/apis/{APIid}', headers=headers)
        return resp

    def deleteAllAPIs(self):
        allDeleted = True
        apis = self.getAPIs().json()
        for api in apis['apis']:
            print(f'Deleting API: {api["api_definition"]["name"]}: {api["api_definition"]["api_id"]}')
            resp = self.deleteAPI(api['api_definition']['api_id'])
            print(resp.json())
            if resp.status_code != 200:
                allDeleted = False
        return allDeleted


    # Policy function
    def getPolicy(self, policyID):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/portal/policies/{policyID}', headers=headers)
        return resp

    def getPolicies(self):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/portal/policies/?p=-1', headers=headers)
        return resp

    def createPolicy(self, policyDefinition):
        if type(policyDefinition) is dict:
            policyDefinition = json.dumps(policyDefinition)
        headers = {'Authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        resp = requests.post(f'{self.URL}/api/portal/policies', data=policyDefinition, headers=headers)
        return resp

    def createPolicies(self, policyDefinition, APIid, numberToCreate):
        policies = self.getPolicies().json()
        # create a dictionary of all policy names
        PolicyName = policyDefinition['name']
        allnames = dict()
        for policy in policies['Data']:
            allnames[policy['name']] = 1
        i = 1
        numberCreated = 0
        while numberCreated < numberToCreate:
            # work out the next free name (format is name-i)
            while PolicyName+str(i) in allnames:
                i += 1
            newname=PolicyName+str(i)
            allnames[newname] = 1
            policyDefinition['name']=PolicyName+str(i)
            policyDefinition['access_rights_array'] = json.loads('[{ "api_id": "' + APIid + '", "versions": [ "Default" ], "allowed_urls": [], "restricted_types": [], "limit": null, "allowance_scope": "" }]')
            print(f'Creating policy: {policyDefinition["name"]}')
            resp = self.createPolicy(json.dumps(policyDefinition))
            print(resp.json())
            # if a call fails, stop and return the number of successes
            if resp.status_code != 200:
                break
            numberCreated += 1
        return numberCreated

    def updatePolicy(self, policyDefinition, policyID):
        if type(policyDefinition) is dict:
            policyDefinition = json.dumps(policyDefinition)
        headers = {'Authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        resp = requests.put(f'{self.URL}/api/portal/policies/{policyID}', data=policyDefinition, headers=headers)
        return resp

    def deletePolicy(self, policyID):
        headers = {'Authorization' : self.authKey}
        resp = requests.delete(f'{self.URL}/api/portal/policies/{policyID}', headers=headers)
        return resp

    def deleteAllPolicies(self):
        allDeleted = True
        policies = self.getPolicies().json()
        for policy in policies['Data']:
            print(f'Deleting policy: {policy["_id"]}')
            resp = self.deletePolicy(policy['_id'])
            print(resp.json())
            if resp.status_code != 200:
                allDeleted = False
        return allDeleted


    # Key functions

    # Two options for getting all the keys
    # /api/apis/keys/?p=-1 which just lists the key ids
    # /api/keys/detailed/?p=-1 which dump the details of all the keys
    def getKeys(self):
        headers = {'Authorization' : self.authKey}
        #resp = requests.get(f'{self.URL}/api/apis/-/keys?p=-1', headers=headers)
        resp = requests.get(f'{self.URL}/api/keys/detailed/?p=-1', headers=headers)
        return resp

    def getKey(self, keyID):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/apis/-/keys/{keyID}', headers=headers)
        return resp

    def createKey(self, keyDefinition):
        if type(keyDefinition) is dict:
            keyDefinition = json.dumps(keyDefinition)
        headers = {'Authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        resp = requests.post(f'{self.URL}/api/keys', data=keyDefinition, headers=headers)
        return resp

    def updateKey(self, keyDefinition, KeyID):
        if type(keyDefinition) is dict:
            keyDefinition = json.dumps(keyDefinition)
        headers = {'Authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        resp = requests.put(f'{self.URL}/api/apis/-/keys/{KeyID}', data=keyDefinition, headers=headers)
        return resp

    def deleteKey(self, keyID):
        headers = {'Authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        # not sure where ?auto_guess=true comes from but it works when keys are encrypted
        resp = requests.delete(f'{self.URL}/api/keys/{keyID}/?auto_guess=true', headers=headers)
        return resp

    def deleteAllKeys(self):
        allDeleted = True
        keys = self.getKeys().json()
        for key in keys['keys']:
            keyID = keyID['key_id']
            print(f'Deleting key: {keyID}')
            resp = self.deleteKey(keyID)
            print(resp.json())
            if resp.status_code != 200:
                allDeleted = False
        return allDeleted


    # Portal Catalogue functions
    def getCatalogue(self):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/portal/catalogue', headers=headers)
        return resp

    def updateCatalogue(self, catalogue):
        if type(catalogue) is dict:
            catalogue = json.dumps(catalogue)
        headers = {'Authorization' : self.authKey}
        resp = requests.put(f'{self.URL}/api/portal/catalogue', data=catalogue, headers=headers)
        return resp


    # Organisation functions
    def getOrganisations(self):
        headers = {'admin-auth': self.adminSecret}
        headers['Content-Type'] = 'application/json'
        resp = requests.get(f'{self.URL}/admin/organisations?p=-1', headers=headers)
        return resp

    def getOrganisation(self, orgID):
        headers = {'admin-auth': self.adminSecret}
        headers['Content-Type'] = 'application/json'
        resp = requests.get(f'{self.URL}/admin/organisations/{orgID}', headers=headers)
        return resp

    def createOrganisation(self, orgDefinition):
        if type(orgDefinition) is dict:
            orgDefinition = json.dumps(orgDefinition)
        headers = {'admin-auth': self.adminSecret}
        headers['Content-Type'] = 'application/json'
        resp = requests.post(f'{self.URL}/admin/organisations', data=orgDefinition, headers=headers)
        return resp

    def createOrganisations(self, orgDefinition, numberToCreate):
        orgs = self.getOrganisations().json()
        # create a dictionary of all policy names
        orgSlug = orgDefinition['owner_slug']
        orgOwner = orgDefinition['owner_name']
        allSlugs = dict()
        for org in orgs['organisations']:
            allSlugs[org['owner_slug']] = 1
        i = 1
        numberCreated = 0
        while numberCreated < numberToCreate:
            # work out the next free name (format is name-i)
            while orgSlug+str(i) in allSlugs:
                i += 1
            newSlug=orgSlug+str(i)
            allSlugs[newSlug] = 1
            orgDefinition['owner_name']=orgOwner+str(i)
            orgDefinition['owner_slug']=orgSlug+str(i)
            print(f'Creating Organisation: {orgDefinition["owner_slug"]}')
            resp = self.createOrganisation(json.dumps(orgDefinition))
            print(resp.json())
            # if a call fails, stop and return the number of successes
            if resp.status_code != 200:
                break
            numberCreated += 1
        return numberCreated


    # Users
    def createAdminUser(self, userEmail, userPass, orgID):
        headers = {'admin-auth': self.adminSecret}
        headers['Content-Type'] = 'application/json'
        userDefinition = {
                'first_name': 'Tyk',
                'last_name': 'Admin',
                'email_address': userEmail,
                'password': userPass,
                'active': True,
                'org_id': orgID,
                'user_permissions': { 'ResetPassword' : 'admin', 'IsAdmin': 'admin' }}
        createResp = requests.post(f'{self.URL}/admin/users', data=json.dumps(userDefinition), headers=headers)
        if createResp.status_code != 200:
            return createResp
        # need to send a reset to for the user
        userdata = createResp.json()
        headers = {'Authorization' : userdata['Meta']['access_key']}
        headers['Content-Type'] = 'application/json'
        resetResp = requests.post(f'{self.URL}/api/users/{userdata["Meta"]["id"]}/actions/reset', data='{"new_password":"'+userPass+'"}', headers=headers)
        return createResp


    # Analytics
    # get the usage of all APIs for a period (defaults to today)
    def getAPIUsage(self, startday = time.strftime('%d'), startmonth = time.strftime('%m'), startyear = time.strftime('%Y'), endday = time.strftime('%d'), endmonth = time.strftime('%m'), endyear = time.strftime('%Y')):
        if type(startday) == 'int':
            startday = str(startday)
        if type(startmonth) == 'int':
            startmonth = str(startmonth)
        if type(startyear) == 'int':
            startyear = str(startyear)
        if type(endday) == 'int':
            endday = str(endday)
        if type(endmonth) == 'int':
            endmonth = str(endmonth)
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/usage/apis/{startday}/{startmonth}/{startyear}/{endday}/{endmonth}/{endyear}?by=Hits&sort=1&p=-1', headers=headers)
        return resp

    # Certificates
    def getCerts(self):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/certs?p=-1', headers=headers)
        return resp

    def getCert(self, certid):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/certs/{certid}', headers=headers)
        return resp

    def getCertsDetails(self):
        headers = {'Authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/api/certs?p=-1&mode=detailed', headers=headers)
        return resp

    def createCert(self, certFile):
        headers = {'Authorization' : self.authKey}
        files={'data': open(certFile,'r')}
        resp = requests.post(f'{self.URL}/api/certs', files=files, headers=headers, verify=False)
        return resp

    def deleteCert(self, certid):
        headers = {'Authorization' : self.authKey}
        resp = requests.delete(f'{self.URL}/api/certs/{certid}', headers=headers)
        return resp 



###################### GATEWAY CLASS ######################
class gateway:
    def __init__(self, URL, authKey, description = 'N/A'):
        self.URL = URL.strip('/')       # The gateway URL
        self.authKey = authKey          # User key to authenticate API calls ('Secret' from tyk.conf)
        self.description = description  # description of this gateway

    def __str__(self):
        return f'Gateway URL: {self.URL}, Auth token: {self.authkey}, Description: {self.description}'

    def url(self):
        return self.URL

    def authkey(self):
        return self.authkey

    def setAuthkey(self, authkey):
        self.authkey = authkey
        return self.authkey

    def description(self):
        return self.description

    # API functions
    def getAPI(self, APIid):
        headers = {'x-tyk-authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/tyk/apis/{APIid}', headers=headers)
        return resp

    def getAPIs(self):
        headers = {'x-tyk-authorization' : self.authKey}
        resp = requests.get(f'{self.URL}/tyk/apis', headers=headers)
        return resp

