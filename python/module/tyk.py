# A module to speed up writing scripts to do stuff with the tyk dashboard
# This is not supported by anyone at any level but is just my efforts to make my life easier
# USE AT YOUR OWN RISK

import json
import requests
import time
import uuid
import sys
from packaging import version

# Suppress the warnings from urllib3 when using a self signed certs
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

###################### BASE CLASS ######################
# mostly for functions to print stuff out
class tyk:
    def __init__(self, URL, authKey, description, verify):
        self.session = requests.Session()
        self.URL = URL.strip('/')       # The dashboard or gateway URL
        self.authKey = authKey          # User key to authenticate API calls (admin key or gateway secret)
        self.description = description  # description of this instance
        self.session.verify = verify    # insecure skip verify

    def getUrl(self):
        return self.URL

    def setUrl(self, URL):
        self.URL = URL
        return URL

    def getDescription(self):
        return self.description

    def setDescription(self, description):
        self.description = description
        return description

    def getAuthKey(self):
        return self.authKey

    def setAuthKey(self, authKey):
        self.authKey = authKey
        self.session.headers.update({'Authorization': authKey})
        return self.authKey

    def setVerify(self, verify):
        self.session.verify = verify
        return verify

    def getVerify(self):
        return self.session.verify

    def printUserSummaryHeader(self):
        print('# ID,IsActive,org_id,first_name,last_name,email,IsAdmin,accessKey')

    def printUserSummary(self, user):
        if not "IsAdmin" in user["user_permissions"]:
            user["user_permissions"]["IsAdmin"] = "notAdmin"
        print(f'{user["id"]},{user["active"]},{user["org_id"]},{user["first_name"]},{user["last_name"]},{user["email_address"]},{user["user_permissions"]["IsAdmin"]},{user["access_key"]}')

    def printKeySummaryHeader(self):
        print('# Key; alias; policyID(s); API(s)')

    def printKeySummary(self,key):
        if "key_id" in key:
            print(f'{key["key_id"]};{key["data"]["alias"]}',end='')
        else:
            print(f'{key["key_hash"]};{key["data"]["alias"]}',end='')
        firstPolicy=True
        if "apply_policies" in key["data"] and key["data"]["apply_policies"] is not None:
            for policy in key["data"]["apply_policies"]:
                if firstPolicy:
                    print(f';{policy}',end='')
                    firstPolicy=False
                else:
                    print(f',{policy}',end='')
        else:
            print(';',end='')
        if "access_rights" in key["data"] and key["data"]["access_rights"] is not None:
            firstAPI=True
            for api in key["data"]["access_rights"]:
                if firstAPI:
                    print(f';{api}',end='')
                    firstAPI=False
                else:
                    print(f',{api}',end='')
        else:
            print(';',end='')
        print('')

    def printPolicySummaryHeader(self):
        print('# Name; policyID; policy_id; API, API, ...')

    def printPolicySummary(self, policy):
        if policy["id"] == "":
            policy["id"] = policy["_id"]
        print(f'{policy["name"]};{policy["id"]};{policy["_id"]}',end='')
        if "access_rights" in policy and policy["access_rights"] is not None:
            firstAPI=True
            for api in policy["access_rights"]:
                if firstAPI:
                    print(f';{api}',end='')
                    firstAPI=False
                else:
                    print(f',{api}',end='')
            print('')
        else:
            print(',')

    def printAPISummaryHeader(self):
        print('# Name; apiid')

    def printAPISummary(self, api):
        # handle both forms of classic API
        if "api_definition" in api:
            api = api["api_definition"]
        print(f'{api["name"]},{api["api_id"]}')

    def APIid(self, api):
        if "api_definition" in api:
            return api["api_definition"]["api_id"]
        return api["api_id"]

    def APIName(self, api):
        if "api_definition" in api:
            return api["api_definition"]["name"]
        return api["name"]

