#!/bin/bash

PATH=/bin:/usr/bin:/usr/local/bin:/sbin:/usr/sbin:/usr/local/sbin:~/bin

# A script to see if there are release packages left in -unstable repos on package cloud.
# Most non-stable packages have ~rc in their name but not all.
# And the occasional release package has ~p in it for example gateway 4.0.8~p3
# But this script filters out ~ so will not find those

BASE_URL=https://packagecloud.io
MAX_PAGES=100  # focus on the most recent releases

for URL in $(curl -s https://packagecloud.io/tyk | awk -F\" '/unstable/ && /href=/ {print $4}'); do
  page_count=$(curl -s $BASE_URL/$URL | awk '/role="navigation"/ && match($0, /.*Page ([0-9]+)/, a) {print a[1]}')
  if [[ $page_count -gt $MAX_PAGES ]]; then
    echo "[INFO]$page_count pages found. Limiting to fetching only $MAX_PAGES"
    page_count=$MAX_PAGES
  fi
  echo "$BASE_URL/$URL: $page_count pages to fetch"
  for page in $(seq 0 $page_count); do
    curl -s "$BASE_URL/$URL?page=$page" 2>&-
  done |  awk '/\/packages\// && !/~/ {print $3}' | cut -d\" -f2 | cut -d? -f1 | sort -u
  echo
done
