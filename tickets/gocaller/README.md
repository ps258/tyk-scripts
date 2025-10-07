# API Caller

A Go program that calls an API at regular intervals and warns when API calls take longer than a specified threshold.

## Features

- Configurable API URL, call frequency, and timeout threshold via command-line flags
- Displays detailed timing information for each call
- Tracks statistics of slow calls vs total calls
- Proper error handling for network issues
- Clean, readable output with timestamps

## Building

```bash
go build -o gocaller gocaller.go
```

## Usage

```bash
./gocaller -url=<API_URL> [options]
```

### Options

- `-url string`: API URL to call (required)
- `-threshold duration`: Duration threshold for bell warning (default: 60ms)
  - Examples: `60ms`, `100ms`, `1s`
- `-frequency duration`: Frequency of API calls (default: 1s)
  - Examples: `1s`, `500ms`, `2s`
- `-timeout duration`: The overall timeout of an API call (default: 60s)

### Examples

```bash
# Basic usage - call API every second, bell if > 60ms
./gocaller -url=https://api.example.com/health

# Custom threshold and frequency
./gocaller -url=https://api.example.com/status -threshold=100ms -frequency=2s

# High frequency monitoring
./gocaller -url=http://localhost:8080/ping -threshold=50ms -frequency=500ms
```

## Output

The program displays:
- Timestamp of each call
- Call number and HTTP status
- Response time
- Bell indicator (🔔) for slow calls
- Running count of slow calls vs total calls

Example output:
```
Starting API caller:
  URL: https://api.example.com/health
  Threshold: 60ms
  Frequency: 1s

[14:30:15] Call #1 OK (200) in 45ms (slow calls: 0/1)
[14:30:16] Call #2 OK (200) in 120ms 🔔 SLOW! (slow calls: 1/2)
[14:30:17] Call #3 FAILED after 5s: Get "https://api.example.com/health": context deadline exceeded 🔔 SLOW! (slow calls: 2/3)
```

## Notes

- The program makes an initial call immediately, then continues at the specified frequency
- Press Ctrl+C to stop the program
