package main

import (
	"bytes"
	"context"
	"crypto/tls"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.17.0"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

const (
	defaultServiceName = "api-client-service"
	serviceVersion     = "1.0.0"
)

// headerFlags is a custom type to support multiple -H/--header flags
type headerFlags []string

func (h *headerFlags) String() string {
	return strings.Join(*h, ", ")
}

func (h *headerFlags) Set(value string) error {
	*h = append(*h, value)
	return nil
}

// parseHeaders parses a comma-separated list of key=value pairs into a map
func parseHeaders(headerStr string) map[string]string {
	headers := make(map[string]string)
	if headerStr == "" {
		return headers
	}

	pairs := strings.Split(headerStr, ",")
	for _, pair := range pairs {
		kv := strings.SplitN(strings.TrimSpace(pair), "=", 2)
		if len(kv) == 2 {
			key := strings.TrimSpace(kv[0])
			value := strings.TrimSpace(kv[1])
			headers[key] = value
		}
	}
	return headers
}

// parseHeaderFlags parses header strings in the format "Key: Value" or "Key=Value" into a map
func parseHeaderFlags(headerList []string) map[string]string {
	headers := make(map[string]string)
	if len(headerList) == 0 {
		return headers
	}

	for _, header := range headerList {
		// Support both "Key: Value" (curl style) and "Key=Value" formats
		var key, value string
		if strings.Contains(header, ":") {
			parts := strings.SplitN(header, ":", 2)
			if len(parts) == 2 {
				key = strings.TrimSpace(parts[0])
				value = strings.TrimSpace(parts[1])
			}
		} else if strings.Contains(header, "=") {
			parts := strings.SplitN(header, "=", 2)
			if len(parts) == 2 {
				key = strings.TrimSpace(parts[0])
				value = strings.TrimSpace(parts[1])
			}
		}

		if key != "" {
			headers[key] = value
		}
	}
	return headers
}

// initTracer initializes OpenTelemetry with OTLP exporter (gRPC or HTTP)
func initTracer(ctx context.Context, collectorEndpoint, protocol, serviceName, version, headersStr string) (*sdktrace.TracerProvider, error) {
	var traceExporter sdktrace.SpanExporter
	var err error

	switch protocol {
	case "grpc":
		// Create gRPC connection to OTEL collector
		conn, err := grpc.DialContext(ctx, collectorEndpoint,
			grpc.WithTransportCredentials(insecure.NewCredentials()),
			grpc.WithBlock(),
		)
		if err != nil {
			return nil, fmt.Errorf("failed to create gRPC connection to collector: %w", err)
		}

		// Create OTLP trace exporter for gRPC
		traceExporter, err = otlptracegrpc.New(ctx,
			otlptracegrpc.WithGRPCConn(conn),
		)
		if err != nil {
			return nil, fmt.Errorf("failed to create gRPC trace exporter: %w", err)
		}

	case "http", "https":
		// Parse headers for HTTP/HTTPS requests
		headers := parseHeaders(headersStr)

		// Create OTLP trace exporter for HTTP/HTTPS
		options := []otlptracehttp.Option{
			otlptracehttp.WithEndpoint(collectorEndpoint),
		}

		// Use insecure connection only for HTTP protocol
		if protocol == "http" {
			options = append(options, otlptracehttp.WithInsecure())
		}
		// For HTTPS, the exporter will use secure connection by default

		// Add headers if provided
		if len(headers) > 0 {
			options = append(options, otlptracehttp.WithHeaders(headers))
		}

		traceExporter, err = otlptracehttp.New(ctx, options...)
		if err != nil {
			return nil, fmt.Errorf("failed to create %s trace exporter: %w", strings.ToUpper(protocol), err)
		}

	default:
		return nil, fmt.Errorf("unsupported protocol: %s (supported: grpc, http, https)", protocol)
	}

	// Create resource with service information
	res, err := resource.New(ctx,
		resource.WithAttributes(
			semconv.ServiceName(serviceName),
			semconv.ServiceVersion(version),
			semconv.ServiceInstanceID("instance-1"),
		),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create resource: %w", err)
	}

	// Create trace provider
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(traceExporter),
		sdktrace.WithResource(res),
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
	)

	// Set global trace provider and propagator
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},
		propagation.Baggage{},
	))

	return tp, nil
}