###################### DASHBOARD CLASS ######################
class dashboard(tyk):
    def __init__(self, URL, authKey = '', adminSecret = 'N/A' , description = 'N/A', verify = False):
        super().__init__(URL=URL, authKey=authKey, description=description, verify=verify)
        self.adminSecret = adminSecret  # The admin secret for the admin API (admin_secret in tyk_analytics.conf, AdminSecret in tyk.conf)
        self.session.headers.update({'Authorization': self.authKey})
        self.session.headers.update({'admin-auth': self.adminSecret})

    def __str__(self):
        return f'Dashboard URL: {self.URL}, Auth token: {self.authKey}, Admin Secret: {self.adminSecret}, Description: {self.description} Verify dashboard cert: {self.verify}'

    def __repr__(self):
        return f'tyk.dashboard("URL={self.URL}", authKey="{self.authKey}", adminSecret="{self.adminSecret}", description="{self.description}", verify={self.verify})'

    def getAdminSecret(self):
        return self.adminSecret

    def setAdminSecret(self, adminSecret):
        self.adminSecret = adminSecret
        self.session.headers.update({'admin-auth': adminSecret})
        return self.adminSecret



    # Dashboard API functions

    # Dashboard getAPI
    def getAPI(self, APIid):
        return self.session.get(f'{self.URL}/api/apis/{APIid}', verify=False)

    # Dashboard getAPIs
    def getAPIs(self):
        return self.session.get(f'{self.URL}/api/apis/?p=-1', verify=False)

    # Dashboard __createAPI
    def __createAPI(self, APIdefinition):
        headers = {'Content-Type': 'application/json'}
        return self.session.post(f'{self.URL}/api/apis', data=APIdefinition, headers=headers, verify=False)

    # Dashboard createAPI
    def createAPI(self, APIdefinition):
        APIdefinition = self.standardiseAPIformat(APIdefinition)
        if isinstance(APIdefinition, dict):
            APIdefinition = json.dumps(APIdefinition)
        return self.__createAPI(APIdefinition)

    # Dashboard createAPIs
    def createAPIs(self, APIdefinition, numberToCreate):
        APIdefinition = self.standardiseAPIformat(APIdefinition)
        # create a dictionary of all API names
        apis = self.getAPIs().json()
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
            response = self.__createAPI(json.dumps(APIdefinition))
            #print(response.json())
            # if a call fails, stop and return the number of successes
            if response.status_code != 200:
                break
            numberCreated += 1
        return numberCreated

    # Dashboard updateAPI
    def updateAPI(self, APIdefinition, APIid):
        if isinstance(APIdefinition, dict):
            APIdefinition = json.dumps(APIdefinition)
        headers = {'Content-Type': 'application/json'}
        return self.session.put(f'{self.URL}/api/apis/{APIid}', data=APIdefinition, headers=headers, verify=False)

    # Dashboard deleteAPI
    def deleteAPI(self, APIid):
        return self.session.delete(f'{self.URL}/api/apis/{APIid}', verify=False)

    # Dashboard deleteAllAPIs
    def deleteAllAPIs(self):
        allDeleted = True
        apis = self.getAPIs().json()['apis']
        for api in apis:
            id = self.APIid(api)
            #print(f'Deleting API: {self.APIName(api)}: {id}')
            response = self.deleteAPI(id)
            if response.status_code != 200:
                allDeleted = False
        return allDeleted

    # Dashboard standardise the API JSON format
    def standardiseAPIformat(self, APIdefinition):
        # the dashboard needs to have a key called 'api_definition' with the api_definition in it
        # but sometimes the json is just the API definition. So test for that and set it right
        if isinstance(APIdefinition, str):
            # convert to a dict so we can test for the api_definition key
            APIdefinition = json.loads(APIdefinition)
        if not 'api_definition' in APIdefinition:
            APIDict = dict()
            APIDict['api_definition'] = APIdefinition
            APIdefinition = APIDict
        return APIdefinition


    # Dashboard Policy functions
    # Dashboard getPolicy
    def getPolicy(self, policyID):
        return self.session.get(f'{self.URL}/api/portal/policies/{policyID}', verify=False)

    # Dashboard getPolicies
    def getPolicies(self):
        response = self.session.get(f'{self.URL}/api/portal/policies/?p=-1', verify=False)
        if response.status_code == 200:
            body_json = response.json()
            # rename 'Data' to 'polcies' to be consistent with apis, users and keys.
            body_json['policies'] = body_json['Data']
            del body_json['Data']
            response._content = json.dumps(body_json).encode()
        return response

    # Dashboard createPolicy
    def createPolicy(self, policyDefinition):
        if isinstance(policyDefinition, dict):
            policyDefinition = json.dumps(policyDefinition)
        headers = {'Content-Type': 'application/json'}
        return self.session.post(f'{self.URL}/api/portal/policies', data=policyDefinition, headers=headers, verify=False)

    # Dashboard createPolicies
    def createPolicies(self, policyDefinition, APIid, numberToCreate):
        policies = self.getPolicies().json()
        # create a dictionary of all policy names
        PolicyName = policyDefinition['name']
        allnames = dict()
        for policy in policies['policies']:
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
            #print(response.json())
            # if a call fails, stop and return the number of successes
            if response.status_code != 200:
                break
            numberCreated += 1
        return numberCreated

    # Dashboard updatePolicy
    def updatePolicy(self, policyDefinition, policyID):
        if isinstance(policyDefinition, dict):
            policyDefinition = json.dumps(policyDefinition)
        headers = {'Content-Type': 'application/json'}
        return self.session.put(f'{self.URL}/api/portal/policies/{policyID}', data=policyDefinition, headers=headers, verify=False)

    # Dashboard deletePolicy
    def deletePolicy(self, policyID):
        return self.session.delete(f'{self.URL}/api/portal/policies/{policyID}', verify=False)

    # Dashboard deleteAllPolicies
    def deleteAllPolicies(self):
        allDeleted = True
        policies = self.getPolicies().json()
        for policy in policies['policies']:
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

    # Dashboard getKeys
    def getKeys(self):
        return self.session.get(f'{self.URL}/api/apis/-/keys?p=-1', verify=False)

    # Dashboard getKeysDetailed
    def getKeysDetailed(self):
        return self.session.get(f'{self.URL}/api/keys/detailed/?p=-1', verify=False)

    # Dashboard getKey
    def getKey(self, keyID):
        return self.session.get(f'{self.URL}/api/apis/-/keys/{keyID}', verify=False)

    # Dashboard createKey
    def createKey(self, keyDefinition):
        if isinstance(keyDefinition, dict):
            keyDefinition = json.dumps(keyDefinition)
        headers = {'Content-Type': 'application/json'}
        return self.session.post(f'{self.URL}/api/keys', data=keyDefinition, headers=headers, verify=False)

    # Dashboard createCustomKey
    def createCustomKey(self, keyDefinition, keyID):
        if isinstance(keyDefinition, dict):
            keyDefinition = json.dumps(keyDefinition)
        headers = {'Content-Type': 'application/json'}
        return self.session.post(f'{self.URL}/api/keys/{keyID}', data=keyDefinition, headers=headers, verify=False)

    # Dashboard updateKey
    def updateKey(self, keyDefinition, keyID):
        if isinstance(keyDefinition, dict):
            keyDefinition = json.dumps(keyDefinition)
        headers = {'Content-Type': 'application/json'}
        return self.session.put(f'{self.URL}/api/keys/{keyID}', data=keyDefinition, headers=headers, verify=False)

    # Dashboard deleteKey
    def deleteKey(self, keyID):
        # not sure where ?auto_guess=true comes from but it works when keys are encrypted
        return self.session.delete(f'{self.URL}/api/keys/{keyID}/?auto_guess=true', verify=False)

    # Dashboard deleteAllKeys
    def deleteAllKeys(self):
        allDeleted = True
        keys = self.getKeys().json()
        for keyID in keys['data']['keys']:
            print(f'Deleting key: {keyID}')
            response = self.deleteKey(keyID)
            print(response.json())
            if response.status_code != 200:
                allDeleted = False
        return allDeleted

    # Dashboard keyExists
    def keyExists(self, keyID):
        resp = self.session.get(f'{self.URL}/api/apis/-/keys/{keyID}', verify=False)
        return resp.status_code == 200


    # Dashboard Portal Catalogue functions

    # Dashboard getCatalogue
    def getCatalogue(self):
        return self.session.get(f'{self.URL}/api/portal/catalogue', verify=False)

    # Dashboard updateCatalogue
    def updateCatalogue(self, catalogue):
        if isinstance(catalogue, dict):
            catalogue = json.dumps(catalogue)
        return self.session.put(f'{self.URL}/api/portal/catalogue', data=catalogue, verify=False)


    # Dashboard Organisation functions

    # Dashboard getOrganisations
    def getOrganisations(self):
        return self.session.get(f'{self.URL}/admin/organisations?p=-1', verify=False)

    # Dashboard getOrganisation
    def getOrganisation(self, orgID):
        return self.session.get(f'{self.URL}/admin/organisations/{orgID}', verify=False)

    # Dashboard createOrganisation
    def createOrganisation(self, orgDefinition):
        if isinstance(orgDefinition, dict):
            orgDefinition = json.dumps(orgDefinition)
        headers = {'Content-Type': 'application/json'}
        return self.session.post(f'{self.URL}/admin/organisations', data=orgDefinition, headers=headers, verify=False)

    # Dashboard createOrganisations
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

    # Dashboard deleteOrganisation
    def getOrganisation(self, orgID):
        return self.session.delete(f'{self.URL}/admin/organisations/{orgID}', verify=False)


    # Dashboard User functions

    # Dashboard createAdminUser
    def createAdminUser(self, userEmail, userPass, orgID):
        headers = {'Content-Type': 'application/json'}
        userDefinition = {
                'first_name': 'Tyk',
                'last_name': 'Admin',
                'email_address': userEmail,
                'password': userPass,
                'active': True,
                'org_id': orgID,
                'user_permissions': { 'ResetPassword' : 'admin', 'IsAdmin': 'admin' }}
        createResp = self.session.post(f'{self.URL}/admin/users', data=json.dumps(userDefinition), headers=headers, verify=False)
        if createResp.status_code != 200:
            return createResp
        # need to set the user password immediately
        userdata = createResp.json()
        self.setAuthKey(userdata['Meta']['access_key'])
        headers = {'Content-Type': 'application/json'}
        resetResp = self.session.post(f'{self.URL}/api/users/{userdata["Meta"]["id"]}/actions/reset', data='{"new_password":"'+userPass+'"}', headers=headers, verify=False)
        return createResp

    # Dashboard getUsers
    def getUsers(self):
        return self.session.get(f'{self.URL}/api/users?p=-1', verify=False)

    # Dashboard getUser
    def getUser(self, userid):
        return self.session.get(f'{self.URL}/api/users/{userid}', verify=False)

    # Dashboard deleteUser
    def deleteUser(self, userid):
        return self.session.delete(f'{self.URL}/api/users/{userid}/actions/key/reset', verify=False)

    # Dashboard resetAdminKey
    def resetAdminKey(self, userid):
        return self.session.put(f'{self.URL}/api/users/{userid}/actions/key/reset', verify=False)

    # Dashboard resetUserPassword
    def resetUserPassword(self, userid, userPass):
        return self.session.post(f'{self.URL}/api/users/{userid}/actions/reset', data='{"new_password":"'+userPass+'"}', verify=False)


    # Dashboard Licence functions

    # Dashboard setLicence
    def setLicence(self, licence):
        headers = {'Content-Type' : 'application/x-www-form-urlencoded'}
        return self.session.post(f'{self.URL}/license', data=f'license={licence}', headers=headers, verify=False)


    # Dashboard Bootstrap functions

    # Dashboard bootstrap. Takes an admin email, admin password, a dashboard licence and an optional portal cname.
    def bootstrap(self, userEmail, userPass, licence, cname = "portal.cname.com"):
        # set the licence
        response = self.setLicence(licence)
        if response.status_code != 200:
            print("[FATAL]licence cannot be set")
            return response
        # create the org
        orgDef = { "owner_name": userEmail, "owner_slug": "slug", "cname_enabled": True, "cname": cname}
        response = self.createOrganisation(orgDef)
        if response.status_code != 200:
            print("[FATAL]Failed to create organisation")
            return response
        orgID = response.json()['Meta']
        response = self.createAdminUser(userEmail, userPass, orgID)
        return response



    # Dashboard Analytics functions

    # Dashboard getAPIUsage
    def getAPIUsage(self, startday = time.strftime('%d'), startmonth = time.strftime('%m'), startyear = time.strftime('%Y'), endday = time.strftime('%d'), endmonth = time.strftime('%m'), endyear = time.strftime('%Y')):
        # Get the usage of all APIs for a period (defaults to today)
        if isinstance(startday, int):
            startday = str(startday)
        if isinstance(startmonth, int):
            startmonth = str(startmonth)
        if isinstance(startyear, int):
            startyear = str(startyear)
        if isinstance(endday, int):
            endday = str(endday)
        if isinstance(endmonth, int):
            endmonth = str(endmonth)
        if isinstance(endyear, int):
            endmonth = str(endyear)
        return self.session.get(f'{self.URL}/api/usage/apis/{startday}/{startmonth}/{startyear}/{endday}/{endmonth}/{endyear}?by=Hits&sort=1&p=-1', verify=False)

    # Dashboard Certificate functions

    # Dashboard getCerts
    def getCerts(self):
        return self.session.get(f'{self.URL}/api/certs?p=-1', verify=False)

    # Dashboard getCert
    def getCert(self, certid):
        return self.session.get(f'{self.URL}/api/certs/{certid}', verify=False)

    # Dashboard getCertsDetails
    def getCertsDetails(self):
        return self.session.get(f'{self.URL}/api/certs?p=-1&mode=detailed', verify=False)

    # Dashboard createCert
    def createCert(self, certFile):
        files={'data': open(certFile,'r')}
        return self.session.post(f'{self.URL}/api/certs', files=files, verify=False)

    # Dashboard deleteCert
    def deleteCert(self, certid):
        return self.session.delete(f'{self.URL}/api/certs/{certid}', verify=False)

    # Dashboard deleteAllCerts
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

    # Dashboard System functions

    # Dashboard getNodes
    def getNodes(self):
        return self.session.get(f'{self.URL}/api/system/nodes?p=-1', verify=False)

    # Dashboard getSystemStats
    def getSystemStats(self, ):
        return self.session.get(f'{self.URL}/api/system/stats', verify=False)

    # Dashboard getSystemStatus
    def getSystemStatus(self):
        return self.session.get(f'{self.URL}/hello/', verify=False)

    # Dashboard is up
    def isUp(self):
        try:
            response = self.getSystemStatus()
            return response.status_code == 200
        except:
            return False

    # Dashboard wait to be up
    def waitUp(self, timeout = 0):
        count = 0
        if timeout > 0:
            while (not self.isUp() and count < timeout):
                time.sleep(1)
                count += 1
        else:
            while not self.isUp():
                time.sleep(1)
        return self.isUp()



