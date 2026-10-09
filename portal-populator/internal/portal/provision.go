package portal

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

// item is the common shape of portal list entries we care about.
type item struct {
	ID             uint   `json:"ID"`
	Name           string `json:"Name"`
	Email          string `json:"Email"`
	Type           string `json:"Type"`
	OrganisationID uint   `json:"OrganisationID"`
}

type Options struct {
	ProviderID  uint
	Concurrency int
	// Password is sent for each developer when non-empty.
	Password string
	// Visibility of created apps. "personal" keeps each developer's analytics
	// to their own apps; "organisation" makes every org member see every app
	// in the org, which changes how many tags the portal sends.
	Visibility string
}

type Result struct {
	Created  map[string]int
	Existing map[string]int
}

func (r *Result) add(kind string, created, existing int) {
	r.Created[kind] += created
	r.Existing[kind] += existing
}

// ResolveProvider returns the provider to attach products and plans to: the
// given ID, or the only provider when id is 0.
func ResolveProvider(ctx context.Context, c *Client, id uint) (uint, error) {
	if id != 0 {
		var it item
		if err := c.Do(ctx, http.MethodGet, fmt.Sprintf("/providers/%d", id), nil, &it); err != nil {
			return 0, fmt.Errorf("provider %d: %w", id, err)
		}
		return id, nil
	}
	providers, err := ListAll[item](ctx, c, "/providers")
	if err != nil {
		return 0, fmt.Errorf("list providers: %w", err)
	}
	switch len(providers) {
	case 0:
		return 0, fmt.Errorf("the portal has no provider; add the Dashboard as a provider first")
	case 1:
		return providers[0].ID, nil
	}
	var names []string
	for _, p := range providers {
		names = append(names, fmt.Sprintf("%d (%s)", p.ID, p.Name))
	}
	return 0, fmt.Errorf("the portal has %d providers, pass --provider-id: %s", len(providers), strings.Join(names, ", "))
}

