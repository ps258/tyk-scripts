package agg

import (
	"testing"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/bsontype"
)

func TestVersionKeyMatchesPump(t *testing.T) {
	// Taken from a real pump-written document (aggregate.json).
	got := VersionKey("41a13688a4a944ff4ce504a455a9ce2b", "Non Versioned")
	want := "NDFhMTM2ODhhNGE5NDRmZjRjZTUwNGE0NTVhOWNlMmI6Tm9uIFZlcnNpb25lZA"
	if got != want {
		t.Fatalf("VersionKey = %s, want %s", got, want)
	}
}

func TestDocBSONShape(t *testing.T) {
	ts := time.Date(2025, 10, 8, 8, 30, 0, 0, time.UTC)
	b := NewBuilder("org1", ts, ts.AddDate(1, 0, 0), "run1")
	b.Add(&Counter{Hits: 10, Success: 8, ErrorTotal: 2, ErrorMap: map[string]int{"500": 2},
		TotalLatency: 1000, TotalRequestTime: 1000, MaxLatency: 400, MinLatency: 10, LastTime: ts.Add(time.Minute)},
		Dims{APIID: "a1", APIName: "API 1", Version: "Non Versioned", KeyID: "k1", Alias: "alias", Tags: []string{"api-a1", "pol-p1"}})
	doc := b.Finish()

	raw, err := bson.Marshal(doc)
	if err != nil {
		t.Fatal(err)
	}
	r := bson.Raw(raw)

	// Field types as the pump writes them.
	types := map[string]bsontype.Type{
		"timestamp":                   bsontype.DateTime,
		"timeid.hour":                 bsontype.Int32,
		"total.hits":                  bsontype.Int32,
		"total.errortotal":            bsontype.Int32,
		"total.totallatency":          bsontype.Int64,
		"total.totalrequesttime":      bsontype.Double,
		"total.latency":               bsontype.Double,
		"apiid.a1.bytesin":            bsontype.Int64,
		"apiid.a1.errormap.500":       bsontype.Int32,
		"lists.apiid":                 bsontype.Array,
		"lists.apiendpoints":          bsontype.Array,
		"errors.500.hits":             bsontype.Int32,
		"tags.pol-p1.humanidentifier": bsontype.String,
		"expireAt":                    bsontype.DateTime,
	}
	for path, want := range types {
		v, err := r.LookupErr(splitPath(path)...)
		if err != nil {
			t.Errorf("%s missing: %v", path, err)
			continue
		}
		if v.Type != want {
			t.Errorf("%s has type %s, want %s", path, v.Type, want)
		}
	}
	if doc.TimeID.Hour != 8 {
		t.Errorf("timeid.hour = %d, want 8", doc.TimeID.Hour)
	}
	if _, err := r.LookupErr("oauthids"); err == nil {
		t.Errorf("empty oauthids map should be omitted")
	}
	if e := doc.Errors["500"]; e.Hits != 2 || e.Success != 0 || e.ErrorMap["500"] != 2 {
		t.Errorf("errors.500 = %+v", e)
	}
	if doc.Total.Latency != 100 {
		t.Errorf("total.latency = %v, want 100", doc.Total.Latency)
	}
}

func splitPath(p string) []string {
	var out []string
	start := 0
	for i := 0; i < len(p); i++ {
		if p[i] == '.' {
			out = append(out, p[start:i])
			start = i + 1
		}
	}
	return append(out, p[start:])
}
