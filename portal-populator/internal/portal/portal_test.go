package portal

import (
	"bytes"
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"net/http/httptest"
	"reflect"
	"strconv"
	"strings"
	"sync"
	"testing"
)

func TestTierSizes(t *testing.T) {
	apis := []string{"a", "b", "c", "d", "e"}
	want := map[string]struct{ apps, creds int }{
		"small":  {650, 975},
		"medium": {12750, 19125},
		"large":  {51000, 63750},
		"xlarge": {63750, 89250},
	}
	for name, w := range want {
		p, err := BuildPlan("stress", Tiers[name], apis, 1)
		if err != nil {
			t.Fatal(err)
		}
		if len(p.Apps) != w.apps {
			t.Errorf("%s: %d apps, want %d", name, len(p.Apps), w.apps)
		}
		if got := p.Credentials(); math.Abs(float64(got-w.creds)) > 0.06*float64(w.creds) {
			t.Errorf("%s: %d credentials, want about %d", name, got, w.creds)
		}
	}
}

func TestPlanDeterministicAndValid(t *testing.T) {
	apis := []string{"a", "b", "c", "d"}
	p1, _ := BuildPlan("stress", Tiers["small"], apis, 7)
	p2, _ := BuildPlan("stress", Tiers["small"], apis, 7)
	if !reflect.DeepEqual(p1, p2) {
		t.Fatal("same seed produced different plans")
	}
	admins := map[int]int{}
	for _, d := range p1.Devs {
		if d.Role == "consumer-admin" {
			admins[d.Org]++
		}
	}
	for org := range p1.Orgs {
		if admins[org] != 1 {
			t.Errorf("org %d has %d consumer-admins, want 1", org, admins[org])
		}
	}
	for _, a := range p1.Apps {
		seen := map[int]bool{}
		for _, r := range a.Requests {
			if seen[r.Product] {
				t.Errorf("app %s requests product %d twice", a.Name, r.Product)
			}
			seen[r.Product] = true
		}
	}
}

func TestIneligible(t *testing.T) {
	ok := DashboardAPI{Active: true, UseStandardAuth: true}
	if r := ok.Ineligible(); r != "" {
		t.Fatalf("auth token API rejected: %s", r)
	}
	for _, a := range []DashboardAPI{
		{Active: false, UseStandardAuth: true},
		{Active: true, UseKeyless: true},
		{Active: true, EnableJWT: true},
		{Active: true, UseStandardAuth: true, UseBasicAuth: true},
	} {
		if a.Ineligible() == "" {
			t.Errorf("%+v should be ineligible", a)
		}
	}
}

// fakePortal is an in-memory stand-in for the portal admin API.
type fakePortal struct {
	t     *testing.T
	mu    sync.Mutex
	next  uint
	store map[string][]map[string]any // resource -> objects
	ars   map[uint][]map[string]any   // app id -> access requests
	calls map[string]int
	// lockNext makes the next n writes fail like a busy SQLite database.
	lockNext int
	// wantOrg, when set, is the organisation every created user must be in.
	wantOrg uint
}

func newFakePortal(t *testing.T) *fakePortal {
	f := &fakePortal{t: t, next: 100, store: map[string][]map[string]any{}, ars: map[uint][]map[string]any{}, calls: map[string]int{}}
	f.store["providers"] = []map[string]any{{"ID": float64(1), "Name": "dashboard"}}
	// An unrelated object that cleanup must not touch.
	f.store["products"] = []map[string]any{{"ID": float64(5), "Name": "customer-product"}}
	return f
}