// Provision creates everything in plan that does not exist yet. Objects are
// matched by name (email for developers), so an interrupted run can simply be
// repeated.
func Provision(ctx context.Context, c *Client, plan *Plan, opts Options) (*Result, error) {
	res := &Result{Created: map[string]int{}, Existing: map[string]int{}}
	conc := max(1, opts.Concurrency)

	productIDs, err := ensure(ctx, c, res, "products", "/products", len(plan.Products), conc, byName,
		func(i int) string { return plan.Products[i].Name },
		func(i int) any {
			ps := plan.Products[i]
			details := make([]map[string]string, 0, len(ps.APIIDs))
			for _, id := range ps.APIIDs {
				details = append(details, map[string]string{"APIID": id})
			}
			return map[string]any{
				"Name":                ps.Name,
				"DisplayName":         ps.Name,
				"Description":         "Stress-test product",
				"ProviderID":          opts.ProviderID,
				"IsDocumentationOnly": false,
				"APIDetails":          details,
			}
		})
	if err != nil {
		return res, err
	}

	planIDs, err := ensure(ctx, c, res, "plans", "/plans", len(plan.Plans), conc, byName,
		func(i int) string { return plan.Plans[i].Name },
		func(i int) any {
			ps := plan.Plans[i]
			return map[string]any{
				"Name":                      ps.Name,
				"DisplayName":               ps.Name,
				"Description":               "Stress-test plan",
				"ProviderID":                opts.ProviderID,
				"AutoApproveAccessRequests": true,
				"RateLimit":                 ps.Rate,
				"Per":                       ps.Per,
				"Quota":                     ps.Quota,
				"QuotaRenewalRate":          ps.Renewal,
			}
		})
	if err != nil {
		return res, err
	}

	// One public catalogue holding every product and plan so the combinations
	// are visible to developers. Arrays replace the association, so the PUT
	// is safe to repeat.
	catIDs, err := ensure(ctx, c, res, "catalogues", "/catalogues", 1, 1, byName,
		func(int) string { return plan.Catalogue },
		func(int) any {
			return catalogueBody(plan.Catalogue, productIDs, planIDs)
		})
	if err != nil {
		return res, err
	}
	if err := c.Do(ctx, http.MethodPut, fmt.Sprintf("/catalogues/%d", catIDs[0]),
		catalogueBody(plan.Catalogue, productIDs, planIDs), nil); err != nil {
		return res, fmt.Errorf("update catalogue: %w", err)
	}

	orgIDs, err := ensure(ctx, c, res, "organisations", "/organisations", len(plan.Orgs), conc, byName,
		func(i int) string { return plan.Orgs[i] },
		func(i int) any { return map[string]any{"Name": plan.Orgs[i]} })
	if err != nil {
		return res, err
	}

	orgID := func(i int) uint {
		if i < 0 {
			return DefaultOrgID
		}
		return orgIDs[i]
	}

	// Existing developers are reused by email, so one left in a different
	// organisation by an earlier run (e.g. before --default-org) would keep
	// seeing that organisation's apps. Refuse rather than mix layouts.
	if err := checkDevOrgs(ctx, c, plan, orgID); err != nil {
		return res, err
	}

	devIDs, err := ensure(ctx, c, res, "developers", "/users", len(plan.Devs), conc, byEmail,
		func(i int) string { return plan.Devs[i].Email },
		func(i int) any {
			d := plan.Devs[i]
			body := map[string]any{
				"Email":          d.Email,
				"First":          d.First,
				"Last":           d.Last,
				"Role":           d.Role,
				"Active":         true,
				"OrganisationID": orgID(d.Org),
				"Provider":       "password",
			}
			if opts.Password != "" {
				body["Password"] = opts.Password
			}
			return body
		})
	if err != nil {
		return res, err
	}

	created := make([]bool, len(plan.Apps))
	appIDs, err := ensureTracked(ctx, c, res, "apps", "/apps", len(plan.Apps), conc, byName,
		func(i int) string { return plan.Apps[i].Name },
		func(i int) any {
			return map[string]any{
				"Name":        plan.Apps[i].Name,
				"Description": "Stress-test app",
				"UserID":      devIDs[plan.Apps[i].Dev],
				"Visibility":  opts.Visibility,
			}
		}, created)
	if err != nil {
		return res, err
	}

	// Access requests: provision immediately (plans also auto-approve). For
	// apps from an earlier run, only the missing requests are provisioned.
	var done, skipped atomic.Int64
	stop := progress("access requests", &done, int64(plan.Credentials()))
	defer stop()
	err = forEach(ctx, len(plan.Apps), conc, func(i int) error {
		app := plan.Apps[i]
		have := 0
		if !created[i] {
			ars, err := ListAll[item](ctx, c, fmt.Sprintf("/apps/%d/access-requests", appIDs[i]))
			if err != nil {
				return fmt.Errorf("app %s: list access requests: %w", app.Name, err)
			}
			have = len(ars)
		}
		for j, rq := range app.Requests {
			if j < have {
				skipped.Add(1)
				done.Add(1)
				continue
			}
			body := map[string]any{
				"ProductIDs":           []uint{productIDs[rq.Product]},
				"PlanID":               planIDs[rq.Plan],
				"ProvisionImmediately": true,
			}
			if err := c.Do(ctx, http.MethodPut, fmt.Sprintf("/apps/%d/provision", appIDs[i]), body, nil); err != nil {
				return fmt.Errorf("app %s: provision: %w", app.Name, err)
			}
			done.Add(1)
		}
		return nil
	})
	res.add("access requests", int(done.Load()-skipped.Load()), int(skipped.Load()))
	return res, err
}

// catalogueBody builds a catalogue create/update. The portal requires the
// URL slug (NameWithSlug) as well as the name; plan names are slug-safe.
func catalogueBody(name string, productIDs, planIDs []uint) map[string]any {
	return map[string]any{
		"Name":             name,
		"NameWithSlug":     name,
		"VisibilityStatus": "Public",
		"Products":         productIDs,
		"Plans":            planIDs,
	}
}

