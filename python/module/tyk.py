# A module to speed up writing scripts to do stuff with the tyk dashboard
# This is not supported by anyone at any level but is just my efforts to make my life easier
# USE AT YOUR OWN RISK

import json
import requests
import time

# Suppress the warnings from urllib3 when using a self signed certs
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

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


    # Dashboard API functions
    def getAPI(self, APIid):
        headers = {'Authorization' : self.authKey}
        return requests.get(f'{self.URL}/api/apis/{APIid}', headers=headers, verify=False)

    def getAPIs(self):
        headers = {'Authorization' : self.authKey}
        response = requests.get(f'{self.URL}/api/apis/?p=-1', headers=headers, verify=False)
        body_json = response.json()
        # pull the APIs out of the 'apis' array so that the format is the same as it is from the gateway
        # also extract the API defintions out of 'api_definition' and add it to the array
        apis = []
        for api in body_json['apis']:
            apis.append(api['api_definition'])
        response._content = json.dumps(apis).encode()
        return response

    def createAPI(self, APIdefinition):
        if type(APIdefinition) is dict:
            APIdefinition = json.dumps(APIdefinition)
        headers = {'Authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        return requests.post(f'{self.URL}/api/apis', data=APIdefinition, headers=headers, verify=False)

    def createAPIs(self, APIdefinition, numberToCreate):
        apis = self.getAPIs().json()
        # create a dictionary of all API names
        APIName = APIdefinition['api_definition']['name']
        allnames = dict()
        for api in apis:
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
            response = self.createAPI(APIdefinition)
            print(response.json())
            # if a call fails, stop and return the number of successes
            if response.status_code != 200:
                break
            numberCreated += 1
        return numberCreated

    def updateAPI(self, APIdefinition, APIid):
        if type(APIdefinition) is dict:
            APIdefinition = json.dumps(APIdefinition)
        headers = {'Authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        return requests.put(f'{self.URL}/api/apis/{APIid}', data=APIdefinition, headers=headers, verify=False)

    def deleteAPI(self, APIid):
        headers = {'Authorization' : self.authKey}
        return requests.delete(f'{self.URL}/api/apis/{APIid}', headers=headers, verify=False)

    def deleteAllAPIs(self):
        allDeleted = True
        apis = self.getAPIs().json()
        for api in apis['apis']:
            print(f'Deleting API: {api["api_definition"]["name"]}: {api["api_definition"]["api_id"]}')
            response = self.deleteAPI(api['api_definition']['api_id'])
            print(response.json())
            if response.status_code != 200:
                allDeleted = False
        return allDeleted


    # Dashboard Policy functions
    def getPolicy(self, policyID):
        headers = {'Authorization' : self.authKey}
        return requests.get(f'{self.URL}/api/portal/policies/{policyID}', headers=headers, verify=False)

    def getPolicies(self):
        headers = {'Authorization' : self.authKey}
        response = requests.get(f'{self.URL}/api/portal/policies/?p=-1', headers=headers, verify=False)
        body_json = response.json()
        # pull the policies out of the 'Data' array so that the format is the same as it is from the gateway
        response._content = json.dumps(body_json['Data']).encode()
        return response

    def createPolicy(self, policyDefinition):
        if type(policyDefinition) is dict:
            policyDefinition = json.dumps(policyDefinition)
        headers = {'Authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        return requests.post(f'{self.URL}/api/portal/policies', data=policyDefinition, headers=headers, verify=False)

    def createPolicies(self, policyDefinition, APIid, numberToCreate):
        policies = self.getPolicies().json()
        # create a dictionary of all policy names
        PolicyName = policyDefinition['name']
        allnames = dict()
        for policy in policies:
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
            response = self.createPolicy(json.dumps(policyDefinition))
            print(response.json())
            # if a call fails, stop and return the number of successes
            if response.status_code != 200:
                break
            numberCreated += 1
        return numberCreated

    def updatePolicy(self, policyDefinition, policyID):
        if type(policyDefinition) is dict:
            policyDefinition = json.dumps(policyDefinition)
        headers = {'Authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        return requests.put(f'{self.URL}/api/portal/policies/{policyID}', data=policyDefinition, headers=headers, verify=False)

    def deletePolicy(self, policyID):
        headers = {'Authorization' : self.authKey}
        return requests.delete(f'{self.URL}/api/portal/policies/{policyID}', headers=headers, verify=False)

    def deleteAllPolicies(self):
        allDeleted = True
        policies = self.getPolicies().json()
        for policy in policies:
            print(f'Deleting policy: {policy["_id"]}')
            response = self.deletePolicy(policy['_id'])
            print(response.json())
            if response.status_code != 200:
                allDeleted = False
        return allDeleted


    # Dashboard Key functions

    # Two options for getting all the keys
    # /api/apis/keys/?p=-1 which just lists the key IDs
    # /api/keys/detailed/?p=-1 which dump the details of all the keys
    def getKeys(self):
        headers = {'Authorization' : self.authKey}
        #return requests.get(f'{self.URL}/api/apis/-/keys?p=-1', headers=headers, verify=False)
        return requests.get(f'{self.URL}/api/keys/detailed/?p=-1', headers=headers, verify=False)

    def getKey(self, keyID):
        headers = {'Authorization' : self.authKey}
        return requests.get(f'{self.URL}/api/apis/-/keys/{keyID}', headers=headers, verify=False)

    def createKey(self, keyDefinition):
        if type(keyDefinition) is dict:
            keyDefinition = json.dumps(keyDefinition)
        headers = {'Authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        return requests.post(f'{self.URL}/api/keys', data=keyDefinition, headers=headers, verify=False)

    def createCustomKey(self, keyDefinition, KeyID):
        if type(keyDefinition) is dict:
            keyDefinition = json.dumps(keyDefinition)
        headers = {'Authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        return requests.post(f'{self.URL}/api/keys/{KeyID}', data=keyDefinition, headers=headers, verify=False)

    def updateKey(self, keyDefinition, KeyID):
        if type(keyDefinition) is dict:
            keyDefinition = json.dumps(keyDefinition)
        headers = {'Authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        #return requests.put(f'{self.URL}/api/apis/-/keys/{KeyID}', data=keyDefinition, headers=headers, verify=False)
        return requests.put(f'{self.URL}/api/keys/{KeyID}', data=keyDefinition, headers=headers, verify=False)

    def deleteKey(self, keyID):
        headers = {'Authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        # not sure where ?auto_guess=true comes from but it works when keys are encrypted
        return requests.delete(f'{self.URL}/api/keys/{keyID}/?auto_guess=true', headers=headers, verify=False)

    def deleteAllKeys(self):
        allDeleted = True
        keys = self.getKeys().json()
        for key in keys['keys']:
            keyID = key['key_id']
            print(f'Deleting key: {keyID}')
            response = self.deleteKey(keyID)
            print(response.json())
            if response.status_code != 200:
                allDeleted = False
        return allDeleted


    # Dashboard Portal Catalogue functions
    def getCatalogue(self):
        headers = {'Authorization' : self.authKey}
        return requests.get(f'{self.URL}/api/portal/catalogue', headers=headers, verify=False)

    def updateCatalogue(self, catalogue):
        if type(catalogue) is dict:
            catalogue = json.dumps(catalogue)
        headers = {'Authorization' : self.authKey}
        return requests.put(f'{self.URL}/api/portal/catalogue', data=catalogue, headers=headers, verify=False)


    # Dashboard Organisation functions
    def getOrganisations(self):
        headers = {'admin-auth': self.adminSecret}
        headers['Content-Type'] = 'application/json'
        return requests.get(f'{self.URL}/admin/organisations?p=-1', headers=headers, verify=False)

    def getOrganisation(self, orgID):
        headers = {'admin-auth': self.adminSecret}
        headers['Content-Type'] = 'application/json'
        return requests.get(f'{self.URL}/admin/organisations/{orgID}', headers=headers, verify=False)

    def createOrganisation(self, orgDefinition):
        if type(orgDefinition) is dict:
            orgDefinition = json.dumps(orgDefinition)
        headers = {'admin-auth': self.adminSecret}
        headers['Content-Type'] = 'application/json'
        return requests.post(f'{self.URL}/admin/organisations', data=orgDefinition, headers=headers, verify=False)

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
            response = self.createOrganisation(json.dumps(orgDefinition))
            print(response.json())
            # if a call fails, stop and return the number of successes
            if response.status_code != 200:
                break
            numberCreated += 1
        return numberCreated


    # Dashboard User functions
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
        createResp = requests.post(f'{self.URL}/admin/users', data=json.dumps(userDefinition), headers=headers, verify=False)
        if createResp.status_code != 200:
            return createResp
        # need to send a reset to for the user
        userdata = createResp.json()
        headers = {'Authorization' : userdata['Meta']['access_key']}
        headers['Content-Type'] = 'application/json'
        resetResp = requests.post(f'{self.URL}/api/users/{userdata["Meta"]["id"]}/actions/reset', data='{"new_password":"'+userPass+'"}', headers=headers, verify=False)
        return createResp


    # Dashboard Analytics functions

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
        return requests.get(f'{self.URL}/api/usage/apis/{startday}/{startmonth}/{startyear}/{endday}/{endmonth}/{endyear}?by=Hits&sort=1&p=-1', headers=headers, verify=False)

    # Dashboard Certificate functions
    def getCerts(self):
        headers = {'Authorization' : self.authKey}
        return requests.get(f'{self.URL}/api/certs?p=-1', headers=headers, verify=False)

    def getCert(self, certid):
        headers = {'Authorization' : self.authKey}
        return requests.get(f'{self.URL}/api/certs/{certid}', headers=headers, verify=False)

    def getCertsDetails(self):
        headers = {'Authorization' : self.authKey}
        return requests.get(f'{self.URL}/api/certs?p=-1&mode=detailed', headers=headers, verify=False)

    def createCert(self, certFile):
        headers = {'Authorization' : self.authKey}
        files={'data': open(certFile,'r')}
        return requests.post(f'{self.URL}/api/certs', files=files, headers=headers, verify=False)

    def deleteCert(self, certid):
        headers = {'Authorization' : self.authKey}
        return requests.delete(f'{self.URL}/api/certs/{certid}', headers=headers, verify=False)

    def deleteAllCerts(self):
        allDeleted = True
        certs = self.getCerts().json()
        print(certs)
        for certid in certs['certs']:
            print(f'Deleting certificate: {certid}')
            response = self.deleteCert(certid)
            print(response.json())
            if response.status_code != 200:
                allDeleted = False
        return allDeleted


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

    # Gateway API functions
    def getAPI(self, APIid):
        headers = {'x-tyk-authorization' : self.authKey}
        return requests.get(f'{self.URL}/tyk/apis/{APIid}', headers=headers, verify=False)

    def getAPIs(self):
        headers = {'x-tyk-authorization' : self.authKey}
        return requests.get(f'{self.URL}/tyk/apis', headers=headers, verify=False)
    
    def createAPI(self, APIdefinition):        
        # need to convert it to a dict so we can check for api_definition and extract its contents
        if type(APIdefinition) is str:
            APIdefinition = json.loads(APIdefinition)
        if type(APIdefinition) is dict:
            # Can't use the dashboard format with api_model etc in it.
            # Must just be the contents of api_definition without the api_definition key
            if 'api_definition' in APIdefinition:
                APIdefinition = json.dumps(APIdefinition['api_definition'])
            else:
                APIdefinition = json.dumps(APIdefinition)
        headers = {'x-tyk-authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        response = requests.post(f'{self.URL}/tyk/apis', data=APIdefinition, headers=headers, verify=False)
        # automatically call the group reload (makes things simpler for a caller)
        reloadResp = requests.get(f'{self.URL}/tyk/reload/group', headers=headers, verify=False)
        if reloadResp.status_code != 200:
            print(f'[WARN]The group hot reload failed with code {reloadResp.status_code}: {reloadResp.json()}')
        return response

    def createAPIs(self, APIdefinition, numberToCreate):
        APIName = APIdefinition['api_definition']['name']
        apis = self.getAPIs().json()
        # create a dictionary of all API names
        allnames = dict()
        for api in apis:
            allnames[api['name']] = 1
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
            response = self.createAPI(APIdefinition)
            print(response.json())
            # if a call fails, stop and return the number of successes
            if resp.status_code != 200:
                break
            numberCreated += 1
        return numberCreated


    # Gateway Policy functions
    def getPolicy(self, policyID):
        headers = {'x-tyk-authorization' : self.authKey}
        return requests.get(f'{self.URL}/tyk/policies/{policyID}', headers=headers, verify=False)

    def getPolicies(self):
        headers = {'x-tyk-authorization' : self.authKey}
        return requests.get(f'{self.URL}/tyk/policies', headers=headers, verify=False)

    def createPolicy(self, policyDefinition):
        if type(policyDefinition) is dict:
            policyDefinition = json.dumps(policyDefinition)
        headers = {'x-tyk-authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        return requests.post(f'{self.URL}/tyk/policies', data=policyDefinition, headers=headers, verify=False)

    def createPolicies(self, policyDefinition, APIid, numberToCreate):
        policies = self.getPolicies().json()
        # create a dictionary of all policy names
        PolicyName = policyDefinition['name']
        for policy in policies:
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
            response = self.createPolicy(json.dumps(policyDefinition))
            print(response.json())
            # if a call fails, stop and return the number of successes
            if response.status_code != 200:
                break
            numberCreated += 1
        return numberCreated

    def updatePolicy(self, policyDefinition, policyID):
        if type(policyDefinition) is dict:
            policyDefinition = json.dumps(policyDefinition)
        headers = {'x-tyk-authorization' : self.authKey}
        headers['Content-Type'] = 'application/json'
        return requests.put(f'{self.URL}/tyk/policies/{policyID}', data=policyDefinition, headers=headers, verify=False)

    def deletePolicy(self, policyID):
        headers = {'x-tyk-authorization' : self.authKey}
        return requests.delete(f'{self.URL}/tyk/policies/{policyID}', headers=headers, verify=False)

    def deleteAllPolicies(self):
        allDeleted = True
        policies = self.getPolicies().json()
        for policy in policies:
            print(f'Deleting policy: {policy["_id"]}')
            response = self.deletePolicy(policy['_id'])
            print(response.json())
            if response.status_code != 200:
                allDeleted = False
        return allDeleted

