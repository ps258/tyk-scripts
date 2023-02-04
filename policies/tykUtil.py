# A mmodule to speed up writing scripts to do stuff with the tyk dashboard
# This is not supported by anyone at any level but is just my efforts to make my life easier
# USE AT YOUR OWN RISK

import json
import requests
import sys

# API functions
def getAPIs(dashboardURL, authKey):
    dashboardURL = dashboardURL.strip('/')
    headers = {'Authorization' : authKey}
    resp = requests.get(f'{dashboardURL}/api/apis/?p=-1', headers=headers)
    if resp.status_code != 200:
        print(resp.text)
        sys.exit(1)
    return json.loads(resp.text)

def getAPI(dashboardURL, authKey, APIid):
    dashboardURL = dashboardURL.strip('/')
    headers = {'Authorization' : authKey}
    resp = requests.get(f'{dashboardURL}/api/apis/{APIid}', headers=headers)
    if resp.status_code != 200:
        print(resp.text)
        sys.exit(1)
    return json.loads(resp.text)

def createAPI(dashboardURL, authKey, APIdefinition):
    dashboardURL = dashboardURL.strip('/')
    headers = {'Authorization' : authKey}
    headers["Content-Type"] = "application/json"
    resp = requests.post(f'{dashboardURL}/api/apis', data=APIdefinition, headers=headers, allow_redirects=False)
    if resp.status_code != 200:
        print(resp.text)
        sys.exit(1)
    return json.loads(resp.text)

def updateAPI(dashboardURL, authKey, APIid, APIdefinition):
    dashboardURL = dashboardURL.strip('/')
    headers = {'Authorization' : authKey}
    headers["Content-Type"] = "application/json"
    resp = requests.put(f'{dashboardURL}/api/apis/{APIid}', data=APIdefinition, headers=headers, allow_redirects=False)
    if resp.status_code != 200:
        print(resp.text)
        sys.exit(1)
    return json.loads(resp.text)

def deleteAPI(dashboardURL, authKey, APIid):
    dashboardURL = dashboardURL.strip('/')
    headers = {'Authorization' : authKey}
    resp = requests.delete(f'{dashboardURL}/api/apis/{APIid}', headers=headers)
    if resp.status_code != 200:
        print(resp.text)
        sys.exit(1)
    return json.loads(resp.text)

# Policy function
def getPolicies(dashboardURL, authKey):
    dashboardURL = dashboardURL.strip('/')
    headers = {'Authorization' : authKey}
    resp = requests.get(f'{dashboardURL}/api/portal/policies/?p=-1', headers=headers)
    if resp.status_code != 200:
        print(resp.text)
        sys.exit(1)
    return json.loads(resp.text)

def getPolicy(dashboardURL, authKey, policyID):
    dashboardURL = dashboardURL.strip('/')
    headers = {'Authorization' : authKey}
    resp = requests.get(f'{dashboardURL}/api/portal/policies/{policyID}', headers=headers)
    if resp.status_code != 200:
        print(resp.text)
        sys.exit(1)
    return json.loads(resp.text)

def createPolicy(dashboardURL, authKey, policyDefinition):
    dashboardURL = dashboardURL.strip('/')
    headers = {'Authorization' : authKey}
    headers["Content-Type"] = "application/json"
    resp = requests.post(f'{dashboardURL}/api/portal/policies', data=policyDefinition, headers=headers, allow_redirects=False)
    if resp.status_code != 200:
        print(resp.text)
        sys.exit(1)
    return json.loads(resp.text)

def updatePolicy(dashboardURL, authKey, policyID, policyDefinition):
    dashboardURL = dashboardURL.strip('/')
    headers = {'Authorization' : authKey}
    headers["Content-Type"] = "application/json"
    resp = requests.put(f'{dashboardURL}/api/portal/policies/{policyID}', data=policyDefinition, headers=headers, allow_redirects=False)
    if resp.status_code != 200:
        print(resp.text)
        sys.exit(1)
    return json.loads(resp.text)

def deletePolicy(dashboardURL, authKey, policyID):
    dashboardURL = dashboardURL.strip('/')
    headers = {'Authorization' : authKey}
    headers["Content-Type"] = "application/json"
    resp = requests.delete(f'{dashboardURL}/api/portal/policies/{policyID}', headers=headers)
    if resp.status_code != 200:
        print(resp.text)
        sys.exit(1)
    return json.loads(resp.text)

# Key functions
def createKey(dashboardURL, authKey, keyDefinition):
    dashboardURL = dashboardURL.strip('/')
    headers = {'Authorization' : authKey}
    headers["Content-Type"] = "application/json"
    resp = requests.post(f'{dashboardURL}/api/keys', data=keyDefinition, headers=headers, allow_redirects=False)
    if resp.status_code != 200:
        print(resp.text)
        sys.exit(1)
    return json.loads(resp.text)

# Portal Catalogue functions
def getCatalogue(dashboardURL, authKey):
    dashboardURL = dashboardURL.strip('/')
    headers = {'Authorization' : authKey}
    resp = requests.get(f'{dashboardURL}/api/portal/catalogue', headers=headers)
    if resp.status_code != 200:
        print(resp.text)
        sys.exit(1)
    return json.loads(resp.text)

def updateCatalogue(dashboardURL, authKey, catalogue):
    dashboardURL = dashboardURL.strip('/')
    headers = {'Authorization' : authKey}
    resp = requests.put(f'{dashboardURL}/api/portal/catalogue', date=catalogue, headers=headers)
    if resp.status_code != 200:
        print(resp.text)
        sys.exit(1)
    return json.loads(resp.text)
