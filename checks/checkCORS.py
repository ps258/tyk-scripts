#!/usr/bin/python3

"""
CORS Header Testing Script

This script tests CORS (Cross-Origin Resource Sharing) headers returned by APIs.
It validates:
  - Origin specified in the Origin header matches Access-Control-Allow-Origin
  - Method specified in Access-Control-Request-Method matches Access-Control-Allow-Methods
  - Headers specified in Access-Control-Request-Headers match Access-Control-Allow-Headers

Tyk-specific notes:
  - Tyk will proxy upstream if 'Access-control-request-method' is not set even when CORS pass through is off
  - Tyk changes headers to canonical values (e.g., "fred" becomes "Fred")
  
Example usage:
  ./checkCORS.py --url https://api.example.com/endpoint --origins http://example.com,http://test.com --headers Authorization,Content-Type --verbose
"""

import requests
import sys
import argparse
import os
from typing import List, Dict, Tuple
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for testing environments
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Constants
HTTP_METHODS = ['GET', 'PUT', 'POST', 'PATCH', 'OPTIONS', 'DELETE', 'HEAD', 'CONNECT', 'TRACE']
SCRIPT_NAME = os.path.basename(__file__)


class CORSChecker:
    """Class to handle CORS validation logic"""
    
    def __init__(self, url: str, verbose: bool = False, timeout: int = 10):
        self.url = url
        self.verbose = verbose
        self.timeout = timeout
    
    def check_origin(self, origin: str, headers: Dict[str, str]) -> bool:
        """Check if the origin matches or if wildcard is present"""
        allowed_origin = headers.get('Access-Control-Allow-Origin', '')
        return allowed_origin == origin or allowed_origin == '*'
    
    def check_method(self, method: str, headers: Dict[str, str]) -> bool:
        """Check if the method is in the allowed methods"""
        allowed_methods = headers.get('Access-Control-Allow-Methods', '')
        return method.upper() in allowed_methods.upper()
    
    def check_request_headers(self, request_headers: List[str], headers: Dict[str, str]) -> Tuple[bool, List[str]]:
        """
        Check if all request headers are in the allowed headers (case-insensitive)
        Returns: (all_allowed, list_of_missing_headers)
        """
        allowed_headers = headers.get('Access-Control-Allow-Headers', '').lower()
        # Handle both single header and comma-separated list
        allowed_list = [h.strip() for h in allowed_headers.split(',')]
        
        # Check for wildcard
        if '*' in allowed_list:
            return True, []
        
        missing = []
        for req_header in request_headers:
            if req_header.lower() not in allowed_list:
                missing.append(req_header)
        
        return len(missing) == 0, missing
    
    def test_cors(self, origin: str, method: str, request_headers: List[str] = None) -> Tuple[bool, str, requests.Response]:
        """
        Test CORS for a specific origin, method, and optional headers
        Returns: (is_allowed, reason, response)
        """
        headers = {
            'Origin': origin,
            'Access-Control-Request-Method': method
        }
        
        if request_headers:
            # Join multiple headers with comma as per CORS spec
            headers['Access-Control-Request-Headers'] = ', '.join(request_headers)
            
            # Check if any headers are not lowercase and warn
            non_lowercase = [h for h in request_headers if h != h.lower()]
            if non_lowercase and self.verbose:
                print(f'      ⚠ Warning: RFC 6454 requires Access-Control-Request-Headers to be lowercase.')
                print(f'        Non-lowercase headers: {", ".join(non_lowercase)}')
            
            # Check if headers are sorted alphabetically (case-insensitive) as per RFC
            sorted_headers = sorted(request_headers, key=str.lower)
            if request_headers != sorted_headers:
                print(f'      ⚠ Warning: RFC requires Access-Control-Request-Headers to be sorted alphabetically.')
                print(f'        Current order: {", ".join(request_headers)}')
                print(f'        Expected order: {", ".join(sorted_headers)}')
        
        try:
            resp = requests.options(
                self.url,
                headers=headers,
                verify=False,
                timeout=self.timeout
            )
            return self._validate_response(resp, origin, method, request_headers)
        except requests.exceptions.RequestException as e:
            return False, f'Request failed: {str(e)}', None
    
    def _validate_response(self, resp: requests.Response, origin: str, method: str, request_headers: List[str] = None) -> Tuple[bool, str, requests.Response]:
        """Validate the CORS response headers"""
        reasons = []
        
        # Check Access-Control-Allow-Origin
        if 'Access-Control-Allow-Origin' not in resp.headers:
            reasons.append('Header Access-Control-Allow-Origin not present')
        elif not self.check_origin(origin, resp.headers):
            reasons.append(f'Origin {origin} not in Access-Control-Allow-Origin')
        
        # Check Access-Control-Allow-Methods
        if 'Access-Control-Allow-Methods' not in resp.headers:
            reasons.append('Header Access-Control-Allow-Methods not present')
        elif not self.check_method(method, resp.headers):
            reasons.append(f'Method {method} not in Access-Control-Allow-Methods')
        
        # Check Access-Control-Allow-Headers if request headers were specified
        if request_headers:
            if 'Access-Control-Allow-Headers' not in resp.headers:
                reasons.append(f'Header Access-Control-Allow-Headers not present')
            else:
                all_allowed, missing = self.check_request_headers(request_headers, resp.headers)
                if not all_allowed:
                    reasons.append(f'Request headers not allowed: {", ".join(missing)}')
        
        is_allowed = len(reasons) == 0
        reason = '; '.join(reasons) if reasons else ''
        
        return is_allowed, reason, resp


