// Package inventory reads the live APIs, policies and keys of a Tyk deployment
// that generated traffic is attributed to.
package inventory

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"time"
)

// NonVersioned is the version name the gateway records when a request does
// not select a version (tyk/gateway/handler_success.go).
const NonVersioned = "Non Versioned"

type Inventory struct {
	OrgID       string    `json:"org_id"`
	GeneratedAt time.Time `json:"generated_at"`
	APIs        []API     `json:"apis"`
	Policies    []Policy  `json:"policies"`
	Keys        []Key     `json:"keys"`
	Warnings    []string  `json:"warnings,omitempty"`
}

type API struct {
	ID       string   `json:"id"`
	Name     string   `json:"name"`
	Tags     []string `json:"tags,omitempty"`
	Versions []string `json:"versions"` // analytics version names, NonVersioned first
	Keyless  bool     `json:"keyless,omitempty"`
	Active   bool     `json:"active"`
}

type Policy struct {
	ID string `json:"id"` // Mongo _id (hex)
	// CustomID is the policy's "id" field when it has one; sessions may refer
	// to the policy by either.
	CustomID string   `json:"custom_id,omitempty"`
	Name     string   `json:"name"`
	APIs     []string `json:"apis"`
}

// Key is a session read from Redis.
type Key struct {
	// ID is the Redis key without the "apikey-" prefix. It is the hash when the
	// gateway hashes keys and the raw key otherwise, which is exactly what the
	// gateway records as the analytics APIKey.
	ID       string   `json:"id"`
	Alias    string   `json:"alias,omitempty"`
	Policies []string `json:"policies,omitempty"`
	// Tags are the effective session tags: the session's own tags plus the
	// tags of its applied policies.
	Tags          []string            `json:"tags,omitempty"`
	DeveloperID   string              `json:"developer_id,omitempty"`
	OAuthClientID string              `json:"oauth_client_id,omitempty"`
	Access        map[string][]string `json:"access"` // api id -> definition version names
}

func (inv *Inventory) warnf(format string, args ...any) {
	inv.Warnings = append(inv.Warnings, fmt.Sprintf(format, args...))
}

// Validate drops key access to APIs that are not in the inventory and records
// warnings for anything that will not produce traffic.
func (inv *Inventory) Validate() {
	apis := map[string]bool{}
	for _, a := range inv.APIs {
		apis[a.ID] = true
	}
	pols := map[string]bool{}
	for _, p := range inv.Policies {
		pols[p.ID] = true
		if p.CustomID != "" {
			pols[p.CustomID] = true
		}
	}

	reachable := map[string]bool{}
	for i := range inv.Keys {
		k := &inv.Keys[i]
		for apiID := range k.Access {
			if !apis[apiID] {
				inv.warnf("key %s grants unknown or inactive API %s; ignoring that access", short(k.ID), apiID)
				delete(k.Access, apiID)
				continue
			}
			reachable[apiID] = true
		}
		for _, p := range k.Policies {
			if !pols[p] {
				inv.warnf("key %s applies policy %s which was not found in the policies collection", short(k.ID), p)
			}
		}
	}
	for _, a := range inv.APIs {
		if !a.Keyless && !reachable[a.ID] {
			inv.warnf("API %q (%s) needs auth but no key grants access to it; it will get no traffic", a.Name, a.ID)
		}
	}
}

func short(s string) string {
	if len(s) > 12 {
		return s[:12] + "…"
	}
	return s
}

func (inv *Inventory) sort() {
	sort.Slice(inv.APIs, func(i, j int) bool { return inv.APIs[i].ID < inv.APIs[j].ID })
	sort.Slice(inv.Policies, func(i, j int) bool { return inv.Policies[i].ID < inv.Policies[j].ID })
	sort.Slice(inv.Keys, func(i, j int) bool { return inv.Keys[i].ID < inv.Keys[j].ID })
}

func Load(path string) (*Inventory, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var inv Inventory
	if err := json.Unmarshal(b, &inv); err != nil {
		return nil, fmt.Errorf("parse %s: %w", path, err)
	}
	inv.sort()
	return &inv, nil
}

func (inv *Inventory) Save(path string) error {
	b, err := json.MarshalIndent(inv, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, b, 0o644)
}

// Summary is a short human readable description of the inventory.
func (inv *Inventory) Summary() string {
	keyless := 0
	for _, a := range inv.APIs {
		if a.Keyless {
			keyless++
		}
	}
	return fmt.Sprintf("org %s: %d APIs (%d keyless), %d policies, %d keys, %d warnings",
		inv.OrgID, len(inv.APIs), keyless, len(inv.Policies), len(inv.Keys), len(inv.Warnings))
}
