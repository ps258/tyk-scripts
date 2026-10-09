package portal

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"math/rand/v2"
	"net/http"
	"net/url"
	"strings"
	"sync/atomic"
	"time"
)

// Client is a minimal JSON client for the portal admin API (/portal-api) and
// the Dashboard API. Both take the token as the raw Authorization header.
type Client struct {
	base        string
	token       string
	hc          *http.Client
	lockRetries atomic.Int64
}

func NewClient(base, token string, insecure bool) *Client {
	tr := http.DefaultTransport.(*http.Transport).Clone()
	if insecure {
		tr.TLSClientConfig = &tls.Config{InsecureSkipVerify: true}
	}
	return &Client{
		base:  strings.TrimRight(base, "/"),
		token: token,
		hc:    &http.Client{Timeout: 2 * time.Minute, Transport: tr},
	}
}

// HTTPError is a non-2xx response.
type HTTPError struct {
	Method, Path string
	Status       int
	Body         string
}

func (e *HTTPError) Error() string {
	return fmt.Sprintf("%s %s: %d %s", e.Method, e.Path, e.Status, strings.TrimSpace(e.Body))
}

// Do sends body as JSON and decodes the response into out (when non-nil).
// Network errors and 5xx responses are retried a few times. "database is
// locked" errors (a SQLite-backed portal refusing concurrent writes; the
// write is rolled back) are retried for longer with jittered backoff.
func (c *Client) Do(ctx context.Context, method, path string, body, out any) error {
	var payload []byte
	if body != nil {
		var err error
		if payload, err = json.Marshal(body); err != nil {
			return err
		}
	}

	const maxAttempts, maxLockAttempts = 4, 12
	var lastErr error
	for attempt, failures := 0, 0; ; attempt++ {
		if attempt > 0 {
			wait := time.Duration(min(attempt*attempt, 16)) * 250 * time.Millisecond
			wait += time.Duration(rand.Int64N(int64(wait)))
			select {
			case <-time.After(wait):
			case <-ctx.Done():
				return ctx.Err()
			}
		}
		if attempt >= maxLockAttempts || failures >= maxAttempts {
			return lastErr
		}
		req, err := http.NewRequestWithContext(ctx, method, c.base+path, bytes.NewReader(payload))
		if err != nil {
			return err
		}
		req.Header.Set("Authorization", c.token)
		req.Header.Set("Accept", "application/json")
		if body != nil {
			req.Header.Set("Content-Type", "application/json")
		}
		resp, err := c.hc.Do(req)
		if err != nil {
			lastErr = err
			failures++
			continue
		}
		raw, err := io.ReadAll(resp.Body)
		resp.Body.Close()
		if err != nil {
			lastErr = err
			failures++
			continue
		}
		if resp.StatusCode >= 300 && isLocked(raw) {
			lastErr = &HTTPError{method, path, resp.StatusCode, string(raw)}
			c.lockRetries.Add(1)
			continue
		}
		if resp.StatusCode >= 500 {
			lastErr = &HTTPError{method, path, resp.StatusCode, string(raw)}
			failures++
			continue
		}
		if resp.StatusCode >= 300 {
			return &HTTPError{method, path, resp.StatusCode, string(raw)}
		}
		if out != nil && len(bytes.TrimSpace(raw)) > 0 {
			if err := json.Unmarshal(raw, out); err != nil {
				return fmt.Errorf("%s %s: decode response: %w", method, path, err)
			}
		}
		return nil
	}
}

// LockRetries is how many requests were retried because the portal database
// was locked.
func (c *Client) LockRetries() int64 { return c.lockRetries.Load() }

func isLocked(body []byte) bool {
	b := bytes.ToLower(body)
	return bytes.Contains(b, []byte("database is locked")) ||
		bytes.Contains(b, []byte("database table is locked")) ||
		bytes.Contains(b, []byte("sqlite_busy"))
}

// ListAll pages through a portal admin list endpoint. Responses are either a
// bare array or {"data": [...]}.
func ListAll[T any](ctx context.Context, c *Client, path string) ([]T, error) {
	const perPage = 100
	var all []T
	for page := 1; ; page++ {
		q := url.Values{"page": {fmt.Sprint(page)}, "per_page": {fmt.Sprint(perPage)}}
		sep := "?"
		if strings.Contains(path, "?") {
			sep = "&"
		}
		var raw json.RawMessage
		if err := c.Do(ctx, http.MethodGet, path+sep+q.Encode(), nil, &raw); err != nil {
			return nil, err
		}
		var items []T
		if err := json.Unmarshal(raw, &items); err != nil {
			var wrapped struct {
				Data []T `json:"data"`
			}
			if err2 := json.Unmarshal(raw, &wrapped); err2 != nil {
				return nil, fmt.Errorf("GET %s: unexpected list shape: %w", path, err)
			}
			items = wrapped.Data
		}
		all = append(all, items...)
		if len(items) < perPage {
			return all, nil
		}
	}
}