func (f *fakePortal) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	f.mu.Lock()
	defer f.mu.Unlock()
	if r.Header.Get("Authorization") != "token" {
		http.Error(w, "unauthorised", http.StatusUnauthorized)
		return
	}
	parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/portal-api/"), "/")
	res := parts[0]
	f.calls[r.Method+" "+res]++

	if r.Method != http.MethodGet && f.lockNext > 0 {
		f.lockNext--
		w.WriteHeader(http.StatusUnprocessableEntity)
		w.Write([]byte(`{"errors":["database is locked"]}`))
		return
	}

	var body map[string]any
	if r.Body != nil {
		_ = json.NewDecoder(r.Body).Decode(&body)
	}
	idOf := func(s string) uint { n, _ := strconv.Atoi(s); return uint(n) }

	switch {
	case r.Method == http.MethodGet && len(parts) == 1:
		page, _ := strconv.Atoi(r.URL.Query().Get("page"))
		per, _ := strconv.Atoi(r.URL.Query().Get("per_page"))
		all := f.store[res]
		lo, hi := min((page-1)*per, len(all)), min(page*per, len(all))
		json.NewEncoder(w).Encode(all[lo:hi])
	case r.Method == http.MethodGet && len(parts) == 2:
		for _, o := range f.store[res] {
			if uint(o["ID"].(float64)) == idOf(parts[1]) {
				json.NewEncoder(w).Encode(o)
				return
			}
		}
		http.NotFound(w, r)
	case r.Method == http.MethodGet && len(parts) == 3 && parts[2] == "access-requests":
		json.NewEncoder(w).Encode(f.ars[idOf(parts[1])])
	case r.Method == http.MethodGet && len(parts) == 5 && parts[4] == "credentials":
		// One credential per access request; the key embeds both IDs.
		json.NewEncoder(w).Encode([]map[string]any{{
			"ID":             float64(1),
			"Credential":     "key-" + parts[1] + "-" + parts[3],
			"CredentialHash": "hash-" + parts[1] + "-" + parts[3],
		}})
	case r.Method == http.MethodPost && len(parts) == 1:
		f.validateCreate(res, body)
		f.next++
		body["ID"] = float64(f.next)
		f.store[res] = append(f.store[res], body)
		json.NewEncoder(w).Encode(body)
	case r.Method == http.MethodPut && len(parts) == 3 && parts[2] == "provision":
		if len(body["ProductIDs"].([]any)) != 1 || body["PlanID"].(float64) == 0 || body["ProvisionImmediately"] != true {
			f.t.Errorf("bad provision body %v", body)
		}
		id := idOf(parts[1])
		f.ars[id] = append(f.ars[id], map[string]any{"ID": float64(len(f.ars[id]) + 1)})
	case r.Method == http.MethodPut && len(parts) == 2:
		f.calls["PUT "+res+" body"] = len(body["Products"].([]any))
	case r.Method == http.MethodDelete && len(parts) == 2:
		objs := f.store[res]
		for i, o := range objs {
			if uint(o["ID"].(float64)) == idOf(parts[1]) {
				f.store[res] = append(objs[:i], objs[i+1:]...)
				return
			}
		}
		http.NotFound(w, r)
	default:
		http.Error(w, "unexpected "+r.Method+" "+r.URL.Path, http.StatusNotFound)
	}
}

func (f *fakePortal) validateCreate(res string, b map[string]any) {
	nonZero := func(k string) {
		if v, _ := b[k].(float64); v == 0 {
			f.t.Errorf("POST %s: %s missing in %v", res, k, b)
		}
	}
	switch res {
	case "products":
		nonZero("ProviderID")
		if len(b["APIDetails"].([]any)) == 0 {
			f.t.Errorf("product without APIs: %v", b)
		}
	case "plans":
		nonZero("ProviderID")
		nonZero("RateLimit")
		nonZero("Quota")
	case "users":
		nonZero("OrganisationID")
		if f.wantOrg != 0 && uint(b["OrganisationID"].(float64)) != f.wantOrg {
			f.t.Errorf("user in org %v, want %d", b["OrganisationID"], f.wantOrg)
		}
		if b["Active"] != true || b["Password"] != "pw" {
			f.t.Errorf("user not active or without password: %v", b)
		}
	case "catalogues":
		if b["NameWithSlug"] == "" || b["NameWithSlug"] == nil {
			f.t.Errorf("catalogue without NameWithSlug: %v", b)
		}
	case "apps":
		nonZero("UserID")
		if b["Visibility"] != "personal" {
			f.t.Errorf("app visibility %v", b["Visibility"])
		}
	}
}

