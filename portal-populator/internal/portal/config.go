// Package portal provisions Enterprise Developer Portal objects (products,
// plans, catalogue, organisations, developers, apps and approved access
// requests) for the APIs in a Tyk Dashboard, so that real portal credentials
// exist for testing.
package portal

import (
	"fmt"
	"math"
	"math/rand/v2"
	"sort"
	"strings"
)

// Tier sizes the portal objects to create.
type Tier struct {
	Plans          int
	Products       int
	APIsPerProduct int
	Orgs           int
	Developers     int
	// HeavyDevelopers own HeavyApps apps each; everyone else owns one. The
	// presets use half the developers, and the command keeps it at half
	// when --developers is overridden (see DefaultHeavy).
	HeavyDevelopers int
	HeavyApps       int
	// CredentialsPerApp is the average number of access requests per app;
	// the fractional part is applied randomly (seeded).
	CredentialsPerApp float64
	// DefaultOrg puts every developer in the portal's Default Organisation
	// instead of creating organisations. Default-org developers only see
	// their own apps; in portals before v1.14 developers in any other
	// organisation see every app in it.
	DefaultOrg bool
}

// DefaultOrgID is the portal's built-in Default Organisation.
const DefaultOrgID = 1

// Tiers match the stress-test sizing discussed for the developer dashboard.
var Tiers = map[string]Tier{
	"small":  {Plans: 5, Products: 20, APIsPerProduct: 3, Orgs: 5, Developers: 50, HeavyDevelopers: 25, HeavyApps: 25, CredentialsPerApp: 1.5},
	"medium": {Plans: 10, Products: 50, APIsPerProduct: 3, Orgs: 20, Developers: 500, HeavyDevelopers: 250, HeavyApps: 50, CredentialsPerApp: 1.5},
	"large":  {Plans: 20, Products: 100, APIsPerProduct: 3, Orgs: 50, Developers: 2000, HeavyDevelopers: 1000, HeavyApps: 50, CredentialsPerApp: 1.25},
	"xlarge": {Plans: 20, Products: 100, APIsPerProduct: 3, Orgs: 50, Developers: 2500, HeavyDevelopers: 1250, HeavyApps: 50, CredentialsPerApp: 1.4},
}

// DefaultHeavy is the number of heavy developers when none is given: half
// the developers, rounded down.
func (t Tier) DefaultHeavy() int {
	return t.Developers / 2
}

func TierNames() []string {
	names := make([]string, 0, len(Tiers))
	for n := range Tiers {
		names = append(names, n)
	}
	sort.Slice(names, func(i, j int) bool { return Tiers[names[i]].Developers < Tiers[names[j]].Developers })
	return names
}

func (t Tier) Validate() error {
	switch {
	case t.Plans < 1, t.Products < 1, t.APIsPerProduct < 1, t.Developers < 1:
		return fmt.Errorf("plans, products, apis-per-product and developers must all be at least 1")
	case t.Orgs < 1 && !t.DefaultOrg:
		return fmt.Errorf("orgs must be at least 1 unless developers go in the Default Organisation")
	case t.HeavyDevelopers < 0 || t.HeavyDevelopers > t.Developers:
		return fmt.Errorf("heavy-developers must be between 0 and developers")
	case t.HeavyDevelopers > 0 && t.HeavyApps < 2:
		return fmt.Errorf("heavy-apps must be at least 2")
	case t.CredentialsPerApp < 1:
		return fmt.Errorf("credentials-per-app must be at least 1")
	}
	return nil
}

// Plan is the full, deterministic set of objects to create. Names embed the
// prefix so a re-run can find and adopt what already exists, and cleanup can
// find everything it created.
type Plan struct {
	Prefix    string
	Products  []ProductSpec
	Plans     []PlanSpec
	Catalogue string
	Orgs      []string
	Devs      []DevSpec
	Apps      []AppSpec
}

type ProductSpec struct {
	Name   string
	APIIDs []string
}

type PlanSpec struct {
	Name    string
	Rate    int
	Per     int
	Quota   int
	Renewal int
}

type DevSpec struct {
	// Name is the email's local part: <prefix>-single-NNNN for developers
	// with one app, <prefix>-multi-NNNN for heavy developers. Each kind is
	// numbered from 0001.
	Name  string
	Email string
	First string
	Last  string
	Org   int // index into Plan.Orgs, or -1 for the Default Organisation
	Role  string
	Heavy bool
}

// Developer kinds, as used in names.
const (
	KindSingle = "single"
	KindMulti  = "multi"
)

func (d DevSpec) Kind() string {
	if d.Heavy {
		return KindMulti
	}
	return KindSingle
}

