package agg

import (
	"sort"
	"time"
)

type TimeID struct {
	Year  int `bson:"year" json:"year"`
	Month int `bson:"month" json:"month"`
	Day   int `bson:"day" json:"day"`
	Hour  int `bson:"hour" json:"hour"`
}

type Lists struct {
	APIEndpoints []ListCounter `bson:"apiendpoints" json:"apiendpoints"`
	APIID        []ListCounter `bson:"apiid" json:"apiid"`
	APIKeys      []ListCounter `bson:"apikeys" json:"apikeys"`
	Endpoints    []ListCounter `bson:"endpoints" json:"endpoints"`
	Errors       []ListCounter `bson:"errors" json:"errors"`
	Geo          []ListCounter `bson:"geo" json:"geo"`
	OauthIDs     []ListCounter `bson:"oauthids" json:"oauthids"`
	Tags         []ListCounter `bson:"tags" json:"tags"`
	Versions     []ListCounter `bson:"versions" json:"versions"`
}

// Doc is one aggregate document. Empty dimension maps are omitted, matching
// the pump (which only ever $inc's into the keys it has seen).
type Doc struct {
	OrgID     string              `bson:"orgid" json:"orgid"`
	TimeStamp time.Time           `bson:"timestamp" json:"timestamp"`
	TimeID    TimeID              `bson:"timeid" json:"timeid"`
	APIID     map[string]*Counter `bson:"apiid,omitempty" json:"apiid,omitempty"`
	APIKeys   map[string]*Counter `bson:"apikeys,omitempty" json:"apikeys,omitempty"`
	Errors    map[string]*Counter `bson:"errors,omitempty" json:"errors,omitempty"`
	Versions  map[string]*Counter `bson:"versions,omitempty" json:"versions,omitempty"`
	OauthIDs  map[string]*Counter `bson:"oauthids,omitempty" json:"oauthids,omitempty"`
	Tags      map[string]*Counter `bson:"tags,omitempty" json:"tags,omitempty"`
	Lists     Lists               `bson:"lists" json:"lists"`
	Total     Counter             `bson:"total" json:"total"`
	ExpireAt  time.Time           `bson:"expireAt" json:"expireAt"`
	LastTime  time.Time           `bson:"lasttime" json:"lasttime"`
	// Seed marks documents written by this tool so they can be found and removed.
	Seed string `bson:"_seed,omitempty" json:"_seed,omitempty"`
}

// Dims identifies where a cell's traffic is attributed.
type Dims struct {
	APIID   string
	APIName string
	Version string // analytics version name, e.g. "Non Versioned"
	KeyID   string // apikeys identifier ("" for keyless)
	Alias   string
	OauthID string
	Tags    []string // already trimmed and filtered, in record order
}

// Builder accumulates cells into a Doc.
type Builder struct {
	doc *Doc
}

// NewBuilder starts a document for the bucket beginning at ts. timeid is
// derived from ts as the pump does, so minute buckets share an hour's timeid.
func NewBuilder(orgID string, ts, expireAt time.Time, seed string) *Builder {
	ts = ts.UTC()
	return &Builder{doc: &Doc{
		OrgID:     orgID,
		TimeStamp: ts,
		TimeID:    TimeID{Year: ts.Year(), Month: int(ts.Month()), Day: ts.Day(), Hour: ts.Hour()},
		APIID:     map[string]*Counter{},
		APIKeys:   map[string]*Counter{},
		Errors:    map[string]*Counter{},
		Versions:  map[string]*Counter{},
		OauthIDs:  map[string]*Counter{},
		Tags:      map[string]*Counter{},
		ExpireAt:  expireAt,
		Seed:      seed,
	}}
}

func unit(m map[string]*Counter, key, id, human string) *Counter {
	c, ok := m[key]
	if !ok {
		c = &Counter{Identifier: id, HumanIdentifier: human}
		m[key] = c
	}
	return c
}

// Add attributes one cell to every dimension it belongs to.
func (b *Builder) Add(cell *Counter, d Dims) {
	if cell.Hits == 0 {
		return
	}
	doc := b.doc
	doc.Total.merge(cell)
	unit(doc.APIID, d.APIID, d.APIID, d.APIName).merge(cell)
	if d.Version != "" {
		unit(doc.Versions, VersionKey(d.APIID, d.Version), d.Version, d.Version).merge(cell)
	}
	if d.KeyID != "" {
		unit(doc.APIKeys, d.KeyID, d.KeyID, d.Alias).merge(cell)
	}
	if d.OauthID != "" {
		unit(doc.OauthIDs, d.OauthID, d.OauthID, "").merge(cell)
	}
	// Like the pump, a tag repeated on a record is counted once per occurrence.
	for _, t := range d.Tags {
		unit(doc.Tags, t, t, t).merge(cell)
	}
	for code, n := range cell.ErrorMap {
		unit(doc.Errors, code, code, "").merge(cell.errorSlice(code, n))
	}
}

// Empty reports whether no traffic was added.
func (b *Builder) Empty() bool { return b.doc.Total.Hits == 0 }

// Finish computes averages, error lists and the lists.* arrays.
func (b *Builder) Finish() *Doc {
	doc := b.doc
	doc.Total.Identifier, doc.Total.HumanIdentifier = "", ""
	doc.Total.finalize()
	if doc.Total.ErrorMap == nil {
		doc.Total.ErrorMap = map[string]int{}
	}
	doc.LastTime = doc.Total.LastTime

	doc.Lists = Lists{
		APIEndpoints: []ListCounter{},
		APIID:        toList(doc.APIID),
		APIKeys:      toList(doc.APIKeys),
		Endpoints:    []ListCounter{},
		Errors:       toList(doc.Errors),
		Geo:          []ListCounter{},
		OauthIDs:     toList(doc.OauthIDs),
		Tags:         toList(doc.Tags),
		Versions:     toList(doc.Versions),
	}
	return doc
}

// toList finalizes each counter and returns them ordered by hits (desc) then
// identifier, so output is deterministic for a given seed.
func toList(m map[string]*Counter) []ListCounter {
	keys := make([]string, 0, len(m))
	for k, c := range m {
		c.finalize()
		keys = append(keys, k)
	}
	sort.Slice(keys, func(i, j int) bool {
		a, b := m[keys[i]], m[keys[j]]
		if a.Hits != b.Hits {
			return a.Hits > b.Hits
		}
		return keys[i] < keys[j]
	})
	out := make([]ListCounter, 0, len(keys))
	for _, k := range keys {
		out = append(out, m[k].asListItem())
	}
	return out
}