func TestProvisionResumeAndCleanup(t *testing.T) {
	f := newFakePortal(t)
	srv := httptest.NewServer(f)
	defer srv.Close()
	c := NewClient(srv.URL+"/portal-api", "token", false)
	ctx := context.Background()

	tier := Tier{Plans: 3, Products: 4, APIsPerProduct: 2, Orgs: 2, Developers: 6, HeavyDevelopers: 1, HeavyApps: 5, CredentialsPerApp: 1.5}
	plan, err := BuildPlan("stress", tier, []string{"api1", "api2", "api3"}, 1)
	if err != nil {
		t.Fatal(err)
	}
	pid, err := ResolveProvider(ctx, c, 0)
	if err != nil || pid != 1 {
		t.Fatalf("provider %d, %v", pid, err)
	}
	opts := Options{ProviderID: pid, Concurrency: 3, Password: "pw", Visibility: "personal"}

	res, err := Provision(ctx, c, plan, opts)
	if err != nil {
		t.Fatal(err)
	}
	want := map[string]int{"products": 4, "plans": 3, "catalogues": 1, "organisations": 2, "developers": 6, "apps": 10, "access requests": plan.Credentials()}
	if !reflect.DeepEqual(res.Created, want) {
		t.Fatalf("created %v, want %v", res.Created, want)
	}
	if f.calls["PUT catalogues body"] != 4 {
		t.Errorf("catalogue should hold 4 products, got %d", f.calls["PUT catalogues body"])
	}

	// Drop one app's access requests to simulate an interrupted run.
	f.mu.Lock()
	someApp := uint(f.store["apps"][0]["ID"].(float64))
	lost := len(f.ars[someApp])
	f.ars[someApp] = nil
	f.mu.Unlock()

	res, err = Provision(ctx, c, plan, opts)
	if err != nil {
		t.Fatal(err)
	}
	for kind, n := range res.Created {
		if kind == "access requests" {
			if n != lost {
				t.Errorf("resume provisioned %d access requests, want %d", n, lost)
			}
		} else if n != 0 {
			t.Errorf("resume created %d %s", n, kind)
		}
	}

	counts, err := Cleanup(ctx, c, "stress", 2, false)
	if err != nil {
		t.Fatal(err)
	}
	if counts["apps"] != 10 || counts["developers"] != 6 || counts["products"] != 4 {
		t.Errorf("cleanup counts %v", counts)
	}
	if got := fmt.Sprint(f.store["products"]); !strings.Contains(got, "customer-product") || len(f.store["products"]) != 1 {
		t.Errorf("cleanup touched unrelated products: %v", got)
	}
}

func TestRetriesLockedDatabase(t *testing.T) {
	f := newFakePortal(t)
	f.lockNext = 3
	srv := httptest.NewServer(f)
	defer srv.Close()
	c := NewClient(srv.URL+"/portal-api", "token", false)

	var it item
	if err := c.Do(context.Background(), http.MethodPost, "/organisations", map[string]any{"Name": "o"}, &it); err != nil {
		t.Fatalf("locked writes should be retried: %v", err)
	}
	if it.ID == 0 || c.LockRetries() != 3 {
		t.Fatalf("id %d, lock retries %d", it.ID, c.LockRetries())
	}

	// Other 4xx errors are not retried.
	err := c.Do(context.Background(), http.MethodPost, "/nope/1/2/3", map[string]any{}, nil)
	if he, ok := err.(*HTTPError); !ok || he.Status != http.StatusNotFound {
		t.Fatalf("want a 404 HTTPError, got %v", err)
	}
}

func TestSingleAppDefaultOrg(t *testing.T) {
	tier := Tiers["small"]
	tier.HeavyDevelopers, tier.DefaultOrg = 0, true
	plan, err := BuildPlan("stress", tier, []string{"a", "b", "c"}, 1)
	if err != nil {
		t.Fatal(err)
	}
	if len(plan.Orgs) != 0 || len(plan.Apps) != len(plan.Devs) {
		t.Fatalf("%d orgs, %d apps for %d developers", len(plan.Orgs), len(plan.Apps), len(plan.Devs))
	}

	f := newFakePortal(t)
	f.wantOrg = DefaultOrgID
	srv := httptest.NewServer(f)
	defer srv.Close()
	c := NewClient(srv.URL+"/portal-api", "token", false)
	res, err := Provision(context.Background(), c, plan, Options{ProviderID: 1, Concurrency: 2, Password: "pw", Visibility: "personal"})
	if err != nil {
		t.Fatal(err)
	}
	if res.Created["organisations"] != 0 || res.Created["apps"] != tier.Developers {
		t.Fatalf("created %v", res.Created)
	}
	for _, u := range f.store["users"] {
		if u["Role"] != "consumer-admin" {
			t.Fatalf("default-org developer has role %v", u["Role"])
		}
	}

	// Re-provisioning the same developers into organisations must be refused.
	tier.DefaultOrg = false
	orgPlan, _ := BuildPlan("stress", tier, []string{"a", "b", "c"}, 1)
	f.wantOrg = 0
	if _, err := Provision(context.Background(), c, orgPlan, Options{ProviderID: 1, Concurrency: 2, Password: "pw", Visibility: "personal"}); err == nil ||
		!strings.Contains(err.Error(), "different organisation") {
		t.Fatalf("expected org mismatch error, got %v", err)
	}
}