type AppSpec struct {
	Name string
	Dev  int // index into Plan.Devs
	// Requests holds one access request per entry: product index and plan index.
	Requests []RequestSpec
}

type RequestSpec struct {
	Product int
	Plan    int
}

// BuildPlan lays out every object for the tier over the eligible APIs.
func BuildPlan(prefix string, t Tier, apiIDs []string, seed uint64) (*Plan, error) {
	if err := t.Validate(); err != nil {
		return nil, err
	}
	if len(apiIDs) == 0 {
		return nil, fmt.Errorf("no eligible APIs")
	}
	r := rand.New(rand.NewPCG(seed, 0x9047a1))
	p := &Plan{Prefix: prefix, Catalogue: prefix + "-catalogue"}

	// Products take consecutive windows of APIs so every API is in at least
	// one product when there are enough products.
	per := min(t.APIsPerProduct, len(apiIDs))
	for i := range t.Products {
		ps := ProductSpec{Name: fmt.Sprintf("%s-product-%03d", prefix, i+1)}
		for j := range per {
			ps.APIIDs = append(ps.APIIDs, apiIDs[(i*per+j)%len(apiIDs)])
		}
		p.Products = append(p.Products, ps)
	}

	// Plans range from modest to generous; limits are high enough not to get
	// in the way of anyone generating real traffic.
	for i := range t.Plans {
		rate := 100 * int(math.Pow(2, float64(i%8)))
		p.Plans = append(p.Plans, PlanSpec{
			Name:    fmt.Sprintf("%s-plan-%02d", prefix, i+1),
			Rate:    rate,
			Per:     60,
			Quota:   rate * 60 * 24 * 30,
			Renewal: 2592000,
		})
	}

	if !t.DefaultOrg {
		for i := range t.Orgs {
			p.Orgs = append(p.Orgs, fmt.Sprintf("%s-org-%02d", prefix, i+1))
		}
	}

	// Heavy developers are spread evenly through the list.
	heavy := map[int]bool{}
	if t.HeavyDevelopers > 0 {
		step := t.Developers / t.HeavyDevelopers
		for i := range t.HeavyDevelopers {
			heavy[i*step+step/2] = true
		}
	}
	orgHasAdmin := map[int]bool{}
	kindCount := map[bool]int{}
	for i := range t.Developers {
		// Default-org developers are consumer-admins, as self-registered
		// developers are. Otherwise each kind is dealt round-robin across
		// the organisations separately, so every organisation gets its
		// share of both kinds wherever the heavy developers sit in the list.
		org, role := -1, "consumer-admin"
		if !t.DefaultOrg {
			org, role = kindCount[heavy[i]]%t.Orgs, "consumer-team-member"
			if !orgHasAdmin[org] {
				role, orgHasAdmin[org] = "consumer-admin", true
			}
		}
		kindCount[heavy[i]]++
		d := DevSpec{Org: org, Role: role, Heavy: heavy[i]}
		n := fmt.Sprintf("%04d", kindCount[heavy[i]])
		d.Name = fmt.Sprintf("%s-%s-%s", prefix, d.Kind(), n)
		d.Email = d.Name + "@" + prefix + ".test"
		d.First, d.Last = strings.ToUpper(d.Kind()[:1])+d.Kind()[1:], n
		p.Devs = append(p.Devs, d)
	}

	// Apps are named after their developer so a name identifies its owner:
	// <dev>-app for single-app developers, <dev>-app-NN for heavy ones.
	appWidth := max(2, len(fmt.Sprint(t.HeavyApps)))

	whole := int(t.CredentialsPerApp)
	frac := t.CredentialsPerApp - float64(whole)
	for di, d := range p.Devs {
		n := 1
		if d.Heavy {
			n = t.HeavyApps
		}
		for k := range n {
			a := AppSpec{Name: d.Name + "-app", Dev: di}
			if d.Heavy {
				a.Name = fmt.Sprintf("%s-app-%0*d", d.Name, appWidth, k+1)
			}
			reqs := whole
			if r.Float64() < frac {
				reqs++
			}
			used := map[int]bool{}
			for range reqs {
				prod := r.IntN(len(p.Products))
				for used[prod] && len(used) < len(p.Products) {
					prod = r.IntN(len(p.Products))
				}
				used[prod] = true
				a.Requests = append(a.Requests, RequestSpec{Product: prod, Plan: r.IntN(len(p.Plans))})
			}
			p.Apps = append(p.Apps, a)
		}
	}
	return p, nil
}

// Credentials returns the number of access requests in the plan.
func (p *Plan) Credentials() int {
	n := 0
	for _, a := range p.Apps {
		n += len(a.Requests)
	}
	return n
}
