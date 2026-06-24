#!/usr/bin/env python3
"""
RPC Server Health Check Script

This script checks if an RPC server is up and running by attempting to connect
to it every second. It reports success or failure for each connection attempt.

Based on the connection logic from rpc_client.go, this script:
- Supports both TCP and TLS connections
- Sends the protocol handshake ("proto2")
- Does not perform authentication
- Reports connection status every second
"""

import socket
import ssl
import time
import sys
import argparse
from datetime import datetime
from typing import Tuple


class RPCHealthChecker:
    """Health checker for RPC server connectivity"""
    
    def __init__(self, host: str, port: int, use_ssl: bool = False,
                 ssl_verify: bool = True, timeout: int = 10):
        """
        Initialize the RPC health checker.
        
        Args:
            host: RPC server hostname or IP address
            port: RPC server port
            use_ssl: Whether to use SSL/TLS connection
            ssl_verify: Whether to verify SSL certificates (only used if use_ssl=True)
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.ssl_verify = ssl_verify
        self.timeout = timeout
        self.connection_string = f"{host}:{port}"
        
        # Statistics tracking
        self.start_time = None
        self.success_count = 0
        self.failure_count = 0
        self.total_connection_time = 0.0
        
    def check_connection(self) -> Tuple[bool, str, float]:
        """
        Attempt to connect to the RPC server.
        
        Returns:
            Tuple of (success: bool, message: str, connection_time: float)
        """
        start = time.time()
        sock = None
        try:
            # Create a socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            
            # Wrap with SSL if needed
            if self.use_ssl:
                context = ssl.create_default_context()
                if not self.ssl_verify:
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                sock = context.wrap_socket(sock, server_hostname=self.host)
            
            # Connect to the server
            sock.connect((self.host, self.port))
            
            # Send protocol handshake (matching the Go client behavior)
            # The Go client sends: "proto2" + length byte + connection ID
            # For health check, we just send the protocol identifier
            sock.sendall(b"proto2")
            
            connection_time = time.time() - start
            return True, "Connection successful", connection_time
            
        except socket.timeout:
            connection_time = time.time() - start
            return False, f"Connection timeout after {self.timeout}s", connection_time
        except socket.gaierror as e:
            connection_time = time.time() - start
            return False, f"DNS resolution failed: {e}", connection_time
        except ConnectionRefusedError:
            connection_time = time.time() - start
            return False, "Connection refused - server may be down", connection_time
        except ssl.SSLError as e:
            connection_time = time.time() - start
            return False, f"SSL error: {e}", connection_time
        except Exception as e:
            connection_time = time.time() - start
            return False, f"Error: {type(e).__name__}: {e}", connection_time
        finally:
            # Ensure socket is always closed, even on errors
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass  # Ignore errors during cleanup
    
    def print_summary(self):
        """Print summary statistics on exit"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        print("\n" + "=" * 70)
        print("HEALTH CHECK SUMMARY")
        print("=" * 70)
        print(f"Start Time:       {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time:         {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration:         {duration:.1f} seconds")
        print(f"Total Checks:     {self.success_count + self.failure_count}")
        print("-" * 70)
        
        if self.success_count > 0:
            avg_time = (self.total_connection_time / self.success_count) * 1000  # Convert to ms
            success_rate = (self.success_count / (self.success_count + self.failure_count)) * 100
            print(f"✓ Successes:      {self.success_count} ({success_rate:.1f}%)")
            print(f"  Avg Conn Time:  {avg_time:.2f} ms")
        else:
            print(f"✓ Successes:      0 (0.0%)")
            print(f"  Avg Conn Time:  N/A")
        
        if self.failure_count > 0:
            failure_rate = (self.failure_count / (self.success_count + self.failure_count)) * 100
            print(f"✗ Failures:       {self.failure_count} ({failure_rate:.1f}%)")
        else:
            print(f"✗ Failures:       0 (0.0%)")
        
        print("=" * 70)
    
    def run_continuous_check(self, interval: int = 1):
        """
        Run continuous health checks at specified interval.
        
        Args:
            interval: Time between checks in seconds
        """
        self.start_time = datetime.now()
        
        print(f"Starting RPC health check for {self.connection_string}")
        print(f"SSL: {self.use_ssl}, Interval: {interval}s, Timeout: {self.timeout}s")
        print(f"Only failures will be printed")
        print("-" * 70)
        
        consecutive_failures = 0
        consecutive_successes = 0
        
        try:
            while True:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                success, message, connection_time = self.check_connection()
                
                if success:
                    self.success_count += 1
                    self.total_connection_time += connection_time
                    consecutive_successes += 1
                    consecutive_failures = 0
                    # Don't print successful connections
                else:
                    self.failure_count += 1
                    consecutive_failures += 1
                    consecutive_successes = 0
                    status = "✗ DOWN"
                    color = "\033[91m"  # Red
                    reset = "\033[0m"  # Reset color
                    
                    print(f"[{timestamp}] {color}{status}{reset} - {message} "
                          f"(consecutive failures: {consecutive_failures})")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.print_summary()
            sys.exit(0)


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description="RPC Server Health Check - Monitor RPC server connectivity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check TCP connection to localhost:5000
  python rpc_health_check.py localhost 5000
  
  # Check SSL connection with certificate verification
  python rpc_health_check.py example.com 5000 --ssl
  
  # Check SSL connection without certificate verification
  python rpc_health_check.py example.com 5000 --ssl --no-verify
  
  # Check every 5 seconds with 15 second timeout
  python rpc_health_check.py localhost 5000 --interval 5 --timeout 15
        """
    )
    
    parser.add_argument("host", help="RPC server hostname or IP address")
    parser.add_argument("port", type=int, help="RPC server port")
    parser.add_argument("--ssl", action="store_true", 
                       help="Use SSL/TLS connection")
    parser.add_argument("--no-verify", action="store_true",
                       help="Skip SSL certificate verification (use with --ssl)")
    parser.add_argument("--interval", type=int, default=1,
                       help="Check interval in seconds (default: 1)")
    parser.add_argument("--timeout", type=int, default=10,
                       help="Connection timeout in seconds (default: 10)")
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.port < 1 or args.port > 65535:
        print("Error: Port must be between 1 and 65535", file=sys.stderr)
        sys.exit(1)
    
    if args.no_verify and not args.ssl:
        print("Warning: --no-verify has no effect without --ssl")
    
    # Create and run health checker
    checker = RPCHealthChecker(
        host=args.host,
        port=args.port,
        use_ssl=args.ssl,
        ssl_verify=not args.no_verify,
        timeout=args.timeout
    )
    
    checker.run_continuous_check(interval=args.interval)


if __name__ == "__main__":
    main()
