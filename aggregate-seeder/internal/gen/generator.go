// Package gen turns an inventory and a traffic profile into aggregate documents.
package gen

import (
	"fmt"
	"math"
	"math/rand/v2"
	"slices"
	"sort"
	"time"

	"github.com/TykTechnologies/aggregate-seeder/internal/agg"
	"github.com/TykTechnologies/aggregate-seeder/internal/inventory"
	"github.com/TykTechnologies/aggregate-seeder/internal/profile"
)

type Options struct {
	OrgID         string
	From, To      time.Time
	BucketMinutes int // 60 for hourly documents
	Seed          uint64
	ExpireAt      time.Time
	RunID         string // written to _seed
}

type Generator struct {
	opts    Options
	prof    *profile.Profile
	loc     *time.Location
	diurnal []float64 // mean 1
	weekday []float64 // mean 1
	apis    []*apiModel
}

type apiModel struct {
	api       inventory.API
	share     float64
	beh       profile.Resolved
	codes     []string
	codeW     []float64
	consumers []*consumer
}

// consumer is one source of traffic for an API: a key, or anonymous callers
// of a keyless API.
type consumer struct {
	dims     agg.Dims // Version is filled per cell
	versions []string
	weights  []float64 // consumer share * version share
}

func New(inv *inventory.Inventory, prof *profile.Profile, opts Options) (*Generator, error) {
	if opts.BucketMinutes < 1 || opts.BucketMinutes > 60 || 60%opts.BucketMinutes != 0 {
		return nil, fmt.Errorf("bucket size must divide an hour, got %d minutes", opts.BucketMinutes)
	}
	if !opts.To.After(opts.From) {
		return nil, fmt.Errorf("to must be after from")
	}
	loc, err := time.LoadLocation(prof.Timezone)
	if err != nil {
		return nil, err
	}
	g := &Generator{
		opts:    opts,
		prof:    prof,
		loc:     loc,
		diurnal: meanOne(prof.Diurnal),
		weekday: meanOne(prof.Weekday),
	}

	// Setup randomness is independent of the per-bucket streams so adding a
	// bucket never changes the shape of the model.
	r := rand.New(rand.NewPCG(opts.Seed, 0x5eed))
	apiZipf := meanOne(zipfWeights(r, len(inv.APIs), prof.APIZipf))

	keysByAPI := map[string][]*inventory.Key{}
	for i := range inv.Keys {
		k := &inv.Keys[i]
		for apiID := range k.Access {
			keysByAPI[apiID] = append(keysByAPI[apiID], k)
		}
	}

	var weights []float64
	for i, api := range inv.APIs {
		m := &apiModel{api: api, beh: prof.Resolve(api.ID, api.Name)}
		m.codes, m.codeW = sortedCodes(m.beh.Errors)
		m.consumers = g.consumers(r, api, keysByAPI[api.ID])
		if len(m.consumers) == 0 {
			continue
		}
		w := apiZipf[i]
		if m.beh.Weight > 0 {
			w = m.beh.Weight
		}
		g.apis = append(g.apis, m)
		weights = append(weights, w)
	}
	if len(g.apis) == 0 {
		return nil, fmt.Errorf("no API can receive traffic: need keyless APIs or keys with access rights")
	}
	for i, s := range normalize(weights) {
		g.apis[i].share = s
	}
	return g, nil
}

func (g *Generator) consumers(r *rand.Rand, api inventory.API, keys []*inventory.Key) []*consumer {
	if api.Keyless {
		// Keyless APIs have no session, so no key, policy or session tags.
		c := &consumer{dims: agg.Dims{APIID: api.ID, APIName: api.Name, Tags: g.recordTags(api, nil)}}
		c.versions, c.weights = g.versionSplit(api, nil, 1)
		return []*consumer{c}
	}
	shares := normalize(zipfWeights(r, len(keys), g.prof.ConsumerZipf))
	out := make([]*consumer, 0, len(keys))
	for i, k := range keys {
		c := &consumer{dims: agg.Dims{
			APIID:   api.ID,
			APIName: api.Name,
			KeyID:   k.ID,
			Alias:   k.Alias,
			OauthID: k.OAuthClientID,
			Tags:    g.recordTags(api, k),
		}}
		c.versions, c.weights = g.versionSplit(api, k.Access[api.ID], shares[i])
		out = append(out, c)
	}
	return out
}