// APIClient represents our HTTP client with tracing capabilities
type APIClient struct {
	httpClient *http.Client
	tracer     trace.Tracer
}

// NewAPIClient creates a new API client with OpenTelemetry instrumentation
func NewAPIClient(serviceName string) *APIClient {
	// Create custom transport with insecure skip verify
	transport := &http.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
	}

	// Create HTTP client with OTEL instrumentation and insecure skip verify
	client := &http.Client{
		Transport: otelhttp.NewTransport(transport),
		Timeout:   30 * time.Second,
	}

	tracer := otel.Tracer(serviceName)

	return &APIClient{
		httpClient: client,
		tracer:     tracer,
	}
}

// CallAPI makes an HTTP request to the specified API with tracing
func (c *APIClient) CallAPI(ctx context.Context, method, url string, body io.Reader, customHeaders map[string]string) (*http.Response, error) {
	// Create a span for the API call
	ctx, span := c.tracer.Start(ctx, fmt.Sprintf("API Call: %s %s", method, url))
	defer span.End()

	// Add attributes to the span
	span.SetAttributes(
		attribute.String("http.method", method),
		attribute.String("http.url", url),
		attribute.String("component", "http-client"),
	)

	// Create HTTP request
	req, err := http.NewRequestWithContext(ctx, method, url, body)
	if err != nil {
		span.RecordError(err)
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set content type if body is provided
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	// Add custom headers to the request
	for key, value := range customHeaders {
		req.Header.Set(key, value)
	}

	// The otelhttp.Transport will automatically inject tracing headers
	// including traceparent, tracestate, etc.

	// Make the HTTP request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		span.RecordError(err)
		span.SetAttributes(attribute.String("error", err.Error()))
		return nil, fmt.Errorf("failed to make request: %w", err)
	}

	// Add response attributes to span
	span.SetAttributes(
		attribute.Int("http.status_code", resp.StatusCode),
		attribute.String("http.status", resp.Status),
	)

	// Mark span as error if status code indicates an error
	if resp.StatusCode >= 400 {
		span.SetAttributes(attribute.Bool("error", true))
	}

	return resp, nil
}

// BusinessLogic represents some business logic that calls external APIs
// Each API call will create its own independent trace
func (c *APIClient) BusinessLogic(baseCtx context.Context, apiURL string, numCalls int, delayBetweenCalls time.Duration, customHeaders map[string]string, requestData []byte) error {
	log.Printf("Starting business logic operation with %d calls and %v delay between calls...", numCalls, delayBetweenCalls)

	// Determine HTTP method based on whether data is provided
	method := "GET"
	if len(requestData) > 0 {
		method = "POST"
	}

	for i := 1; i <= numCalls; i++ {
		// Create a new root context for each API call to ensure separate traces
		// This creates independent traces instead of child spans
		callCtx, callSpan := c.tracer.Start(context.Background(), fmt.Sprintf("Independent API Call %d/%d", i, numCalls))

		callSpan.SetAttributes(
			attribute.Int("call.number", i),
			attribute.Int("call.total", numCalls),
			attribute.String("operation", "fetch-user-data"),
			attribute.String("api.endpoint", apiURL),
			attribute.String("delay_between_calls", delayBetweenCalls.String()),
		)

		// Prepare request body if data is provided
		var body io.Reader
		if len(requestData) > 0 {
			body = bytes.NewReader(requestData)
			callSpan.SetAttributes(attribute.Int("request.body.size", len(requestData)))
		}

		log.Printf("Making %s request %d/%d to %s", method, i, numCalls, apiURL)
		resp, err := c.CallAPI(callCtx, method, apiURL, body, customHeaders)
		if err != nil {
			callSpan.RecordError(err)
			callSpan.End()
			log.Printf("Failed to call API on attempt %d: %v", i, err)
			continue // Continue with next call instead of failing completely
		}

		// Read response body
		bodyBytes, err := io.ReadAll(resp.Body)
		resp.Body.Close()
		if err != nil {
			callSpan.RecordError(err)
			callSpan.End()
			log.Printf("Failed to read response on attempt %d: %v", i, err)
			continue // Continue with next call instead of failing completely
		}

		callSpan.SetAttributes(
			attribute.Int("response.size", len(bodyBytes)),
			attribute.Bool("api.success", resp.StatusCode < 400),
		)

		log.Printf("API Call %d/%d - Response Status: %s", i, numCalls, resp.Status)
		log.Printf("API Call %d/%d - Response Body: %s", i, numCalls, string(bodyBytes))

		callSpan.End()

		// Add delay between calls (except after the last call)
		if i < numCalls && delayBetweenCalls > 0 {
			log.Printf("Waiting %v before next call...", delayBetweenCalls)
			time.Sleep(delayBetweenCalls)
		}
	}

	return nil
}

