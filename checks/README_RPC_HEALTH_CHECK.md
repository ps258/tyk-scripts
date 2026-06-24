# RPC Server Health Check

A Python script to monitor RPC server connectivity, based on the connection logic from [`rpc_client.go`](../code/tyk/rpc/rpc_client.go).

## Features

- ✅ Tests RPC server connectivity every second (configurable)
- ✅ Supports both TCP and TLS/SSL connections
- ✅ Sends protocol handshake (`proto2`) matching the Go client behavior
- ✅ Does **not** perform authentication (health check only)
- ✅ Color-coded output (green for UP, red for DOWN)
- ✅ Tracks consecutive successes/failures
- ✅ Configurable timeout and check interval

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only standard library)

## Usage

### Basic Usage

```bash
# Make the script executable (optional)
chmod +x rpc_health_check.py

# Check TCP connection
python rpc_health_check.py localhost 5000

# Or if made executable
./rpc_health_check.py localhost 5000
```

### SSL/TLS Connection

```bash
# With certificate verification
python rpc_health_check.py example.com 5000 --ssl

# Without certificate verification (insecure, for testing only)
python rpc_health_check.py example.com 5000 --ssl --no-verify
```

### Custom Intervals and Timeouts

```bash
# Check every 5 seconds with 15 second timeout
python rpc_health_check.py localhost 5000 --interval 5 --timeout 15
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `host` | RPC server hostname or IP address | (required) |
| `port` | RPC server port | (required) |
| `--ssl` | Use SSL/TLS connection | False |
| `--no-verify` | Skip SSL certificate verification | False |
| `--interval` | Check interval in seconds | 1 |
| `--timeout` | Connection timeout in seconds | 10 |

## Example Output

```
Starting RPC health check for localhost:5000
SSL: False, Interval: 1s, Timeout: 10s
----------------------------------------------------------------------
[2026-04-13 13:30:01] ✓ UP - Connection successful (consecutive: 1)
[2026-04-13 13:30:02] ✓ UP - Connection successful (consecutive: 2)
[2026-04-13 13:30:03] ✓ UP - Connection successful (consecutive: 3)
[2026-04-13 13:30:04] ✗ DOWN - Connection refused - server may be down (consecutive: 1)
[2026-04-13 13:30:05] ✗ DOWN - Connection refused - server may be down (consecutive: 2)
```

## How It Works

The script mimics the connection behavior from the Go RPC client:

1. **Creates a socket connection** - TCP or TLS based on configuration
2. **Sends protocol handshake** - Sends `proto2` to match the Go client's protocol
3. **Reports status** - Indicates whether the connection succeeded or failed
4. **Repeats** - Checks every second (or configured interval)

Unlike the full Go client, this script:
- Does **not** authenticate with API keys
- Does **not** send connection IDs
- Does **not** maintain persistent connections
- Simply checks if the server is accepting connections

## Stopping the Script

Press `Ctrl+C` to stop the health check gracefully.

## Comparison with Go Client

| Feature | Go Client ([`rpc_client.go`](../code/tyk/rpc/rpc_client.go)) | Python Health Check |
|---------|--------------|---------------------|
| Connection | ✅ TCP/TLS | ✅ TCP/TLS |
| Protocol handshake | ✅ `proto2` + conn ID | ✅ `proto2` only |
| Authentication | ✅ API Key/Group login | ❌ No authentication |
| Persistent connection | ✅ Connection pool | ❌ Connect & disconnect |
| Purpose | Production RPC client | Health monitoring |

## Use Cases

- **Monitoring**: Check if RPC server is running before starting dependent services
- **Debugging**: Verify network connectivity to RPC server
- **CI/CD**: Wait for RPC server to be ready in deployment pipelines
- **Alerting**: Integrate with monitoring systems to detect RPC server downtime

## Exit Codes

- `0` - Normal exit (user interrupted with Ctrl+C)
- `1` - Invalid arguments or configuration error