func checkDevOrgs(ctx context.Context, c *Client, plan *Plan, orgID func(int) uint) error {
	users, err := ListAll[item](ctx, c, "/users")
	if err != nil {
		return fmt.Errorf("list developers: %w", err)
	}
	want := make(map[string]uint, len(plan.Devs))
	for _, d := range plan.Devs {
		want[strings.ToLower(d.Email)] = orgID(d.Org)
	}
	wrong := 0
	for _, u := range users {
		if org, ok := want[strings.ToLower(u.Email)]; ok && u.OrganisationID != org {
			wrong++
		}
	}
	if wrong > 0 {
		return fmt.Errorf("%d existing %s developers are in a different organisation than this run puts them in; "+
			"run cleanup first or use another --prefix", wrong, plan.Prefix)
	}
	return nil
}

func byName(it item) string  { return it.Name }
func byEmail(it item) string { return strings.ToLower(it.Email) }

func ensure(ctx context.Context, c *Client, res *Result, kind, path string, n, conc int,
	key func(item) string, name func(int) string, body func(int) any) ([]uint, error) {
	return ensureTracked(ctx, c, res, kind, path, n, conc, key, name, body, nil)
}

// ensureTracked returns the IDs of n objects, creating those whose name is
// not already present at path. created (when non-nil) records which were new.
func ensureTracked(ctx context.Context, c *Client, res *Result, kind, path string, n, conc int,
	key func(item) string, name func(int) string, body func(int) any, created []bool) ([]uint, error) {

	existing, err := ListAll[item](ctx, c, path)
	if err != nil {
		return nil, fmt.Errorf("list %s: %w", kind, err)
	}
	byKey := make(map[string]uint, len(existing))
	for _, it := range existing {
		byKey[key(it)] = it.ID
	}

	ids := make([]uint, n)
	var missing []int
	for i := range n {
		if id, ok := byKey[strings.ToLower(name(i))]; ok {
			ids[i] = id
		} else if id, ok := byKey[name(i)]; ok {
			ids[i] = id
		} else {
			missing = append(missing, i)
		}
	}

	var done atomic.Int64
	stop := progress(kind, &done, int64(len(missing)))
	defer stop()
	err = forEach(ctx, len(missing), conc, func(k int) error {
		i := missing[k]
		var it item
		if err := c.Do(ctx, http.MethodPost, path, body(i), &it); err != nil {
			return fmt.Errorf("create %s %q: %w", kind, name(i), err)
		}
		if it.ID == 0 {
			return fmt.Errorf("create %s %q: response had no ID", kind, name(i))
		}
		ids[i] = it.ID
		if created != nil {
			created[i] = true
		}
		done.Add(1)
		return nil
	})
	res.add(kind, int(done.Load()), n-len(missing))
	return ids, err
}

// forEach runs fn for 0..n-1 on conc workers and returns the first error.
func forEach(ctx context.Context, n, conc int, fn func(int) error) error {
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	jobs := make(chan int)
	var (
		wg       sync.WaitGroup
		once     sync.Once
		firstErr error
	)
	for range min(conc, max(n, 1)) {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for i := range jobs {
				if err := fn(i); err != nil {
					once.Do(func() { firstErr = err; cancel() })
				}
			}
		}()
	}
	for i := range n {
		select {
		case jobs <- i:
		case <-ctx.Done():
		}
		if ctx.Err() != nil {
			break
		}
	}
	close(jobs)
	wg.Wait()
	if firstErr == nil && ctx.Err() != nil {
		return context.Cause(ctx)
	}
	return firstErr
}

// progress logs a counter every 10s until the returned func is called.
func progress(kind string, done *atomic.Int64, total int64) func() {
	if total == 0 {
		return func() {}
	}
	t := time.NewTicker(10 * time.Second)
	quit := make(chan struct{})
	go func() {
		for {
			select {
			case <-t.C:
				log.Printf("  %s: %d/%d", kind, done.Load(), total)
			case <-quit:
				return
			}
		}
	}()
	return func() { t.Stop(); close(quit) }
}