func main() {
	ctx := context.Background()

	// Define command-line flags
	var apiHeaders headerFlags
	collectorEndpoint := flag.String("otel-endpoint", "", "OpenTelemetry collector endpoint (required)")
	protocol := flag.String("otel-protocol", "grpc", "Protocol to use for OTEL collector (grpc, http, or https) (default: grpc)")
	headers := flag.String("otel-headers", "", "HTTP headers for OTEL collector (HTTP only, format: key1=value1,key2=value2)")
	apiURL := flag.String("api-url", "", "API URL to call (required)")
	serviceName := flag.String("service-name", defaultServiceName, "Service name for tracing (default: "+defaultServiceName+")")
	version := flag.String("service-version", serviceVersion, "Service version for tracing (default: "+serviceVersion+")")
	numCalls := flag.Int("num-calls", 1, "Number of API calls to make (default: 1)")
	delayBetweenCalls := flag.Duration("delay", 0, "Delay between API calls (e.g., 1s, 500ms, 2m) (default: 0)")
	dataFile := flag.String("D", "", "File containing data to send with requests (will use POST method)")
	flag.Var(&apiHeaders, "H", "HTTP header for API requests (format: 'Key: Value' or 'Key=Value'). Can be specified multiple times.")
	flag.Var(&apiHeaders, "header", "HTTP header for API requests (format: 'Key: Value' or 'Key=Value'). Can be specified multiple times.")

	// Parse command-line flags
	flag.Parse()

	// Validate required parameters
	if *collectorEndpoint == "" {
		log.Fatal("Error: -otel-endpoint parameter is required")
	}
	if *apiURL == "" {
		log.Fatal("Error: -api-url parameter is required")
	}

	// Validate protocol parameter
	if *protocol != "grpc" && *protocol != "http" && *protocol != "https" {
		log.Fatal("Error: -otel-protocol must be either 'grpc', 'http', or 'https'")
	}

	// Read data file if provided
	var requestData []byte
	if *dataFile != "" {
		var err error
		requestData, err = os.ReadFile(*dataFile)
		if err != nil {
			log.Fatalf("Error: failed to read data file '%s': %v", *dataFile, err)
		}
		log.Printf("Loaded %d bytes from data file: %s", len(requestData), *dataFile)
	}

	// Log initialization details
	if *protocol == "http" && *headers != "" {
		log.Printf("Initializing OpenTelemetry with collector endpoint: %s (protocol: %s, headers: %s)", *collectorEndpoint, *protocol, *headers)
	} else {
		log.Printf("Initializing OpenTelemetry with collector endpoint: %s (protocol: %s)", *collectorEndpoint, *protocol)
	}

	// Initialize OpenTelemetry
	tp, err := initTracer(ctx, *collectorEndpoint, *protocol, *serviceName, *version, *headers)
	if err != nil {
		log.Fatalf("Failed to initialize tracer: %v", err)
	}

	// Ensure all spans are flushed before program exits
	defer func() {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := tp.Shutdown(ctx); err != nil {
			log.Printf("Error shutting down tracer provider: %v", err)
		}
	}()

	// Parse API headers
	customHeaders := parseHeaderFlags(apiHeaders)
	if len(customHeaders) > 0 {
		log.Printf("Using custom API headers: %v", customHeaders)
	}

	// Create API client
	client := NewAPIClient(*serviceName)

	// Execute business logic - each call will create its own independent trace
	if err := client.BusinessLogic(ctx, *apiURL, *numCalls, *delayBetweenCalls, customHeaders, requestData); err != nil {
		log.Fatalf("Business logic failed: %v", err)
	}

	log.Println("Operation completed successfully!")

	// Give some time for traces to be exported
	time.Sleep(2 * time.Second)
}
