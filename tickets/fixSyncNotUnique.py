#!/usr/bin/python3

# When a 'tyk-sync dump' is provided from an environment where 'enable_duplicate_slugs' is true you
# cannot do a 'tyk-sync publish' because the names, slugs and listen paths are not unique.
# This script will alter the dumped API files so that the names, listen paths and slugs are unique

import sys
import json

allNames = dict()
allSlugs = dict()
allListenPaths = dict()

def getNewName(name, allNames):
    if name in allNames:
        i = 1
        while name+str(i) in allNames:
            i += 1
        newname = name+str(i)
        allNames[newname] = 1
        return newname
    allNames[name] = 1
    return name

def getNewSlug(slug, allSlugs):
    if slug in allSlugs:
        i = 1
        while slug+str(i) in allSlugs:
            i += 1
        newslug = slug+str(i)
        allSlugs[newslug] = 1
        return newslug
    allSlugs[slug] = 1
    return slug

def getNewListenPath(listenPath, allListenPaths):
    if listenPath in allListenPaths:
        i = 1
        while listenPath+str(i) in allListenPaths:
            i += 1
        newListenPath = listenPath+str(i)
        allListenPaths[newListenPath] = 1
        return newListenPath
    allListenPaths[listenPath] = 1
    return listenPath

if __name__ == "__main__":
    if len(sys.argv) < 2 :
        print(f"[USAGE]{sys.argv[0]}: api* oas*")
        print(f"       It is necessary to specify both the path to the api* and oas* files at the same time so that the listen paths can be made unique")
        sys.exit(1)
    for i, file in enumerate(sys.argv[1:]):
        with open(file, "r") as APIFile:
            APIjson=json.load(APIFile)
        changed = False
        if "api_definition" in APIjson:
            name = APIjson["api_definition"]["name"]
            slug = APIjson["api_definition"]["slug"]
            listenPath = APIjson["api_definition"]["proxy"]["listen_path"]
            #print(f'{file}: {name}, {slug}, {listenPath}')

            # find the next free name
            newname = getNewName(name, allNames)
            if name != newname:
                print(f'File: {file} Name Clash: {name} -> {newname}')
                APIjson["api_definition"]["name"] = newname
                changed = True

            # find the next free slug
            newslug = getNewSlug(slug, allSlugs)
            if slug != newslug:
                print(f'File: {file} Slug Clash: {slug} -> {newslug}')
                APIjson["api_definition"]["slug"] = newslug
                changed = True

            # find the next free listen path
            newListenPath = getNewListenPath(listenPath, allListenPaths)
            if newListenPath != listenPath:
                print(f'File: {file} Listen Path Clash: {listenPath} -> {newListenPath}')
                APIjson["api_definition"]["proxy"]["listen_path"] = newListenPath
                changed = True
        
        elif "oas" in APIjson:
            name = APIjson["oas"]["x-tyk-api-gateway"]["info"]["name"]
            listenPath = APIjson["oas"]["x-tyk-api-gateway"]["server"]["listenPath"]["value"]

            # find the next free name
            newname = getNewName(name, allNames)
            if name != newname:
                print(f'File: {file} Name Clash: {name} -> {newname}')
                APIjson["oas"]["x-tyk-api-gateway"]["info"]["name"] = newname
                changed = True

            # find the next free listen path
            newListenPath = getNewListenPath(listenPath, allListenPaths)
            if newListenPath != listenPath:
                print(f'File: {file} Listen Path Clash: {listenPath} -> {newListenPath}')
                APIjson["oas"]["x-tyk-api-gateway"]["server"]["listenPath"]["value"] = newListenPath
                changed = True
        
        elif "oas" in APIjson:
            name = APIjson["oas"]["x-tyk-api-gateway"]["info"]["name"]
            listenPath = APIjson["oas"]["x-tyk-api-gateway"]["server"]["listenPath"]["value"]

        else:
            print(f"[WARN]{file=} is not in Tyk Classic or Tyk OAS format")

        if changed:
            with open(file, "w") as APIFile:
                APIFile.write(json.dumps(APIjson, indent=2))