def print_verbose_response(resp: requests.Response):
    """Print detailed response information"""
    if resp:
        print(f'      Status Code: {resp.status_code}')
        cors_headers = {k: v for k, v in resp.headers.items() if 'access-control' in k.lower()}
        if cors_headers:
            print('      CORS Headers:')
            for key, value in cors_headers.items():
                print(f'        {key}: {value}')


def run_cors_tests(url: str, origins: List[str], request_headers: List[str], verbose: bool):
    """Main function to run CORS tests"""
    checker = CORSChecker(url, verbose)
    
    print(f'Testing CORS for URL: {url}\n')
    
    for origin in origins:
        print(f'Testing Origin: {origin}')
        
        for method in HTTP_METHODS:
            if not request_headers:
                # Test without custom headers
                is_allowed, reason, resp = checker.test_cors(origin, method)
                
                if is_allowed:
                    print(f'  ✓ {method} allowed')
                    if verbose:
                        print_verbose_response(resp)
                else:
                    if verbose:
                        print(f'  ✗ {method} disallowed by CORS: {reason}')
                        print_verbose_response(resp)
            else:
                # Test with all custom headers together (as per CORS spec)
                is_allowed, reason, resp = checker.test_cors(origin, method, request_headers)
                
                headers_str = ', '.join(request_headers)
                if is_allowed:
                    print(f'  ✓ {method} allowed with headers: {headers_str}')
                    if verbose:
                        print_verbose_response(resp)
                else:
                    if verbose:
                        print(f'  ✗ {method} disallowed with headers [{headers_str}]: {reason}')
                        print_verbose_response(resp)
        
        print()  # Blank line between origins


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Test CORS headers on API endpoints',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --url https://api.example.com/endpoint --origins http://example.com
  %(prog)s --url https://api.example.com/endpoint --origins http://example.com,http://test.com --headers Authorization,Content-Type --verbose
  %(prog)s --url https://api.example.com/endpoint --origins http://example.com --timeout 30
        """
    )
    
    parser.add_argument(
        '--url',
        required=True,
        help='REST API URL to test'
    )
    
    parser.add_argument(
        '--origins',
        required=True,
        help='Comma-separated list of origins to test (e.g., http://example.com,http://test.com)'
    )
    
    parser.add_argument(
        '--headers',
        default='',
        help='Comma-separated list of custom headers to test (e.g., Authorization,Content-Type)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output with detailed response information'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='Request timeout in seconds (default: 10)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Parse comma-separated values
    origins = [o.strip() for o in args.origins.split(',') if o.strip()]
    request_headers = [h.strip() for h in args.headers.split(',') if h.strip()] if args.headers else []
    
    if not origins:
        print('Error: At least one origin must be specified')
        sys.exit(1)
    
    try:
        run_cors_tests(args.url, origins, request_headers, args.verbose)
    except KeyboardInterrupt:
        print('\n\nTest interrupted by user')
        sys.exit(130)
    except Exception as e:
        print(f'\nError: {str(e)}')
        sys.exit(1)


if __name__ == '__main__':
    main()
