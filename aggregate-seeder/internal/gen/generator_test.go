package gen

import (
	"math"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/TykTechnologies/aggregate-seeder/internal/inventory"
	"github.com/TykTechnologies/aggregate-seeder/internal/profile"
	"github.com/TykTechnologies/aggregate-seeder/internal/verify"
)

func testInventory() *inventory.Inventory {
	inv := &inventory.Inventory{
		OrgID: "org1",
		APIs: []inventory.API{
			{ID: "api1", Name: "Orders", Tags: []string{"internal", "team.a"}, Versions: []string{"Non Versioned"}, Active: true},
			{ID: "api2", Name: "Payments", Versions: []string{"Non Versioned", "v1", "v2"}, Active: true},
			{ID: "api3", Name: "Health", Versions: []string{"Non Versioned"}, Keyless: true, Active: true},
		},
		Policies: []inventory.Policy{{ID: "pol1", Name: "Gold", APIs: []string{"api1", "api2"}}},
	}
	for i := range 20 {
		k := inventory.Key{
			ID:       "key" + string(rune('a'+i)),
			Alias:    "consumer",
			Policies: []string{"pol1"},
			Access:   map[string][]string{"api1": nil, "api2": {"v1"}},
		}
		if i%2 == 0 {
			k.Tags = []string{"portal-org-1", "portal-app-" + string(rune('0'+i%10))}
		}
		inv.Keys = append(inv.Keys, k)
	}
	inv.Validate()
	return inv
}

func newGen(t *testing.T, minutes int, seed uint64) *Generator {
	t.Helper()
	from := time.Date(2025, 10, 6, 0, 0, 0, 0, time.UTC) // a Monday
	g, err := New(testInventory(), profile.Default(), Options{
		OrgID: "org1", From: from, To: from.Add(24 * time.Hour), BucketMinutes: minutes,
		Seed: seed, ExpireAt: from.AddDate(10, 0, 0), RunID: "test",
	})
	if err != nil {
		t.Fatal(err)
	}
	return g
}

func TestDocsAreConsistent(t *testing.T) {
	for _, minutes := range []int{60, 15} {
		g := newGen(t, minutes, 7)
		rep := verify.NewReport()
		for _, b := range g.Buckets() {
			if d := g.Bucket(b); d != nil {
				rep.Add(d)
				if d.TimeID.Hour != b.Hour() || !d.TimeStamp.Equal(b) {
					t.Fatalf("bucket %s: timestamp %s timeid %+v", b, d.TimeStamp, d.TimeID)
				}
			}
		}
		if rep.Failed > 0 {
			t.Fatalf("%d-minute buckets:\n%s", minutes, rep)
		}
		if rep.Docs != 24*60/minutes {
			t.Fatalf("expected a document per bucket, got %d", rep.Docs)
		}
	}
}

func TestDailyVolume(t *testing.T) {
	g := newGen(t, 60, 3)
	total := 0
	for _, b := range g.Buckets() {
		if d := g.Bucket(b); d != nil {
			total += d.Total.Hits
		}
	}
	// Monday weekday factor and noise move it around, but it should be in range.
	want := profile.Default().DailyRequests
	if ratio := float64(total) / want; math.Abs(ratio-1) > 0.35 {
		t.Fatalf("daily total %d is %.2fx the profile's %v", total, ratio, want)
	}
}

func TestDeterministic(t *testing.T) {
	ts := time.Date(2025, 10, 6, 10, 0, 0, 0, time.UTC)
	a, b := newGen(t, 60, 42).Bucket(ts), newGen(t, 60, 42).Bucket(ts)
	if !reflect.DeepEqual(a, b) {
		t.Fatal("same seed produced different documents")
	}
	if c := newGen(t, 60, 43).Bucket(ts); reflect.DeepEqual(a, c) {
		t.Fatal("different seeds produced identical documents")
	}
}

func TestTagsAndDimensions(t *testing.T) {
	d := newGen(t, 60, 1).Bucket(time.Date(2025, 10, 6, 11, 0, 0, 0, time.UTC))
	for _, tag := range []string{"pol-pol1", "portal-org-1", "api-api1", "api-api3", "org-org1", "internal", "teama"} {
		if _, ok := d.Tags[tag]; !ok {
			t.Errorf("missing tag %q", tag)
		}
	}
	for tag := range d.Tags {
		if strings.HasPrefix(tag, "key-") || strings.Contains(tag, ".") {
			t.Errorf("tag %q should have been dropped or trimmed", tag)
		}
	}
	// Keyless traffic has no key; key traffic never reaches v2 (not granted).
	keyHits := 0
	for _, k := range d.APIKeys {
		keyHits += k.Hits
	}
	if keyHits+d.APIID["api3"].Hits != d.Total.Hits {
		t.Errorf("key hits %d + keyless hits %d != total %d", keyHits, d.APIID["api3"].Hits, d.Total.Hits)
	}
	for _, v := range d.Versions {
		if v.Identifier == "v2" {
			t.Errorf("v2 received traffic but no key grants it")
		}
	}
	if d.Tags["pol-pol1"].Hits != keyHits {
		t.Errorf("pol-pol1 hits %d, want all key hits %d", d.Tags["pol-pol1"].Hits, keyHits)
	}
}
