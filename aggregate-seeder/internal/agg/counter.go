// Package agg models the Tyk Pump Mongo aggregate document
// (see tyk-pump/analytics/aggregate.go) and builds it from pre-aggregated cells.
package agg

import (
	b64 "encoding/base64"
	"sort"
	"strings"
	"time"
)

// ErrorData mirrors analytics.ErrorData.
type ErrorData struct {
	Code  string `bson:"code" json:"code"`
	Count int    `bson:"count" json:"count"`
}

// Counter mirrors analytics.Counter as the pump writes it into a dimension map
// (e.g. apiid.<id>). errormap is only present once an error has been counted.
type Counter struct {
	BytesIn              int64          `bson:"bytesin" json:"bytesin"`
	BytesOut             int64          `bson:"bytesout" json:"bytesout"`
	ClosedConnections    int64          `bson:"closedconnections" json:"closedconnections"`
	ErrorTotal           int            `bson:"errortotal" json:"errortotal"`
	Hits                 int            `bson:"hits" json:"hits"`
	HumanIdentifier      string         `bson:"humanidentifier" json:"humanidentifier"`
	Identifier           string         `bson:"identifier" json:"identifier"`
	LastTime             time.Time      `bson:"lasttime" json:"lasttime"`
	MaxLatency           int64          `bson:"maxlatency" json:"maxlatency"`
	MaxUpstreamLatency   int64          `bson:"maxupstreamlatency" json:"maxupstreamlatency"`
	MinLatency           int64          `bson:"minlatency" json:"minlatency"`
	MinUpstreamLatency   int64          `bson:"minupstreamlatency" json:"minupstreamlatency"`
	OpenConnections      int64          `bson:"openconnections" json:"openconnections"`
	Success              int            `bson:"success" json:"success"`
	TotalLatency         int64          `bson:"totallatency" json:"totallatency"`
	TotalRequestTime     float64        `bson:"totalrequesttime" json:"totalrequesttime"`
	TotalUpstreamLatency int64          `bson:"totalupstreamlatency" json:"totalupstreamlatency"`
	ErrorList            []ErrorData    `bson:"errorlist" json:"errorlist"`
	Latency              float64        `bson:"latency" json:"latency"`
	RequestTime          float64        `bson:"requesttime" json:"requesttime"`
	UpstreamLatency      float64        `bson:"upstreamlatency" json:"upstreamlatency"`
	ErrorMap             map[string]int `bson:"errormap,omitempty" json:"errormap,omitempty"`
}

// ListCounter is the same data as it appears in the lists.* arrays, where the
// pump always writes errormap (possibly empty).
type ListCounter struct {
	BytesIn              int64          `bson:"bytesin" json:"bytesin"`
	BytesOut             int64          `bson:"bytesout" json:"bytesout"`
	ClosedConnections    int64          `bson:"closedconnections" json:"closedconnections"`
	ErrorTotal           int            `bson:"errortotal" json:"errortotal"`
	Hits                 int            `bson:"hits" json:"hits"`
	HumanIdentifier      string         `bson:"humanidentifier" json:"humanidentifier"`
	Identifier           string         `bson:"identifier" json:"identifier"`
	LastTime             time.Time      `bson:"lasttime" json:"lasttime"`
	MaxLatency           int64          `bson:"maxlatency" json:"maxlatency"`
	MaxUpstreamLatency   int64          `bson:"maxupstreamlatency" json:"maxupstreamlatency"`
	MinLatency           int64          `bson:"minlatency" json:"minlatency"`
	MinUpstreamLatency   int64          `bson:"minupstreamlatency" json:"minupstreamlatency"`
	OpenConnections      int64          `bson:"openconnections" json:"openconnections"`
	Success              int            `bson:"success" json:"success"`
	TotalLatency         int64          `bson:"totallatency" json:"totallatency"`
	TotalRequestTime     float64        `bson:"totalrequesttime" json:"totalrequesttime"`
	TotalUpstreamLatency int64          `bson:"totalupstreamlatency" json:"totalupstreamlatency"`
	ErrorList            []ErrorData    `bson:"errorlist" json:"errorlist"`
	Latency              float64        `bson:"latency" json:"latency"`
	RequestTime          float64        `bson:"requesttime" json:"requesttime"`
	UpstreamLatency      float64        `bson:"upstreamlatency" json:"upstreamlatency"`
	ErrorMap             map[string]int `bson:"errormap" json:"errormap"`
}

