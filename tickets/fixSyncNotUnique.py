#!/usr/bin/python3

# When a 'tyk-sync dump' is provided from an environment where 'enable_duplicate_slugs' is true you
# cannot do a 'tyk-sync publish' because the names, slugs and listen paths are not unique.
# This script will alter the dumped API files so that the names, listen paths and slugs are unique

import sys
import json

allnames = dict()
allslugs = dict()
alllisten_paths = dict()

if __name__ == "__main__":
    for i, file in enumerate(sys.argv[1:]):
        with open(file, "r") as APIFile:
            APIjson=json.load(APIFile)
        changed = False
        name = APIjson["api_definition"]["name"]
        slug = APIjson["api_definition"]["slug"]
        listen_path = APIjson["api_definition"]["proxy"]["listen_path"]
        i = 1
        #print(f'{file}: {name}, {slug}, {listen_path}')
        if name in allnames:
            # find the next free name
            while name+str(i) in allnames:
                i += 1
            newname = name+str(i)
            allnames[newname] = 1
            print(f'File: {file} Name Clash: {name} -> {newname}')
            APIjson["api_definition"]["name"] = newname
            changed = True
        else:
            allnames[name] = 1

        if slug in allslugs:
            while slug+str(i) in allslugs:
                i += 1
            newslug = slug+str(i)
            allslugs[newslug] = 1
            APIjson["api_definition"]["slug"] = newslug
            changed = True
            print(f'File: {file} Slug Clash: {slug} -> {newslug}')
        else:
            allslugs[slug] = 1

        if listen_path in alllisten_paths:
            while listen_path+str(i) in alllisten_paths:
                i += 1
            newlisten_path = listen_path+str(i) 
            alllisten_paths[newlisten_path] = 1
            APIjson["api_definition"]["proxy"]["listen_path"] = newlisten_path
            changed = True
            print(f'File: {file} Listen Path Clash: {listen_path} -> {newlisten_path}')
        else:
            alllisten_paths[listen_path] = 1

        if changed:
            with open(file, "w") as APIFile:
                APIFile.write(json.dumps(APIjson, indent=2))
