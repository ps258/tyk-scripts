#!/usr/bin/python3

import json
import requests

# mine
day=1
month=10
year=2021
dshb = "https://daskboard.url"
tags = ["Customer1", "Customer2"]
auth = "auth-from-userid"

tagUse = {}
for tag in tags:
    tagUse[tag] = 0

# get keys
auth_header = {'Authorization' : auth}
resp = requests.get(f'{dshb}/api/activity/keys/{day}/{month}/{year}/{day}/{month}/{year}?p=-1', headers=auth_header)
keys = json.loads(resp.text)
#print(resp.text)
for keyid in keys['data']:
    print(keyid['id']['key'])

for keyid in keys['data']:
    key = keyid['id']['key']
    resp = requests.get(f'{dshb}/api/activity/keys/{key}/{day}/{month}/{year}/{day}/{month}/{year}?res=day&p=-1', headers=auth_header)
    keyUse = json.loads(resp.text)
    print(f'Key {key}, hits {keyUse["data"][0]["hits"]}')

for keyid in keys['data']:
    key = keyid['id']['key']
    for tag in tags:
        url=f'{dshb}/api/activity/keys/{key}/{day}/{month}/{year}/{day}/{month}/{year}?res=day&p=-1&tags={tag}'
        #print(url)
        resp = requests.get(url, headers=auth_header)
        keyUse = json.loads(resp.text)
        try:
            hits = keyUse["data"][0]["hits"]
        except:
            hits = 0
        print(f'Key {key}, Tag {tag}, hits {hits}')
        tagUse[tag] += hits

print("Customer use")
for tag in tags:
    print(tag, " -> ", tagUse[tag])
