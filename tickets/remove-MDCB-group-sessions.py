#!/usr/bin/env python3

# When the data plane gateways don't have a long life lots of records can build up in redis
# This script tidies up the unused ones and sets a TTL on the used ones so that they will evaporate
# The related Jira is TT-15281 Session Key Build-up Causing MDCB-Gateway Communication Failures
# An MDCB restart will remove the in-memory list which causes the symptoms in TT-15281 but the keys will persist in redis
# This script will tidy those up

import argparse
import re
from redis import Redis
from redis.cluster import RedisCluster
from redis.exceptions import RedisError

def main():
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Check TTL of specific Redis keys (Cluster-aware)')
    parser.add_argument('--host', dest='host', default='localhost', help='Redis server host (default: localhost)')
    parser.add_argument('--port', dest='port', type=int, default=6379, help='Redis server port (default: 6379)')
    parser.add_argument('--password', dest='password', help='Redis server password (optional)')
    parser.add_argument('--batch-size', dest='batch_size', type=int, default=100, help='Scan batch size (default: 100)')
    parser.add_argument('--cluster', dest='cluster', action='store_true', help='Connect to a Redis Cluster')
    parser.add_argument('--nodes', dest='nodes', help='Comma-separated list of cluster nodes (host:port format)')
    parser.add_argument('--live-run', dest='live_run', action='store_true', help='Commit changes to redis rather than just printing what would be done')
    
    args = parser.parse_args()
    
    # Connect to Redis (either standalone or cluster)
    try:
        if args.cluster:
            # For cluster mode, we can use either a single node or multiple nodes
            if args.nodes:
                # Parse the comma-separated list of nodes
                startup_nodes = []
                for node in args.nodes.split(','):
                    host, port = node.strip().split(':')
                    startup_nodes.append({"host": host, "port": int(port)})
                
                r = RedisCluster(
                    startup_nodes=startup_nodes,
                    password=args.password,
                    decode_responses=True
                )
            else:
                # Use a single node as the entry point to the cluster
                r = RedisCluster(
                    host=args.host,
                    port=args.port,
                    password=args.password,
                    decode_responses=True
                )
            print(f"Successfully connected to Redis Cluster via {args.host}:{args.port}")
        else:
            # Standalone Redis
            r = Redis(
                host=args.host,
                port=args.port,
                password=args.password,
                decode_responses=True
            )
            print(f"Successfully connected to Redis at {args.host}:{args.port}")
        
        # Test connection
        r.ping()
    except RedisError as e:
        print(f"Failed to connect to Redis: {e}")
        return
    
    # Use scan_iter to iterate through keys matching the pattern
    group_keys = []
    
    # Count for progress reporting
    count = 0
    print("Scanning for keys (this may take a while for large databases)...")
    
    try:
        # In cluster mode, scan_iter will iterate through all nodes
        for group_key in r.scan_iter(match="tyk-sink-sessions.group*", count=args.batch_size):
            count += 1
            if count % 1000 == 0:
                print(f"Scanned {count} keys so far...")
                
            group_keys.append(group_key)
        print(f"Found {count} keys matching tyk-sink-sessions.group*")
    except Exception as e:
        print(f"Error during group key scanning: {e}")
        return
    
    # If the group_key doesn't have a TTL, check if the session_key exists.
    # If the corresponding session_key exists then set the group_key TTL to the session_key TTL
    # If the corresponding session_key doesn't exist then delete the group_key
    if group_keys:
        for group_key in group_keys:
            nonce = group_key.split("group")[-1]
            session_key = f"tyk-sink-sessions.{nonce}"
            #print(group_key, nonce, " => ", session_key)
            group_key_ttl = r.ttl(group_key)
            if group_key_ttl <= 0:
                # If the corresponding session_key exists then set the group_key TTL to the session_key TTL
                if r.exists(session_key):
                    session_key_ttl = r.ttl(session_key)
                    print(f"Setting TTL of {group_key} to {session_key_ttl}s")
                    if args.live_run:
                        r.expire(group_key, session_key_ttl)
                else:
                    # If the corresponding session_key doesn't exist then delete the group_key
                    print(f"Deleting {group_key} because {session_key} is not present")
                    if args.live_run:
                        r.delete(group_key)
            else:
                # the group_key has a TTL, report the group_key and session_key with TTLs to verify things are right
                session_key_ttl = r.ttl(session_key)
                print(f"Group key TTL already set {group_key}:{group_key_ttl} -> {session_key}:{session_key_ttl}")
    else:
        print("No matching keys found. This script is for the control plane redis of an MDCB enabled deployement")

if __name__ == "__main__":
    main()
