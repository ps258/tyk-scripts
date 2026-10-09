package portal

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"sync/atomic"
)

// Cleanup deletes the objects Provision created for prefix, dependents first.
// Deleting an app also revokes its credentials, and deleting a product or
// plan removes its Dashboard policy. With dryRun it only counts.
func Cleanup(ctx context.Context, c *Client, prefix string, conc int, dryRun bool) (map[string]int, error) {
	// Names from before developers were split by kind (<prefix>-dev-NNNN,
	// <prefix>-app-NNNNN) are matched too.
	owned := func(name string, kinds ...string) bool {
		for _, k := range kinds {
			if strings.HasPrefix(name, prefix+"-"+k+"-") {
				return true
			}
		}
		return false
	}
	steps := []struct {
		kind, path string
		match      func(item) bool
	}{
		{"apps", "/apps", func(it item) bool { return owned(it.Name, "app", KindSingle, KindMulti) }},
		{"developers", "/users", func(it item) bool {
			e := strings.ToLower(it.Email)
			return owned(e, "dev", KindSingle, KindMulti) && strings.HasSuffix(e, "@"+prefix+".test")
		}},
		{"organisations", "/organisations", func(it item) bool { return strings.HasPrefix(it.Name, prefix+"-org-") }},
		{"catalogues", "/catalogues", func(it item) bool { return it.Name == prefix+"-catalogue" }},
		{"plans", "/plans", func(it item) bool { return strings.HasPrefix(it.Name, prefix+"-plan-") }},
		{"products", "/products", func(it item) bool { return strings.HasPrefix(it.Name, prefix+"-product-") }},
	}

	counts := map[string]int{}
	for _, s := range steps {
		all, err := ListAll[item](ctx, c, s.path)
		if err != nil {
			return counts, fmt.Errorf("list %s: %w", s.kind, err)
		}
		var ids []uint
		for _, it := range all {
			if s.match(it) {
				ids = append(ids, it.ID)
			}
		}
		if dryRun {
			counts[s.kind] = len(ids)
			continue
		}
		var done atomic.Int64
		stop := progress("deleting "+s.kind, &done, int64(len(ids)))
		err = forEach(ctx, len(ids), max(1, conc), func(i int) error {
			if err := c.Do(ctx, http.MethodDelete, fmt.Sprintf("%s/%d", s.path, ids[i]), nil, nil); err != nil {
				return fmt.Errorf("delete %s %d: %w", s.kind, ids[i], err)
			}
			done.Add(1)
			return nil
		})
		stop()
		counts[s.kind] = int(done.Load())
		if err != nil {
			return counts, err
		}
	}
	return counts, nil
}