func TestNamesByKind(t *testing.T) {
	tier := Tier{Plans: 1, Products: 1, APIsPerProduct: 1, Orgs: 2, Developers: 6, HeavyDevelopers: 2, HeavyApps: 3, CredentialsPerApp: 1}
	p, err := BuildPlan("stress", tier, []string{"a"}, 1)
	if err != nil {
		t.Fatal(err)
	}
	var emails, apps []string
	for _, d := range p.Devs {
		emails = append(emails, d.Email)
	}
	for _, a := range p.Apps {
		apps = append(apps, a.Name)
	}
	// Heavy developers are spread through the list (positions 1 and 4) but
	// each kind is numbered from 0001.
	wantEmails := []string{
		"stress-single-0001@stress.test", "stress-multi-0001@stress.test", "stress-single-0002@stress.test",
		"stress-single-0003@stress.test", "stress-multi-0002@stress.test", "stress-single-0004@stress.test",
	}
	if !reflect.DeepEqual(emails, wantEmails) {
		t.Errorf("emails %v", emails)
	}
	wantApps := []string{
		"stress-single-0001-app",
		"stress-multi-0001-app-01", "stress-multi-0001-app-02", "stress-multi-0001-app-03",
		"stress-single-0002-app", "stress-single-0003-app",
		"stress-multi-0002-app-01", "stress-multi-0002-app-02", "stress-multi-0002-app-03",
		"stress-single-0004-app",
	}
	if !reflect.DeepEqual(apps, wantApps) {
		t.Errorf("apps %v", apps)
	}
	if d := p.Devs[1]; d.First != "Multi" || d.Last != "0001" {
		t.Errorf("display name %q %q", d.First, d.Last)
	}
	for _, a := range p.Apps {
		owner, _, _, ok := parseAppName("stress", a.Name)
		if !ok || owner+"@stress.test" != p.Devs[a.Dev].Email {
			t.Errorf("app %s parsed to owner %q", a.Name, owner)
		}
	}
	for _, bad := range []string{"stress-app-00001", "stress-single-0001-apple", "other-single-0001-app", "stress-single--app"} {
		if _, _, _, ok := parseAppName("stress", bad); ok {
			t.Errorf("%s should not parse", bad)
		}
	}
}

