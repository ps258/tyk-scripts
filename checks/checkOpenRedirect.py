#!/usr/bin/python3

# attempts to perform an open redirect and reports the results
# Usage: python open_redirect_test.py <url> <redirect_url>

import sys
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def test_open_redirect(url, redirect_url):
    payload = { 'redirect': redirect_url }
    response = requests.get(url, params=payload, verify=False)

    # Check if the response URL matches the redirect URL
    if response.url == redirect_url:
        print(f"The URL '{url}' is vulnerable to open redirect.")
    else:
        print(f"The URL '{url}' is not vulnerable to open redirect.")

# Example usage
#test_open_redirect("http://192.168.49.2:30818/", "https://google.com")
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python open_redirect_test.py <url> <redirect_url>")
        sys.exit(1)

    url = sys.argv[1]
    redirect_url = sys.argv[2]
    test_open_redirect(url, redirect_url)

