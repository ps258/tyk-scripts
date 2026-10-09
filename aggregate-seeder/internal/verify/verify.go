// Package verify checks the internal consistency of aggregate documents.
package verify

import (
	"fmt"
	"math"
	"strings"

	"github.com/TykTechnologies/aggregate-seeder/internal/agg"
)

// Issue is one failed check.
type Issue struct {
	Rule   string
	Detail string
}

// Doc returns every consistency problem in doc.
func Doc(doc *agg.Doc) []Issue {
	var out []Issue
	fail := func(rule, format string, args ...any) {
		out = append(out, Issue{Rule: rule, Detail: fmt.Sprintf(format, args...)})
	}

	ts := doc.TimeStamp.UTC()
	if doc.TimeID != (agg.TimeID{Year: ts.Year(), Month: int(ts.Month()), Day: ts.Day(), Hour: ts.Hour()}) {
		fail("timeid", "timeid %+v does not match timestamp %s", doc.TimeID, ts)
	}

	checkCounter("total", &doc.Total, fail)
	dims := []struct {
		name string
		m    map[string]*agg.Counter
		list []agg.ListCounter
	}{
		{"apiid", doc.APIID, doc.Lists.APIID},
		{"apikeys", doc.APIKeys, doc.Lists.APIKeys},
		{"errors", doc.Errors, doc.Lists.Errors},
		{"versions", doc.Versions, doc.Lists.Versions},
		{"oauthids", doc.OauthIDs, doc.Lists.OauthIDs},
		{"tags", doc.Tags, doc.Lists.Tags},
	}
	for _, d := range dims {
		for k, c := range d.m {
			checkCounter(d.name+"."+k, c, fail)
		}
		checkList(d.name, d.m, d.list, fail)
	}

	if s := sumHits(doc.APIID); s != doc.Total.Hits {
		fail("total=sum(apiid)", "total.hits %d, sum of apiid hits %d", doc.Total.Hits, s)
	}
	if s := sumHits(doc.Versions); s != doc.Total.Hits {
		fail("total=sum(versions)", "total.hits %d, sum of versions hits %d", doc.Total.Hits, s)
	}
	if s := sumHits(doc.APIKeys); s > doc.Total.Hits {
		fail("sum(apikeys)<=total", "sum of apikeys hits %d exceeds total %d", s, doc.Total.Hits)
	}
	if s := sumHits(doc.Errors); s != doc.Total.ErrorTotal {
		fail("total.errortotal=sum(errors)", "total.errortotal %d, sum of errors hits %d", doc.Total.ErrorTotal, s)
	}
	for id, c := range doc.APIID {
		if t, ok := doc.Tags["api-"+agg.TrimTag(id)]; ok && t.Hits != c.Hits {
			fail("tags.api-<id>=apiid", "api %s: apiid hits %d, tag hits %d", id, c.Hits, t.Hits)
		}
	}
	if !doc.LastTime.Equal(doc.Total.LastTime) {
		fail("lasttime", "lasttime %s, total.lasttime %s", doc.LastTime, doc.Total.LastTime)
	}
	return out
}

func checkCounter(where string, c *agg.Counter, fail func(string, string, ...any)) {
	if c.Success+c.ErrorTotal != c.Hits {
		fail("success+errors=hits", "%s: success %d + errortotal %d != hits %d", where, c.Success, c.ErrorTotal, c.Hits)
	}
	sum := 0
	for _, v := range c.ErrorMap {
		sum += v
	}
	if sum != c.ErrorTotal {
		fail("sum(errormap)=errortotal", "%s: errormap sums to %d, errortotal %d", where, sum, c.ErrorTotal)
	}
	if len(c.ErrorList) != len(c.ErrorMap) {
		fail("errorlist=errormap", "%s: %d errorlist entries, %d errormap entries", where, len(c.ErrorList), len(c.ErrorMap))
	} else {
		for _, e := range c.ErrorList {
			if c.ErrorMap[e.Code] != e.Count {
				fail("errorlist=errormap", "%s: code %s errorlist %d errormap %d", where, e.Code, e.Count, c.ErrorMap[e.Code])
			}
		}
	}
	if c.Hits > 0 {
		h := float64(c.Hits)
		if !near(c.Latency, float64(c.TotalLatency)/h) || !near(c.RequestTime, c.TotalRequestTime/h) ||
			!near(c.UpstreamLatency, float64(c.TotalUpstreamLatency)/h) {
			fail("averages", "%s: averages do not equal totals/hits", where)
		}
		if c.MinLatency > c.MaxLatency || c.MinUpstreamLatency > c.MaxUpstreamLatency {
			fail("min<=max", "%s: min latency above max", where)
		}
	}
}

func checkList(name string, m map[string]*agg.Counter, list []agg.ListCounter, fail func(string, string, ...any)) {
	if len(list) != len(m) {
		fail("lists=maps", "lists.%s has %d entries, %s has %d", name, len(list), name, len(m))
		return
	}
	byID := map[string]*agg.Counter{}
	for _, c := range m {
		byID[c.Identifier] = c
	}
	for _, l := range list {
		// versions are keyed by hash but identified by version name, which can
		// repeat across APIs, so only check hits for unique identifiers.
		c, ok := byID[l.Identifier]
		if !ok {
			fail("lists=maps", "lists.%s entry %q has no matching %s entry", name, l.Identifier, name)
			continue
		}
		if name != "versions" && c.Hits != l.Hits {
			fail("lists=maps", "lists.%s %q hits %d, map hits %d", name, l.Identifier, l.Hits, c.Hits)
		}
	}
}

func sumHits(m map[string]*agg.Counter) int {
	s := 0
	for _, c := range m {
		s += c.Hits
	}
	return s
}

func near(a, b float64) bool {
	return math.Abs(a-b) <= 1e-6*math.Max(1, math.Abs(b))
}

// Report aggregates issues across documents.
type Report struct {
	Docs     int
	Failed   int
	ByRule   map[string]int
	Examples map[string]string
}

func NewReport() *Report {
	return &Report{ByRule: map[string]int{}, Examples: map[string]string{}}
}

func (r *Report) Add(doc *agg.Doc) {
	r.Docs++
	issues := Doc(doc)
	if len(issues) > 0 {
		r.Failed++
	}
	for _, i := range issues {
		r.ByRule[i.Rule]++
		if _, ok := r.Examples[i.Rule]; !ok {
			r.Examples[i.Rule] = fmt.Sprintf("%s: %s", doc.TimeStamp.UTC().Format("2006-01-02T15:04Z"), i.Detail)
		}
	}
}

func (r *Report) String() string {
	var b strings.Builder
	fmt.Fprintf(&b, "checked %d documents, %d with issues\n", r.Docs, r.Failed)
	for rule, n := range r.ByRule {
		fmt.Fprintf(&b, "  %-30s %8d  e.g. %s\n", rule, n, r.Examples[rule])
	}
	return b.String()
}
