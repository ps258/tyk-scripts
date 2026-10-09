package inventory

import (
	"context"
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
)

const keyPrefix = "apikey-"

type session struct {
	OrgID         string         `json:"org_id"`
	Alias         string         `json:"alias"`
	ApplyPolicies []string       `json:"apply_policies"`
	ApplyPolicyID string         `json:"apply_policy_id"`
	Tags          []string       `json:"tags"`
	MetaData      map[string]any `json:"meta_data"`
	AccessRights  map[string]struct {
		APIID    string   `json:"api_id"`
		Versions []string `json:"versions"`
	} `json:"access_rights"`
	Expires       int64  `json:"expires"`
	IsInactive    bool   `json:"is_inactive"`
	OauthClientID string `json:"oauth_client_id"`
}

type KeyOptions struct {
	IncludeExpired bool
	// PolicyTags maps policy ID to that policy's tags. The gateway merges these
	// into the session's tags when it applies the policies.
	PolicyTags map[string][]string
}

// LoadKeys scans Redis for apikey-* sessions belonging to inv.OrgID.
func LoadKeys(ctx context.Context, rdb redis.UniversalClient, inv *Inventory, opts KeyOptions) error {
	names, err := scanKeys(ctx, rdb, keyPrefix+"*")
	if err != nil {
		return err
	}

	var skippedOrg, skippedNoAccess, skippedExpired, skippedInactive, skippedBad int
	now := time.Now().Unix()

	const batch = 500
	for start := 0; start < len(names); start += batch {
		chunk := names[start:min(start+batch, len(names))]
		vals, err := mget(ctx, rdb, chunk)
		if err != nil {
			return err
		}
		for i, raw := range vals {
			if raw == "" {
				continue
			}
			var s session
			if err := json.Unmarshal([]byte(raw), &s); err != nil {
				skippedBad++
				continue
			}
			switch {
			case s.OrgID != inv.OrgID:
				skippedOrg++
				continue
			case len(s.AccessRights) == 0:
				skippedNoAccess++
				continue
			case s.IsInactive:
				skippedInactive++
				continue
			case s.Expires > 0 && s.Expires < now && !opts.IncludeExpired:
				skippedExpired++
				continue
			}
			inv.Keys = append(inv.Keys, toKey(strings.TrimPrefix(chunk[i], keyPrefix), &s, opts.PolicyTags))
		}
	}

	if skippedNoAccess+skippedExpired+skippedInactive+skippedBad > 0 {
		inv.warnf("skipped keys: %d without access rights, %d expired, %d inactive, %d unparseable (%d belonged to other orgs)",
			skippedNoAccess, skippedExpired, skippedInactive, skippedBad, skippedOrg)
	}
	return nil
}

func toKey(id string, s *session, policyTags map[string][]string) Key {
	policies := s.ApplyPolicies
	if len(policies) == 0 && s.ApplyPolicyID != "" {
		policies = []string{s.ApplyPolicyID}
	}

	// Effective session tags: the set union of the session's own tags and the
	// tags of every applied policy (tyk/gateway/middleware.go applyPolicies).
	seen := map[string]bool{}
	var tags []string
	add := func(ts []string) {
		for _, t := range ts {
			if !seen[t] {
				seen[t] = true
				tags = append(tags, t)
			}
		}
	}
	add(s.Tags)
	for _, p := range policies {
		add(policyTags[p])
	}

	k := Key{
		ID:            id,
		Alias:         s.Alias,
		Policies:      policies,
		Tags:          tags,
		OAuthClientID: s.OauthClientID,
		Access:        map[string][]string{},
	}
	if dev, ok := s.MetaData["tyk_developer_id"].(string); ok {
		k.DeveloperID = dev
	}
	for apiID, ar := range s.AccessRights {
		if ar.APIID != "" {
			apiID = ar.APIID
		}
		vs := append([]string(nil), ar.Versions...)
		sort.Strings(vs)
		k.Access[apiID] = vs
	}
	return k
}

func scanKeys(ctx context.Context, rdb redis.UniversalClient, match string) ([]string, error) {
	var (
		mu  sync.Mutex
		out []string
	)
	scan := func(ctx context.Context, c *redis.Client) error {
		iter := c.Scan(ctx, 0, match, 1000).Iterator()
		for iter.Next(ctx) {
			mu.Lock()
			out = append(out, iter.Val())
			mu.Unlock()
		}
		return iter.Err()
	}

	var err error
	switch c := rdb.(type) {
	case *redis.ClusterClient:
		err = c.ForEachMaster(ctx, scan)
	case *redis.Client:
		err = scan(ctx, c)
	default:
		return nil, fmt.Errorf("unsupported redis client type %T", rdb)
	}
	if err != nil {
		return nil, fmt.Errorf("scan %s: %w", match, err)
	}
	sort.Strings(out)
	return out, nil
}

// mget fetches values with a pipeline of GETs, which also works across
// cluster slots.
func mget(ctx context.Context, rdb redis.UniversalClient, keys []string) ([]string, error) {
	pipe := rdb.Pipeline()
	cmds := make([]*redis.StringCmd, len(keys))
	for i, k := range keys {
		cmds[i] = pipe.Get(ctx, k)
	}
	// Exec reports the first failed command, which may just be a key that
	// expired since the scan, so judge each command on its own.
	_, _ = pipe.Exec(ctx)
	out := make([]string, len(keys))
	var firstErr error
	failed := 0
	for i, c := range cmds {
		v, err := c.Result()
		switch {
		case err == nil:
			out[i] = v
		case err != redis.Nil:
			failed++
			if firstErr == nil {
				firstErr = err
			}
		}
	}
	if failed == len(keys) && firstErr != nil {
		return nil, fmt.Errorf("get sessions: %w", firstErr)
	}
	return out, nil
}
