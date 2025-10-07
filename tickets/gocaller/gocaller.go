package main

import (
	"crypto/tls"
	"flag"
	"fmt"
	"net/http"
	"os"
	"time"
)

func main() {
	// Command line flags
	var (
		url       = flag.String("url", "", "API URL to call (required)")
		threshold = flag.Duration("threshold", 60*time.Millisecond, "Duration threshold of latency in API call for bell warning (e.g., 60ms, 100ms)")
		frequency = flag.Duration("frequency", 1*time.Second, "Frequency of API calls (e.g., 1s, 500ms)")
		timeout   = flag.Duration("timeout", 60*time.Second, "HTTP client timeout duration (e.g., 30s, 5m, 1h)")
	)

	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "Usage: %s [options]\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "\nA program that makes a single call to an API at regular intervals and rings the terminal bell\n")
		fmt.Fprintf(os.Stderr, "when API calls take longer than the specified threshold.\n\n")
		fmt.Fprintf(os.Stderr, "Options:\n")
		flag.PrintDefaults()
		fmt.Fprintf(os.Stderr, "\nExamples:\n")
		fmt.Fprintf(os.Stderr, "  %s -url=https://api.example.com/health\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "  %s -url=https://api.example.com/status -threshold=100ms -frequency=2s\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "  %s -url=https://api.example.com/health -timeout=30s\n", os.Args[0])
	}

	flag.Parse()

	// Validate required parameters
	if *url == "" {
		fmt.Fprintf(os.Stderr, "Error: URL is required\n\n")
		flag.Usage()
		os.Exit(1)
	}

	// Create HTTP client with configurable timeout and skip SSL verification
	client := &http.Client{
		Timeout: *timeout,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: true,
			},
		},
	}

	startTimestamp := time.Now().Format("15:04:05")
	fmt.Printf("[%s] Starting API caller:\n", startTimestamp)
	fmt.Printf("[%s]   URL: %s\n", startTimestamp, *url)
	fmt.Printf("[%s]   Threshold: %v\n", startTimestamp, *threshold)
	fmt.Printf("[%s]   Frequency: %v\n", startTimestamp, *frequency)
	fmt.Printf("[%s]   Timeout: %v\n", startTimestamp, *timeout)
	fmt.Printf("[%s]   Bell will ring if calls take longer than %v\n\n", startTimestamp, *threshold)

	// Create ticker for regular API calls
	ticker := time.NewTicker(*frequency)
	defer ticker.Stop()

	callCount := 0
	slowCallCount := 0

	// Make initial call immediately
	makeAPICall(client, *url, *threshold, &callCount, &slowCallCount)

	// Continue making calls at specified frequency
	for range ticker.C {
		makeAPICall(client, *url, *threshold, &callCount, &slowCallCount)
	}
}

func makeAPICall(client *http.Client, url string, threshold time.Duration, callCount, slowCallCount *int) {
	*callCount++
	currentCallNum := *callCount // Capture the call number for this specific call
	start := time.Now()

	// Create channels for result and timeout
	resultChan := make(chan *http.Response, 1)
	errorChan := make(chan error, 1)
	timeoutChan := time.After(threshold)

	// Start the HTTP request in a goroutine
	go func() {
		resp, err := client.Get(url)
		if err != nil {
			errorChan <- err
		} else {
			resultChan <- resp
		}
	}()

	timestamp := time.Now().Format("15:04:05")
	var resp *http.Response
	var err error

	// Wait for either the result or timeout
	select {
	case resp = <-resultChan:
		// Request completed successfully within threshold
		duration := time.Since(start)
		defer resp.Body.Close()

		statusText := "OK"
		if resp.StatusCode >= 400 {
			statusText = "ERROR"
		}

		// Check if it was actually slow even though it completed within timeout window
		if duration > threshold {
			*slowCallCount++
			fmt.Printf("\a[%s] Call #%d %s (%d) in %v 🔔 SLOW! (slow calls: %d/%d)\n",
				timestamp, currentCallNum, statusText, resp.StatusCode, duration, *slowCallCount, *callCount)
		}

	case err = <-errorChan:
		// Request failed within threshold
		duration := time.Since(start)
		if duration > threshold {
			*slowCallCount++
			fmt.Printf("\a[%s] Call #%d FAILED after %v: %v 🔔 SLOW! (slow calls: %d/%d)\n",
				timestamp, currentCallNum, duration, err, *slowCallCount, *callCount)
		} else {
			fmt.Printf("[%s] Call #%d FAILED after %v: %v (slow calls: %d/%d)\n",
				timestamp, currentCallNum, duration, err, *slowCallCount, *callCount)
		}

	case <-timeoutChan:
		// Threshold exceeded - ring bell immediately
		*slowCallCount++
		fmt.Printf("\a[%s] Call #%d 🔔 SLOW CALL WARNING! (threshold: %v exceeded)\n",
			timestamp, currentCallNum, threshold)

		// Continue waiting for the actual response to complete (but don't block the next call)
		go func() {
			select {
			case resp := <-resultChan:
				duration := time.Since(start)
				resp.Body.Close()
				statusText := "OK"
				if resp.StatusCode >= 400 {
					statusText = "ERROR"
				}
				completionTimestamp := time.Now().Format("15:04:05")
				fmt.Printf("[%s] Call #%d eventually completed: %s (%d) in %v (slow calls: %d/%d)\n",
					completionTimestamp, currentCallNum, statusText, resp.StatusCode, duration, *slowCallCount, *callCount)
			case err := <-errorChan:
				duration := time.Since(start)
				failureTimestamp := time.Now().Format("15:04:05")
				fmt.Printf("[%s] Call #%d eventually failed after %v: %v (slow calls: %d/%d)\n",
					failureTimestamp, currentCallNum, duration, err, *slowCallCount, *callCount)
			}
		}()
	}
}
