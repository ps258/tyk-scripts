package main

import (
	"context"
	"crypto/tls"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
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

// initTracer initializes OpenTelemetry with gRPC OTLP exporter
func initTracer(ctx context.Context, collectorEndpoint, serviceName, version string) (*sdktrace.TracerProvider, error) {
	// Create gRPC connection to OTEL collector
	conn, err := grpc.DialContext(ctx, collectorEndpoint,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithBlock(),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create gRPC connection to collector: %w", err)
	}

	// Create OTLP trace exporter
	traceExporter, err := otlptracegrpc.New(ctx,
		otlptracegrpc.WithGRPCConn(conn),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create trace exporter: %w", err)
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
func (c *APIClient) CallAPI(ctx context.Context, method, url string, body io.Reader) (*http.Response, error) {
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
func (c *APIClient) BusinessLogic(baseCtx context.Context, apiURL string, numCalls int, delayBetweenCalls time.Duration) error {
	log.Printf("Starting business logic operation with %d calls and %v delay between calls...", numCalls, delayBetweenCalls)

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

		log.Printf("Making GET request %d/%d to %s", i, numCalls, apiURL)
		resp, err := c.CallAPI(callCtx, "GET", apiURL, nil)
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
	collectorEndpoint := flag.String("otel-endpoint", "", "OpenTelemetry collector gRPC endpoint (required)")
	apiURL := flag.String("api-url", "", "API URL to call (required)")
	serviceName := flag.String("service-name", defaultServiceName, "Service name for tracing (default: "+defaultServiceName+")")
	version := flag.String("service-version", serviceVersion, "Service version for tracing (default: "+serviceVersion+")")
	numCalls := flag.Int("num-calls", 1, "Number of API calls to make (default: 1)")
	delayBetweenCalls := flag.Duration("delay", 0, "Delay between API calls (e.g., 1s, 500ms, 2m) (default: 0)")

	// Parse command-line flags
	flag.Parse()

	// Validate required parameters
	if *collectorEndpoint == "" {
		log.Fatal("Error: -otel-endpoint parameter is required")
	}
	if *apiURL == "" {
		log.Fatal("Error: -api-url parameter is required")
	}

	log.Printf("Initializing OpenTelemetry with collector endpoint: %s", *collectorEndpoint)

	// Initialize OpenTelemetry
	tp, err := initTracer(ctx, *collectorEndpoint, *serviceName, *version)
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

	// Create API client
	client := NewAPIClient(*serviceName)

	// Execute business logic - each call will create its own independent trace
	if err := client.BusinessLogic(ctx, *apiURL, *numCalls, *delayBetweenCalls); err != nil {
		log.Fatalf("Business logic failed: %v", err)
	}

	log.Println("Operation completed successfully!")

	// Give some time for traces to be exported
	time.Sleep(2 * time.Second)
}
