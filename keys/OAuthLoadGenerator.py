#!/usr/bin/python3

# This script does three things
# 1. Generates OAuth tokens against a Tyk OAuth Client and refreshes that when it expires (-x)
# 2. Calls the API using the generated token. It's not able to generate a huge load but will do 50 rps at least
# 3. Clear the expired tokens referenced in the z-set in redis that tracks them

import os
import sys
import base64
import argparse
import requests
import json
import re
import time

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def help_message():
    script_name = os.path.basename(sys.argv[0])
    print(f"{script_name}: A script to create and use OAuth access tokens")
    print("[USAGE]:")
    print(f"{script_name} -g <gateway URL> -a <API listen path> -i <client ID> -s <client Secret> -S <gateway Secret> -x <token TTL (s)> -r <API call rate (s)> -P <OAuth token purge interval (s)")
    print("         The Auth token will be created from the client ID and client secret")

def purgeOauthTokens(gateway, gateway_secret):
    headers = {
        'x-tyk-authorization': gateway_secret
        }
    try:
        response = requests.delete(f'{gateway}/tyk/oauth/tokens?scope=lapsed', headers=headers, verify=False)
        response.raise_for_status()
        print(response.json())
    except requests.exceptions.RequestException as e:
        print(f"Failed to purge tokens: {e}")
        print("Sleeping for 5s then retrying")
        time.sleep(5)
        purgeOauthTokens(gateway, gateway_secret)

def generateToken(url, encoded_auth_string, client_id, client_secret) -> str:
    print("[INFO]Generating Token:")
    print(f"[INFO]API URL: {url}")
    print(f"[INFO]Client ID: {client_id}")
    print(f"[INFO]Client Secret: {client_secret}")
    print(f"[INFO]Authorization: {encoded_auth_string}")
    print()

    headers = {
        'Authorization': f'Basic {encoded_auth_string}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }
    try:
        response = requests.post(url, headers=headers, data=data, verify=False)
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"Failed to generate token: {e}")
        print("Sleeping for 5s then retrying")
        time.sleep(5)
        return generateToken(url, encoded_auth_string, client_id, client_secret) 



def main():
    parser = argparse.ArgumentParser(description='Create lots of oauth tokens', add_help=False)
    parser.add_argument('-g', dest='gateway', help='Gateway URL')
    parser.add_argument('-a', dest='api', help='API listen path')
    parser.add_argument('-i', dest='client_id', help='Client ID')
    parser.add_argument('-s', dest='client_secret', help='Client Secret')
    parser.add_argument('-S', dest='gateway_secret', help='Gateway Secret. Needed to purge the expired tokens')
    parser.add_argument('-x', dest='token_ttl', help='Token TTL (s)')
    parser.add_argument('-r', dest='rps', default=0, help='API call RPS. Leave undefined for as fast as possible')
    parser.add_argument('-P', dest='purge_interval', help='The interval between token purges (s)')
    parser.add_argument('-h', '--help', action='store_true', help='Show help message')

    args = parser.parse_args()

    if args.help or not all([args.gateway, args.client_id, args.client_secret, args.api, args.token_ttl, args.gateway_secret, args.purge_interval]):
        help_message()
        sys.exit(1)

    # Remove trailing slashes
    gateway = re.sub(r'/$', '', args.gateway)
    api = re.sub(r'/$', '', args.api)
    # Remove leading slash
    api = re.sub(r'^/', '', api)
    token_ttl = int(args.token_ttl)
    purge_interval = int(args.purge_interval)
    rps = int(args.rps)
    
    # Create base64 encoded auth string
    auth_string = f"{args.client_id}:{args.client_secret}"
    auth = base64.b64encode(auth_string.encode()).decode()


    next_purge_time = int(time.time()) + purge_interval
    while True:

        # issue a token
        tokenExpires = int(time.time()) + token_ttl
        token = generateToken(f"{gateway}/{api}/oauth/token", auth, args.client_id, args.client_secret)

        # check if it's time to purge the tokens every time we issue a new one
        if int(time.time()) >= next_purge_time:
            purgeOauthTokens(gateway, args.gateway_secret)
            next_purge_time = int(time.time()) + purge_interval

        headers = { 'Authorization': f'Bearer {token}' }
        request_count = 0
        while int(time.time()) < tokenExpires:
            # call the API until the token expires
            try:
                response = requests.get(f"{gateway}/{api}/", headers=headers, verify=False)
                response.raise_for_status()
                request_count += 1
                print(f"{request_count}: {response.json()}")
            except requests.exceptions.RequestException as e:
                print(f"Request failed: {e}")

            # sleep briefly if rps is > 0.
            if rps:
                time.sleep(1/rps)

if __name__ == "__main__":
    main()