func TestExportCSV(t *testing.T) {
	f := newFakePortal(t)
	srv := httptest.NewServer(f)
	defer srv.Close()
	c := NewClient(srv.URL+"/portal-api", "token", false)
	ctx := context.Background()

	tier := Tier{Plans: 2, Products: 3, APIsPerProduct: 1, Orgs: 2, Developers: 4, HeavyDevelopers: 1, HeavyApps: 3, CredentialsPerApp: 2}
	plan, _ := BuildPlan("stress", tier, []string{"api1", "api2"}, 1)
	if _, err := Provision(ctx, c, plan, Options{ProviderID: 1, Concurrency: 2, Password: "pw", Visibility: "personal"}); err != nil {
		t.Fatal(err)
	}
	// An unrelated app and developer that must not be exported.
	f.mu.Lock()
	f.store["apps"] = append(f.store["apps"], map[string]any{"ID": float64(9999), "Name": "customer-app"})
	f.mu.Unlock()

	var buf bytes.Buffer
	n, err := Export(ctx, c, "stress", "pw", 2, &buf)
	if err != nil {
		t.Fatal(err)
	}
	recs, err := csv.NewReader(&buf).ReadAll()
	if err != nil {
		t.Fatal(err)
	}
	if n != len(plan.Apps) || len(recs) != n+1 {
		t.Fatalf("%d rows (%d records) for %d apps", n, len(recs), len(plan.Apps))
	}
	if !reflect.DeepEqual(recs[0], ExportColumns) {
		t.Fatalf("header %v", recs[0])
	}
	col := map[string]int{}
	for i, h := range ExportColumns {
		col[h] = i
	}
	// Singles first, then multis, each in number order.
	var order []string
	for _, r := range recs[1:] {
		order = append(order, r[col["app_name"]])
		if r[col["password"]] != "pw" || r[col["app_tag"]] != "portal-app-"+r[col["app_id"]] {
			t.Errorf("row %v", r)
		}
		if !strings.HasPrefix(r[col["org_tag"]], "portal-org-") || !strings.HasPrefix(r[col["organisation"]], "stress-org-") {
			t.Errorf("organisation columns in %v", r)
		}
		if keys := strings.Fields(r[col["keys"]]); len(keys) != 2 || !strings.HasPrefix(keys[0], "key-"+r[col["app_id"]]+"-") {
			t.Errorf("keys %q for app %s", r[col["keys"]], r[col["app_id"]])
		}
		wantCount := "1"
		if r[col["kind"]] == KindMulti {
			wantCount = "3"
		}
		if r[col["app_count"]] != wantCount {
			t.Errorf("app_count %s for %s", r[col["app_count"]], r[col["email"]])
		}
	}
	want := []string{"stress-single-0001-app", "stress-single-0002-app", "stress-single-0003-app",
		"stress-multi-0001-app-01", "stress-multi-0001-app-02", "stress-multi-0001-app-03"}
	if !reflect.DeepEqual(order, want) {
		t.Errorf("row order %v", order)
	}
}

func TestCleanupMatchesOldNames(t *testing.T) {
	f := newFakePortal(t)
	f.store["apps"] = []map[string]any{
		{"ID": float64(1), "Name": "stress-app-00001"},
		{"ID": float64(2), "Name": "stress-single-0001-app"},
		{"ID": float64(3), "Name": "stress-multi-0001-app-01"},
		{"ID": float64(4), "Name": "stressed-single-0001-app"},
	}
	f.store["users"] = []map[string]any{
		{"ID": float64(1), "Email": "stress-dev-0001@stress.test"},
		{"ID": float64(2), "Email": "stress-single-0001@stress.test"},
		{"ID": float64(3), "Email": "stress-multi-0001@stress.test"},
		{"ID": float64(4), "Email": "stress-single-0001@example.com"},
	}
	srv := httptest.NewServer(f)
	defer srv.Close()
	c := NewClient(srv.URL+"/portal-api", "token", false)
	counts, err := Cleanup(context.Background(), c, "stress", 1, false)
	if err != nil {
		t.Fatal(err)
	}
	if counts["apps"] != 3 || counts["developers"] != 3 {
		t.Fatalf("counts %v", counts)
	}
	if len(f.store["apps"]) != 1 || len(f.store["users"]) != 1 {
		t.Fatalf("left apps %v, users %v", f.store["apps"], f.store["users"])
	}
}

func TestHalfHeavySpreadAcrossOrgs(t *testing.T) {
	for _, name := range TierNames() {
		tier := Tiers[name]
		if tier.HeavyDevelopers != tier.DefaultHeavy() {
			t.Errorf("%s: preset has %d heavy developers, want half", name, tier.HeavyDevelopers)
		}
		p, err := BuildPlan("stress", tier, []string{"a", "b", "c"}, 1)
		if err != nil {
			t.Fatal(err)
		}
		perOrg := map[int]map[string]int{}
		admins := map[int]int{}
		for _, d := range p.Devs {
			if perOrg[d.Org] == nil {
				perOrg[d.Org] = map[string]int{}
			}
			perOrg[d.Org][d.Kind()]++
			if d.Role == "consumer-admin" {
				admins[d.Org]++
			}
		}
		singles, multis := 0, 0
		for org := range p.Orgs {
			singles += perOrg[org][KindSingle]
			multis += perOrg[org][KindMulti]
			if perOrg[org][KindSingle] == 0 || perOrg[org][KindMulti] == 0 || admins[org] != 1 {
				t.Errorf("%s: org %d has %v and %d admins", name, org, perOrg[org], admins[org])
			}
		}
		if singles != tier.Developers-tier.Developers/2 || multis != tier.Developers/2 {
			t.Errorf("%s: %d single, %d multi developers", name, singles, multis)
		}
	}
}
