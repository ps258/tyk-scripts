#!/bin/bash

# use if the customer sends you a tyk-sync dump but forgets the .tyk.json file

echo '{"type": "apidef","files": ['
first=1
for apifile in api*.json; do
  if [[ -f $apifile ]]; then
    if [[ $first -ne 1 ]]; then
      echo ,
    fi
    echo -n '{"file":"'$apifile'","oas":{}}'
    first=0
  fi
done

echo '],"policies": ['
first=1
for policyfile in policy*.json; do
  if [[ -f $policyfile ]]; then
    if [[ $first -ne 1 ]]; then
      echo ,
    fi
    echo -n '{"file":"'$policyfile'"}'
    first=0
  fi
done
echo ']}'