// recordTags reproduces the tags the gateway puts on an analytics record
// (handler_success.go, analytics.go), then the pump's trimming and filtering.
func (g *Generator) recordTags(api inventory.API, k *inventory.Key) []string {
	var raw []string
	if k != nil {
		for _, p := range k.Policies {
			raw = append(raw, "pol-"+p)
		}
		if k.DeveloperID != "" {
			raw = append(raw, "dev-"+k.DeveloperID)
		}
		raw = append(raw, k.Tags...)
	}
	raw = append(raw, api.Tags...)
	raw = append(raw, g.prof.ExtraTags...)
	if g.opts.OrgID != "" {
		raw = append(raw, "org-"+g.opts.OrgID)
	}
	raw = append(raw, "api-"+api.ID)

	out := make([]string, 0, len(raw))
	for _, t := range raw {
		if agg.IgnoreTag(t, g.prof.IgnoreTagPrefixes) {
			continue
		}
		if t = agg.TrimTag(t); t != "" {
			out = append(out, t)
		}
	}
	return out
}

// versionSplit decides which analytics versions a consumer's traffic is
// recorded under. allowed holds the definition version names from the key's
// access rights (empty means all).
func (g *Generator) versionSplit(api inventory.API, allowed []string, share float64) ([]string, []float64) {
	versions := []string{inventory.NonVersioned}
	for _, v := range api.Versions {
		if v != inventory.NonVersioned && (len(allowed) == 0 || slices.Contains(allowed, v)) {
			versions = append(versions, v)
		}
	}
	if len(versions) == 1 {
		return versions, []float64{share}
	}
	weights := make([]float64, len(versions))
	weights[0] = share * g.prof.VersionDefaultShare
	for i := 1; i < len(versions); i++ {
		weights[i] = share * (1 - g.prof.VersionDefaultShare) / float64(len(versions)-1)
	}
	return versions, weights
}

// Buckets returns the start of every bucket in [From, To).
func (g *Generator) Buckets() []time.Time {
	size := time.Duration(g.opts.BucketMinutes) * time.Minute
	var out []time.Time
	for t := g.opts.From.UTC().Truncate(size); t.Before(g.opts.To); t = t.Add(size) {
		out = append(out, t)
	}
	return out
}

// Bucket builds the document for the bucket starting at ts, or nil when the
// bucket has no traffic (the pump writes nothing in that case). The result
// depends only on the seed, inventory, profile and ts.
func (g *Generator) Bucket(ts time.Time) *agg.Doc {
	r := rand.New(rand.NewPCG(g.opts.Seed, uint64(ts.Unix())))
	size := time.Duration(g.opts.BucketMinutes) * time.Minute

	local := ts.In(g.loc)
	progress := float64(ts.Sub(g.opts.From)) / float64(g.opts.To.Sub(g.opts.From))
	base := g.prof.DailyRequests / 24 *
		g.diurnal[local.Hour()] *
		g.weekday[int(local.Weekday())] *
		(1 + g.prof.Growth*progress) *
		float64(g.opts.BucketMinutes) / 60

	b := agg.NewBuilder(g.opts.OrgID, ts, g.opts.ExpireAt, g.opts.RunID)
	for _, m := range g.apis {
		traffic, latency := 1.0, 1.0
		errRate, codes, codeW := m.beh.ErrorRate, m.codes, m.codeW
		for i := range g.prof.Incidents {
			in := &g.prof.Incidents[i]
			if !in.Applies(ts, m.api.ID, m.api.Name) {
				continue
			}
			if in.TrafficMultiplier > 0 {
				traffic *= in.TrafficMultiplier
			}
			if in.LatencyMultiplier > 0 {
				latency *= in.LatencyMultiplier
			}
			if in.ErrorRate != nil {
				errRate = *in.ErrorRate
			}
			if in.Errors != nil {
				codes, codeW = sortedCodes(in.Errors)
			}
		}

		lambda := base * m.share * traffic * logNormalNoise(r, g.prof.BucketNoise)
		for _, c := range m.consumers {
			for vi, v := range c.versions {
				hits := poisson(r, lambda*c.weights[vi]*logNormalNoise(r, g.prof.CellNoise))
				if hits == 0 {
					continue
				}
				cell := makeCell(r, ts, size, hits, errRate, codes, codeW, &m.beh, latency)
				d := c.dims
				d.Version = v
				b.Add(cell, d)
			}
		}
	}
	if b.Empty() {
		return nil
	}
	return b.Finish()
}

