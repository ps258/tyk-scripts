package portal

import (
	"context"
	"encoding/csv"
	"fmt"
	"io"
	"sort"
	"strings"
	"sync/atomic"
)

// ExportColumns is the header of the developers CSV. There is one row per
// app; developer columns repeat on each of their apps' rows.
var ExportColumns = []string{
	"email", "kind", "number", "app_count", "password", "role",
	"organisation", "org_tag", "app_name", "app_id", "app_tag", "keys", "key_hashes",
}

type credential struct {
	Credential     string `json:"Credential"`
	CredentialHash string `json:"CredentialHash"`
}

type userItem struct {
	item
	Role string `json:"Role"`
}

// Export writes the developers CSV for the developers and apps Provision
// created under prefix. It reads everything back from the portal and finds
// each app's owner from the app's name, so it can run on its own after
// provisioning. Several values in one cell (keys) are separated by spaces.
func Export(ctx context.Context, c *Client, prefix, password string, conc int, w io.Writer) (rows int, err error) {
	users, err := ListAll[userItem](ctx, c, "/users")
	if err != nil {
		return 0, fmt.Errorf("list developers: %w", err)
	}
	orgs, err := ListAll[item](ctx, c, "/organisations")
	if err != nil {
		return 0, fmt.Errorf("list organisations: %w", err)
	}
	apps, err := ListAll[item](ctx, c, "/apps")
	if err != nil {
		return 0, fmt.Errorf("list apps: %w", err)
	}

	orgNames := map[uint]string{DefaultOrgID: "Default Organisation"}
	for _, o := range orgs {
		orgNames[o.ID] = o.Name
	}
	devs := map[string]userItem{}
	for _, u := range users {
		devs[strings.ToLower(u.Email)] = u
	}

	type row struct {
		dev        userItem
		owner      string
		kind, num  string
		app        item
		keys, hash []string
	}
	var out []*row
	appCount := map[string]int{}
	for _, a := range apps {
		owner, kind, num, ok := parseAppName(prefix, a.Name)
		if !ok {
			continue
		}
		email := owner + "@" + prefix + ".test"
		u, ok := devs[email]
		if !ok {
			continue
		}
		appCount[email]++
		out = append(out, &row{dev: u, owner: email, kind: kind, num: num, app: a})
	}

	var done atomic.Int64
	stop := progress("export: apps read", &done, int64(len(out)))
	defer stop()
	err = forEach(ctx, len(out), max(1, conc), func(i int) error {
		r := out[i]
		ars, err := ListAll[item](ctx, c, fmt.Sprintf("/apps/%d/access-requests", r.app.ID))
		if err != nil {
			return fmt.Errorf("app %s: list access requests: %w", r.app.Name, err)
		}
		var keys, hashes []string
		for _, ar := range ars {
			creds, err := ListAll[credential](ctx, c, fmt.Sprintf("/apps/%d/access-requests/%d/credentials", r.app.ID, ar.ID))
			if err != nil {
				return fmt.Errorf("app %s: list credentials: %w", r.app.Name, err)
			}
			for _, cr := range creds {
				keys = append(keys, cr.Credential)
				hashes = append(hashes, cr.CredentialHash)
			}
		}
		r.keys, r.hash = keys, hashes
		done.Add(1)
		return nil
	})
	if err != nil {
		return 0, err
	}

	sort.Slice(out, func(i, j int) bool {
		a, b := out[i], out[j]
		if a.kind != b.kind {
			return a.kind == KindSingle
		}
		if a.num != b.num {
			return a.num < b.num
		}
		return a.app.Name < b.app.Name
	})

	cw := csv.NewWriter(w)
	if err := cw.Write(ExportColumns); err != nil {
		return 0, err
	}
	for _, r := range out {
		org := r.dev.OrganisationID
		if err := cw.Write([]string{
			r.owner, r.kind, r.num, fmt.Sprint(appCount[r.owner]), password, r.dev.Role,
			orgNames[org], MakeTag("org", org), r.app.Name, fmt.Sprint(r.app.ID), MakeTag("app", r.app.ID),
			strings.Join(r.keys, " "), strings.Join(r.hash, " "),
		}); err != nil {
			return 0, err
		}
	}
	cw.Flush()
	return len(out), cw.Error()
}

// MakeTag is the analytics tag the portal puts on a credential's key, e.g.
// portal-app-12 for app 12 and portal-org-3 for organisation 3.
func MakeTag(kind string, id uint) string {
	return fmt.Sprintf("portal-%s-%d", kind, id)
}

// parseAppName splits <prefix>-<kind>-NNNN-app[-NN] into the owner's email
// local part, the kind and the developer number.
func parseAppName(prefix, name string) (owner, kind, num string, ok bool) {
	for _, k := range []string{KindSingle, KindMulti} {
		rest, found := strings.CutPrefix(name, prefix+"-"+k+"-")
		if !found {
			continue
		}
		num, suffix, found := strings.Cut(rest, "-app")
		if !found || num == "" || (suffix != "" && !strings.HasPrefix(suffix, "-")) {
			return "", "", "", false
		}
		return prefix + "-" + k + "-" + num, k, num, true
	}
	return "", "", "", false
}