###################### GATEWAY CLASS ######################
class gateway(tyk):
    def __init__(self, URL, authKey = '', description = 'N/A', verify = False):
        super().__init__(URL=URL, authKey=authKey, description=description, verify=verify)
        self.session.headers.update({'x-tyk-authorization': self.authKey})
        self.session.headers.update({'Content-Type': 'application/json'})

    def __str__(self):
        return f'Gateway URL: {self.URL}, Auth token: {self.authKey}, Description: {self.description}, Verify gateway cert: {self.verify}'

    def __repr__(self):
        return f'tyk.gateway(URL="{self.URL}", authKey="{self.authKey}", description="{self.description}", verify={self.verify})'

    # Gateway API functions

    # Gateway reload
    def reload(self):
        response = self.session.get(f'{self.URL}/tyk/reload', verify=False)
        if response.status_code != 200:
            print(f'[WARN]The hot reload failed with code {response.status_code}: {response.json()}')
        return response

    # Gateway reloadGroup
    def reloadGroup(self):
        response = self.session.get(f'{self.URL}/tyk/reload/group', verify=False)
        if response.status_code != 200:
            print(f'[WARN]The group hot reload failed with code {response.status_code}: {response.json()}')
        return response

    # Gateway getAPI
    def getAPI(self, APIid):
        return self.session.get(f'{self.URL}/tyk/apis/{APIid}', verify=False)

    # Gateway getAPIs
    def getAPIs(self):
        response = self.session.get(f'{self.URL}/tyk/apis', verify=False)
        body_json = {}
        body_json['apis'] = response.json()
        response._content = json.dumps(body_json).encode()
        return response

    # Gateway __createAPI
    def __createAPI(self, APIdefinition):
        return self.session.post(f'{self.URL}/tyk/apis', data=APIdefinition, verify=False)

    # Gateway createAPI
    def createAPI(self, APIdefinition):
        # need to convert it to a dict so we can check for api_definition and extract its contents
        APIdefinition = self.standardiseAPIformat(APIdefinition)
        response = self.__createAPI(json.dumps(APIdefinition))
        # automatically call the group reload (makes things simpler for a caller)
        self.reloadGroup()
        return response

    # Gateway createAPIs
    def createAPIs(self, APIdefinition, numberToCreate):
        APIdefinition = self.standardiseAPIformat(APIdefinition)
        APIName = APIdefinition['name']
        apis = self.getAPIs().json()['apis']
        # create a dictionary of all API names
        allnames = {}
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
            APIdefinition['api_id'] = newname
            APIdefinition['name'] = newname
            APIdefinition['slug'] = newname
            APIdefinition['proxy']['listen_path'] = '/'+newname+'/'
            print(f'Adding API {APIdefinition["name"]}, {APIdefinition["proxy"]["listen_path"]}')
            # create the API but don't reload the group
            response = self.__createAPI(json.dumps(APIdefinition))
            #print(response.json())
            # if a call fails, stop and return the number of successes
            if response.status_code != 200:
                break
            numberCreated += 1
        # reload now
        self.reloadGroup()
        return numberCreated

    # Gateway updateAPI
    def updateAPI(self, APIdefinition, APIid):
        if isinstance(APIdefinition, dict):
            APIdefinition = json.dumps(APIdefinition)
        response = self.session.put(f'{self.URL}/tyk/apis/{APIid}', data=APIdefinition, verify=False)
        self.reloadGroup()
        return response

    # Gateway deleteAPI (private function which doesn't call reloadGroup)
    def __deleteAPI(self, APIid):
        return self.session.delete(f'{self.URL}/tyk/apis/{APIid}', verify=False)

    # Gateway deleteAPI
    def deleteAPI(self, APIid):
        response = self.__deleteAPI(APIid)
        self.reloadGroup()
        return response

    # Gateway deleteAllAPIs
    def deleteAllAPIs(self):
        allDeleted = True
        apis = self.getAPIs().json()['apis']
        for api in apis:
            print(f'Deleting API: {api["name"]}: {api["api_id"]}')
            response = self.__deleteAPI(api['api_id'])
            print(response.json())
            if response.status_code != 200:
                allDeleted = False
        self.reloadGroup()
        return allDeleted

    # Gateway standardise the API JSON format and always return a dict
    def standardiseAPIformat(self, APIdefinition):
        # the gateway must not have a key called 'api_definition' with the api_definition in it
        # but the object needs to be just the API definition itself
        if isinstance(APIdefinition, str):
            # convert to a dict so we can test for the api_definition key
            APIdefinition = json.loads(APIdefinition)
        if 'api_definition' in APIdefinition:
            APIdefinition = APIdefinition['api_definition']
        if 'api_id' not in APIdefinition or APIdefinition['api_id'] is None:
            APIdefinition['api_id'] = str(uuid.uuid4())
        return APIdefinition


    # Gateway Policy functions

    # Gateway getPolicy
    def getPolicy(self, policyID):
        return self.session.get(f'{self.URL}/tyk/policies/{policyID}', verify=False)

    # Gateway getPolicies
    def getPolicies(self):
        #print(f'{self.URL}/tyk/policies')
        cutoffVersion = "4.1.0"
        gatewayVersion = self.getVersion()
        if (version.parse(gatewayVersion) < version.parse(cutoffVersion)):
            print(f'[FATAL]Current gateway is {gatewayVersion}. Cannot retrieve polcies until v{cutoffVersion}', file=sys.stderr)
            #sys.exit(1)
        response = self.session.get(f'{self.URL}/tyk/policies/', verify=False)
        if response.status_code == 200:
            body_json = {}
            body_json['policies'] = response.json()
            response._content = json.dumps(body_json).encode()
        return response

    # Gateway __createPolicy (private function which doesn't call reloadGroup)
    def __createPolicy(self, policyDefinition):
        # convert to a dictionary so we can set the 'id'
        if isinstance(policyDefinition, str):
            policyDefinition = json.loads(policyDefinition)
        if isinstance(policyDefinition, dict):
            if not 'id' in policyDefinition:
                policyDefinition['id'] = str(uuid.uuid4())
            #print(json.dumps(policyDefinition, indent=2), file=sys.stderr)
        #policyID=policyDefinition["id"]
        policyDefinition = json.dumps(policyDefinition)
        #print(f'{self.URL}/tyk/keys/policy/{policyID}', file=sys.stderr)
        #response =  self.session.post(f'{self.URL}/tyk/keys/policy/{policyID}', data=policyDefinition, verify=False)
        response =  self.session.post(f'{self.URL}/tyk/policies', data=policyDefinition, verify=False)
        return response

    # Gateway createPolicy
    def createPolicy(self, policyDefinition):
        response = self.__createPolicy(policyDefinition)
        self.reloadGroup()
        return response

    # Gateway createPolicies
    def createPolicies(self, policyDefinition, APIid, numberToCreate):
        policies = self.getPolicies().json()
        # create a dictionary of all policy names
        allnames = dict()
        PolicyName = policyDefinition['name']
        for policy in policies['policies']:
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
            response = self.__createPolicy(json.dumps(policyDefinition))
            print(response.json())
            # if a call fails, stop and return the number of successes
            if response.status_code != 200:
                break
            numberCreated += 1
        self.reloadGroup()
        return numberCreated

    # Gateway updatePolicy
    def updatePolicy(self, policyDefinition, policyID):
        if isinstance(policyDefinition, dict):
            policyDefinition = json.dumps(policyDefinition)
        response = self.session.put(f'{self.URL}/tyk/policies/{policyID}', data=policyDefinition, verify=False)
        self.reloadGroup()
        return response

    # Gateway __deletePolicy (private function which doesn't call reloadGroup)
    def __deletePolicy(self, policyID):
        return self.session.delete(f'{self.URL}/tyk/policies/{policyID}', verify=False)

    # Gateway deletePolicy
    def deletePolicy(self, policyID):
        response = self.session.delete(f'{self.URL}/tyk/policies/{policyID}', verify=False)
        self.reloadGroup()
        return response

    # Gateway deleteAllPolicies
    def deleteAllPolicies(self):
        allDeleted = True
        policies_response = self.getPolicies()
        if policies_response == 200:
            for policy in policies_response.json()['policies']:
                if ('access_rights' in policy and policy['access_rights'] is not None) or ('access_rights_array' in policy and policy['access_rights_array'] is not None):
                    #print(json.dumps(policy, indent=2))
                    print(f'Deleting policy: {policy["id"]}')
                    response = self.__deletePolicy(policy['id'])
                    print(json.dumps(response.json()))
                    if response.status_code != 200:
                        allDeleted = False
        else:
            allDeleted = False
        return allDeleted


    # Gateway Key functions

    # Gateway getKeys
    def getKeys(self):
        response = self.session.get(f'{self.URL}/tyk/keys', verify=False)
        body_json = response.json()
        #print(json.dumps(body_json, indent=2))
        if response.status_code == 200:
            # pull the Keys out of the 'keys' array so that the format is the same as it is from the Dashboard
            keys = []
            for key in body_json['keys']:
                keys.append(key)
            response._content = json.dumps(keys).encode()
        return response

    # Gateway getKeysDetailed
    def getKeysDetailed(self):
        response = self.session.get(f'{self.URL}/tyk/keys', verify=False)
        body_json = response.json()
        #print(json.dumps(body_json, indent=2))
        if response.status_code == 200:
            # pull the Keys out of the 'keys' array so that the format is the same as it is from the Dashboard
            keys = {}
            keys['keys'] = []
            for key in body_json['keys']:
                #print(f'Key is {key}')
                keyObj = {}
                keyObj["key_id"] = key
                keyResp = self.getKey(key)
                if keyResp.status_code == 200:
                    keyObj["data"] = keyResp.json()
                    #keyJSON = f'"{key}": "{keyResp.json()}"'
                    #keys.append(keyResp.json())
                    #keys.append(keyJSON)
                    #body_json['keys'] = keyResp.json()
                keys['keys'].append(keyObj)
                #print(json.dumps(keys, indent=2))
            #print(json.dumps(body_json, indent=2))
            response._content = json.dumps(keys).encode()
        #print(json.dumps(response.json(), indent=2))
        return response

    # Gateway getKey
    def getKey(self, keyID):
        return self.session.get(f'{self.URL}/tyk/keys/{keyID}', verify=False)

    # Gateway createKey
    def createKey(self, keyDefinition):
        if isinstance(keyDefinition, dict):
            keyDefinition = json.dumps(keyDefinition)
        return self.session.post(f'{self.URL}/tyk/keys', data=keyDefinition, verify=False)

    # Gateway createCustomKey
    def createCustomKey(self, keyDefinition, keyID):
        if isinstance(keyDefinition, dict):
            keyDefinition = json.dumps(keyDefinition)
        return self.session.post(f'{self.URL}/tyk/keys/{keyID}', data=keyDefinition, verify=False)

    # Gateway updateKey
    def updateKey(self, keyDefinition, keyID):
        if isinstance(keyDefinition, dict):
            keyDefinition = json.dumps(keyDefinition)
        return self.session.put(f'{self.URL}/tyk/keys/{keyID}', data=keyDefinition, verify=False)

    # Gateway deleteKey
    def deleteKey(self, keyID):
        return self.session.delete(f'{self.URL}/api/keys/{keyID}', verify=False)

    # Gateway deleteAllKeys
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

    # Gateway keyExists
    def keyExists(self, keyID):
        resp = self.session.get(f'{self.URL}/tyk/keys/{keyID}', verify=False)
        return resp.status_code == 200


    # Gateway Certificate functions

    # Gateway getCerts
    def getCerts(self, orgid):
        # there seems to be a bug in retrieving certs from the gateway unless the orgid is specified (TT-8211)
        return self.session.get(f'{self.URL}/tyk/certs?p=-1&org_id={orgid}', verify=False)

    # Gateway getCert
    def getCert(self, certid):
        return self.session.get(f'{self.URL}/tyk/certs/{certid}', verify=False)

    # Gateway getCertsDetails
    def getCertsDetails(self):
        return self.session.get(f'{self.URL}/tyk/certs?p=-1&mode=detailed', verify=False)

    # Gateway createCert
    def createCert(self, certFile):
        files={'data': open(certFile,'r')}
        return self.session.post(f'{self.URL}/tyk/certs', files=files, verify=False)

    # Gateway deleteCert
    def deleteCert(self, certid):
        return self.session.delete(f'{self.URL}/tyk/certs/{certid}', verify=False)

    # Gateway deleteAllCerts
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

    # Gateway getSystemStatus
    def getSystemStatus(self):
        return self.session.get(f'{self.URL}/hello', verify=False)

    # Gateway is up
    def isUp(self):
        try:
            response = self.getSystemStatus()
            # for v3+ where there are some details
            if response.headers.get('content-type') == 'application/json':
                resp_json = response.json()
                if 'details' in resp_json:
                    if 'redis' in resp_json['details']:
                        if 'status' in resp_json['details']['redis']:
                            return resp_json['details']['redis']['status'] == "pass"
                return False
            else:
                # for earlier when it was just 'hello tikki'
                return response.status_code == 200
        except:
            return False

    # Gateway wait to be up
    def waitUp(self, timeout = 0):
        count = 0
        if timeout > 0:
            while (not self.isUp() and count < timeout):
                time.sleep(1)
                count += 1
        else:
            while not self.isUp():
                time.sleep(1)
        return self.isUp()

    # Gateway getVersion
    def getVersion(self):
        response = self.getSystemStatus()
        if 'application/json' in response.headers.get('content-type'):
            version = response.json()['version']
            return version.replace('v', '')
        if 'text/plain' in response.headers.get('content-type'):
            return '2.0'
        return '0.0'


