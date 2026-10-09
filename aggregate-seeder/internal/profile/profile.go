// Package profile describes the shape of the simulated traffic.
package profile

import (
	"fmt"
	"os"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

type Profile struct {
	// DailyRequests is the average number of requests per day at the start of
	// the range, across all APIs.
	DailyRequests float64 `yaml:"daily_requests"`
	// Growth is the fractional change in volume from the start to the end of
	// the range (0.5 means the last day is 50% busier than the first).
	Growth float64 `yaml:"growth"`
	// Timezone the diurnal and weekday curves are expressed in.
	Timezone string `yaml:"timezone"`
	// Diurnal holds 24 relative weights, one per hour of the day.
	Diurnal []float64 `yaml:"diurnal"`
	// Weekday holds 7 relative weights, Sunday first.
	Weekday []float64 `yaml:"weekday"`
	// BucketNoise is the log-normal sigma applied to each API's volume per bucket.
	BucketNoise float64 `yaml:"bucket_noise"`
	// CellNoise is the log-normal sigma applied per key/API/version per bucket.
	CellNoise float64 `yaml:"cell_noise"`
	// APIZipf and ConsumerZipf set how unevenly traffic is spread across APIs
	// and across the keys of an API (0 = even). Ranks are assigned randomly
	// from the seed; explicit API weights override the API ranking.
	APIZipf      float64 `yaml:"api_zipf"`
	ConsumerZipf float64 `yaml:"consumer_zipf"`
	// VersionDefaultShare is the share of a versioned API's traffic that does
	// not select a version (recorded as "Non Versioned").
	VersionDefaultShare float64 `yaml:"version_default_share"`

	Defaults  APIProfile    `yaml:"defaults"`
	APIs      []APIOverride `yaml:"apis"`
	Incidents []Incident    `yaml:"incidents"`

	// ExtraTags are added to every record, e.g. the gateway's
	// db_app_conf_options.tags when node_is_segmented, or "tyk-hybrid-rpc".
	ExtraTags []string `yaml:"extra_tags"`
	// IgnoreTagPrefixes mirrors the pump's ignore_tag_prefix_list.
	IgnoreTagPrefixes []string `yaml:"ignore_tag_prefixes"`
}

// APIProfile holds per-API behaviour. Unset fields fall back to Defaults.
type APIProfile struct {
	Weight            *float64           `yaml:"weight"`
	ErrorRate         *float64           `yaml:"error_rate"`
	Errors            map[string]float64 `yaml:"errors"`
	LatencyMedianMs   *float64           `yaml:"latency_median_ms"`
	LatencySigma      *float64           `yaml:"latency_sigma"`
	GatewayOverheadMs *float64           `yaml:"gateway_overhead_ms"`
	BytesIn           *float64           `yaml:"bytes_in"`
	BytesOut          *float64           `yaml:"bytes_out"`
}

// APIOverride applies to the API whose ID or name equals Match.
type APIOverride struct {
	Match      string `yaml:"match"`
	APIProfile `yaml:",inline"`
}

// Incident changes behaviour for some APIs (all when APIs is empty) between From and To.
type Incident struct {
	From              time.Time          `yaml:"from"`
	To                time.Time          `yaml:"to"`
	APIs              []string           `yaml:"apis"`
	TrafficMultiplier float64            `yaml:"traffic_multiplier"`
	ErrorRate         *float64           `yaml:"error_rate"`
	Errors            map[string]float64 `yaml:"errors"`
	LatencyMultiplier float64            `yaml:"latency_multiplier"`
}

// Resolved is the effective behaviour of one API.
type Resolved struct {
	Weight            float64 // 0 = use the Zipf ranking
	ErrorRate         float64
	Errors            map[string]float64
	LatencyMedianMs   float64
	LatencySigma      float64
	GatewayOverheadMs float64
	BytesIn           float64
	BytesOut          float64
}

func f(v float64) *float64 { return &v }

// Default returns the built-in profile.
func Default() *Profile {
	return &Profile{
		DailyRequests: 2_000_000,
		Growth:        0.3,
		Timezone:      "UTC",
		// Quiet overnight, ramp from 06:00, busiest 09:00-17:00.
		Diurnal: []float64{
			0.25, 0.2, 0.18, 0.18, 0.2, 0.3, 0.55, 0.9, 1.3, 1.6, 1.7, 1.7,
			1.6, 1.65, 1.7, 1.65, 1.5, 1.3, 1.0, 0.8, 0.65, 0.5, 0.4, 0.3,
		},
		Weekday:             []float64{0.55, 1.1, 1.15, 1.15, 1.1, 1.05, 0.6},
		BucketNoise:         0.15,
		CellNoise:           0.25,
		APIZipf:             1.0,
		ConsumerZipf:        0.8,
		VersionDefaultShare: 0.7,
		Defaults: APIProfile{
			ErrorRate:         f(0.02),
			Errors:            map[string]float64{"401": 1, "403": 3, "404": 2, "429": 1, "499": 0.5, "500": 1, "502": 0.3, "504": 0.5},
			LatencyMedianMs:   f(80),
			LatencySigma:      f(0.9),
			GatewayOverheadMs: f(2),
			BytesIn:           f(0),
			BytesOut:          f(0),
		},
	}
}

// Load reads a YAML profile over the defaults. An empty path returns the defaults.
func Load(path string) (*Profile, error) {
	p := Default()
	if path != "" {
		b, err := os.ReadFile(path)
		if err != nil {
			return nil, err
		}
		// yaml.v3 merges into existing maps; an errors map given in the file
		// should replace the built-in one rather than add to it.
		var probe struct {
			Defaults struct {
				Errors map[string]float64 `yaml:"errors"`
			} `yaml:"defaults"`
		}
		if err := yaml.Unmarshal(b, &probe); err == nil && probe.Defaults.Errors != nil {
			p.Defaults.Errors = nil
		}
		dec := yaml.NewDecoder(strings.NewReader(string(b)))
		dec.KnownFields(true)
		if err := dec.Decode(p); err != nil {
			return nil, fmt.Errorf("parse %s: %w", path, err)
		}
	}
	return p, p.validate()
}

func (p *Profile) validate() error {
	if p.DailyRequests <= 0 {
		return fmt.Errorf("daily_requests must be > 0")
	}
	d := p.Defaults
	if d.ErrorRate == nil || d.LatencyMedianMs == nil || d.LatencySigma == nil ||
		d.GatewayOverheadMs == nil || d.BytesIn == nil || d.BytesOut == nil {
		return fmt.Errorf("defaults: every numeric field must be set")
	}
	if len(p.Diurnal) != 24 {
		return fmt.Errorf("diurnal must have 24 entries, has %d", len(p.Diurnal))
	}
	if len(p.Weekday) != 7 {
		return fmt.Errorf("weekday must have 7 entries, has %d", len(p.Weekday))
	}
	if _, err := time.LoadLocation(p.Timezone); err != nil {
		return fmt.Errorf("timezone: %w", err)
	}
	if p.VersionDefaultShare < 0 || p.VersionDefaultShare > 1 {
		return fmt.Errorf("version_default_share must be between 0 and 1")
	}
	for i, in := range p.Incidents {
		if !in.To.After(in.From) {
			return fmt.Errorf("incident %d: to must be after from", i)
		}
	}
	return nil
}

// Resolve returns the effective behaviour for an API, applying the first
// override whose match equals its ID or name.
func (p *Profile) Resolve(apiID, apiName string) Resolved {
	d := p.Defaults
	r := Resolved{
		ErrorRate:         *d.ErrorRate,
		Errors:            d.Errors,
		LatencyMedianMs:   *d.LatencyMedianMs,
		LatencySigma:      *d.LatencySigma,
		GatewayOverheadMs: *d.GatewayOverheadMs,
		BytesIn:           *d.BytesIn,
		BytesOut:          *d.BytesOut,
	}
	for _, o := range p.APIs {
		if o.Match != apiID && o.Match != apiName {
			continue
		}
		set := func(dst *float64, src *float64) {
			if src != nil {
				*dst = *src
			}
		}
		set(&r.Weight, o.Weight)
		set(&r.ErrorRate, o.ErrorRate)
		set(&r.LatencyMedianMs, o.LatencyMedianMs)
		set(&r.LatencySigma, o.LatencySigma)
		set(&r.GatewayOverheadMs, o.GatewayOverheadMs)
		set(&r.BytesIn, o.BytesIn)
		set(&r.BytesOut, o.BytesOut)
		if o.Errors != nil {
			r.Errors = o.Errors
		}
		break
	}
	return r
}

// Applies reports whether the incident affects the API at time t.
func (in *Incident) Applies(t time.Time, apiID, apiName string) bool {
	if t.Before(in.From) || !t.Before(in.To) {
		return false
	}
	if len(in.APIs) == 0 {
		return true
	}
	for _, m := range in.APIs {
		if m == apiID || m == apiName {
			return true
		}
	}
	return false
}