// makeCell simulates hits requests from one consumer to one API version
// within a bucket, without generating the individual requests.
func makeCell(r *rand.Rand, ts time.Time, size time.Duration, hits int, errRate float64,
	codes []string, codeW []float64, beh *profile.Resolved, latencyMult float64) *agg.Counter {

	c := &agg.Counter{Hits: hits}

	errors := 0
	if len(codes) > 0 {
		errors = binomial(r, hits, errRate)
		for i, n := range multinomial(r, errors, codeW) {
			if n > 0 {
				if c.ErrorMap == nil {
					c.ErrorMap = map[string]int{}
				}
				c.ErrorMap[codes[i]] = n
			}
		}
	}
	c.ErrorTotal = errors
	c.Success = hits - errors

	if med := beh.LatencyMedianMs * latencyMult; med > 0 {
		sigma := beh.LatencySigma
		n := float64(hits)
		mean := med * math.Exp(sigma*sigma/2)
		// The mean of n log-normal samples varies by roughly sd/sqrt(n).
		cv := math.Sqrt(math.Exp(sigma*sigma)-1) / math.Sqrt(n)
		total := n * mean * logNormalNoise(r, min(cv, 1))
		avg := total / n

		lo, hi := avg, avg
		if hits > 1 {
			lo = min(avg, med*math.Exp(sigma*normInv(1/(n+1)))*logNormalNoise(r, 0.1))
			hi = max(avg, med*math.Exp(sigma*normInv(n/(n+1)))*logNormalNoise(r, 0.1))
		}
		oh := beh.GatewayOverheadMs
		c.TotalLatency = int64(math.Round(total))
		c.MinLatency = int64(math.Round(lo))
		c.MaxLatency = int64(math.Round(hi))
		c.TotalUpstreamLatency = max(0, int64(math.Round(total-n*oh)))
		c.MinUpstreamLatency = max(0, int64(math.Round(lo-oh)))
		c.MaxUpstreamLatency = max(0, int64(math.Round(hi-oh)))
		c.TotalRequestTime = float64(c.TotalLatency)
	}

	c.BytesIn = int64(math.Round(beh.BytesIn * float64(hits)))
	c.BytesOut = int64(math.Round(beh.BytesOut * float64(hits)))

	// The last of hits uniformly spread requests lands at U^(1/hits) of the bucket.
	offset := time.Duration(float64(size) * math.Pow(r.Float64(), 1/float64(hits)))
	c.LastTime = ts.Add(min(offset, size-time.Millisecond)).Truncate(time.Millisecond)
	return c
}

func sortedCodes(m map[string]float64) ([]string, []float64) {
	codes := make([]string, 0, len(m))
	for k, w := range m {
		if w > 0 {
			codes = append(codes, k)
		}
	}
	sort.Strings(codes)
	weights := make([]float64, len(codes))
	for i, k := range codes {
		weights[i] = m[k]
	}
	return codes, weights
}

func meanOne(w []float64) []float64 {
	n := normalize(w)
	for i := range n {
		n[i] *= float64(len(n))
	}
	return n
}