###################### Auth Key Class ######################
# mostly for functions to print stuff out
class authKey(tyk):
    def __init__(self, keyFileName=""):
        if keyFileName:
            with open(keyFileName) as keyFile:
                self.JSON=json.load(keyFile)
        else:
            self.JSON = {}

        if not "access_rights" in self.JSON:
            self.JSON["access_rights"] = {}
        if not "alias" in self.JSON:
            self.JSON["alias"] = "Created by Pete's python module"
        if not "last_check" in self.JSON:
            self.JSON["last_check"] = 1421674410
        if not "expires" in self.JSON:
            self.JSON["expires"] = 0
        if not "quota_max" in self.JSON:
            self.JSON["quota_max"] = -1
        if not "quota_renews" in self.JSON:
            self.JSON["quota_renews"] = 1699629658
        if not "quota_remaining" in self.JSON:
            self.JSON["quota_remaining"] = -1
        if not "quota_renewal_rate" in self.JSON:
            self.JSON["quota_renewal_rate"] = 60
        if not "rate" in self.JSON:
            self.JSON["rate"] = 0
        if not "per" in self.JSON:
            self.JSON["per"] = 60
        if not "apply_policies" in self.JSON:
            self.JSON["apply_policies"] = []
        if not "allowance" in self.JSON:
            self.JSON["allowance"] = 0

    def __str__(self):
        return json.dumps(self.JSON, indent=2, sort_keys=True)

    def getRate(self):
        return self.JSON["rate"]

    def setRate(self, rate):
        self.JSON["rate"] = rate
        self.JSON["allowance"] = rate
        return self.JSON["rate"]

    def getPer(self):
        return self.JSON["per"]

    def setPer(self, per):
        self.JSON["per"] = per
        return self.JSON["per"]

    def addAPI(self, apiid):
        self.JSON["access_rights"][apiid] = {
            "api_id": apiid,
            "api_name": "",
            "versions": [ "Default" ],
            "allowed_urls": [],
            "restricted_types": [],
            "limit": None,
            "allowance_scope": ""
        }

    def addPolicy(self, polid):
        self.JSON["apply_policies"].append(polid)

    def json(self):
        return json.dumps(self.JSON)