// merge adds cell into c, following analytics.incrementOrSetUnit. The pump
// only lowers the minimum for successful requests; at cell granularity we
// lower it for any cell that contains at least one success.
func (c *Counter) merge(cell *Counter) {
	if c.Hits == 0 {
		id, human := c.Identifier, c.HumanIdentifier
		*c = *cell
		c.Identifier, c.HumanIdentifier = id, human
		c.ErrorMap = nil
		c.ErrorList = nil
		for k, v := range cell.ErrorMap {
			c.addError(k, v)
		}
		return
	}

	c.Hits += cell.Hits
	c.Success += cell.Success
	c.ErrorTotal += cell.ErrorTotal
	for k, v := range cell.ErrorMap {
		c.addError(k, v)
	}
	c.TotalRequestTime += cell.TotalRequestTime
	c.TotalLatency += cell.TotalLatency
	c.TotalUpstreamLatency += cell.TotalUpstreamLatency
	c.BytesIn += cell.BytesIn
	c.BytesOut += cell.BytesOut

	c.MaxLatency = max(c.MaxLatency, cell.MaxLatency)
	c.MaxUpstreamLatency = max(c.MaxUpstreamLatency, cell.MaxUpstreamLatency)
	if cell.Success > 0 {
		c.MinLatency = min(c.MinLatency, cell.MinLatency)
		c.MinUpstreamLatency = min(c.MinUpstreamLatency, cell.MinUpstreamLatency)
	}
	if cell.LastTime.After(c.LastTime) {
		c.LastTime = cell.LastTime
	}
}

func (c *Counter) addError(code string, n int) {
	if n == 0 {
		return
	}
	if c.ErrorMap == nil {
		c.ErrorMap = make(map[string]int)
	}
	c.ErrorMap[code] += n
}

// errorSlice returns the share of cell attributable to n requests that failed
// with code. The pump feeds each failed request into errors.<code>; at cell
// granularity latency totals are apportioned by request count.
func (c *Counter) errorSlice(code string, n int) *Counter {
	frac := float64(n) / float64(c.Hits)
	return &Counter{
		Hits:                 n,
		ErrorTotal:           n,
		ErrorMap:             map[string]int{code: n},
		TotalRequestTime:     float64(int64(c.TotalRequestTime * frac)),
		TotalLatency:         int64(float64(c.TotalLatency) * frac),
		TotalUpstreamLatency: int64(float64(c.TotalUpstreamLatency) * frac),
		BytesIn:              int64(float64(c.BytesIn) * frac),
		BytesOut:             int64(float64(c.BytesOut) * frac),
		MaxLatency:           c.MaxLatency,
		MaxUpstreamLatency:   c.MaxUpstreamLatency,
		MinLatency:           c.MinLatency,
		MinUpstreamLatency:   c.MinUpstreamLatency,
		LastTime:             c.LastTime,
	}
}

// finalize computes the fields the pump sets in AsTimeUpdate.
func (c *Counter) finalize() {
	if c.Hits > 0 {
		h := float64(c.Hits)
		c.RequestTime = c.TotalRequestTime / h
		c.Latency = float64(c.TotalLatency) / h
		c.UpstreamLatency = float64(c.TotalUpstreamLatency) / h
	}
	c.ErrorList = make([]ErrorData, 0, len(c.ErrorMap))
	for k, v := range c.ErrorMap {
		c.ErrorList = append(c.ErrorList, ErrorData{Code: k, Count: v})
	}
	sort.SliceStable(c.ErrorList, func(i, j int) bool { return c.ErrorList[i].Code < c.ErrorList[j].Code })
}

func (c *Counter) asListItem() ListCounter {
	l := ListCounter(*c)
	if l.ErrorMap == nil {
		l.ErrorMap = map[string]int{}
	}
	return l
}

// VersionKey is the key the pump uses under versions.* (analytics.doHash).
func VersionKey(apiID, version string) string {
	return strings.TrimRight(b64.StdEncoding.EncodeToString([]byte(apiID+":"+version)), "=")
}

// TrimTag mirrors analytics.TrimTag.
func TrimTag(tag string) string {
	return strings.ReplaceAll(strings.TrimSpace(tag), ".", "")
}

// IgnoreTag mirrors analytics.ignoreTag: key-* is always dropped.
func IgnoreTag(tag string, prefixes []string) bool {
	if strings.HasPrefix(tag, "key-") {
		return true
	}
	for _, p := range prefixes {
		if strings.HasPrefix(tag, p) {
			return true
		}
	}
	return false
}
