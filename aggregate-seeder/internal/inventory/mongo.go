package inventory

import (
	"context"
	"fmt"
	"sort"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
)

type apiDef struct {
	APIID       string   `bson:"api_id"`
	Name        string   `bson:"name"`
	OrgID       string   `bson:"org_id"`
	Tags        []string `bson:"tags"`
	Active      bool     `bson:"active"`
	UseKeyless  bool     `bson:"use_keyless"`
	VersionData struct {
		NotVersioned bool                `bson:"not_versioned"`
		Versions     map[string]bson.Raw `bson:"versions"`
	} `bson:"version_data"`
}

// apiDoc accepts both storage shapes used by Dashboard versions: the
// definition nested under api_definition (older) or at the top level (newer).
type apiDoc struct {
	Nested *apiDef `bson:"api_definition"`
	Flat   apiDef  `bson:",inline"`
}

func (d *apiDoc) def() apiDef {
	if d.Nested != nil && d.Nested.APIID != "" {
		return *d.Nested
	}
	return d.Flat
}

type policyDoc struct {
	MID          primitive.ObjectID  `bson:"_id"`
	ID           string              `bson:"id"`
	Name         string              `bson:"name"`
	OrgID        string              `bson:"org_id"`
	Tags         []string            `bson:"tags"`
	AccessRights map[string]bson.Raw `bson:"access_rights"`
	IsInactive   bool                `bson:"is_inactive"`
}

// LoadAPIs reads API definitions from the Dashboard's tyk_apis collection.
// Inactive APIs are skipped because the gateway does not load them.
func LoadAPIs(ctx context.Context, db *mongo.Database, inv *Inventory) error {
	cur, err := db.Collection("tyk_apis").Find(ctx, bson.M{"$or": bson.A{
		bson.M{"api_definition.org_id": inv.OrgID},
		bson.M{"org_id": inv.OrgID},
	}})
	if err != nil {
		return fmt.Errorf("query tyk_apis: %w", err)
	}
	defer cur.Close(ctx)

	for cur.Next(ctx) {
		var d apiDoc
		if err := cur.Decode(&d); err != nil {
			inv.warnf("skipping undecodable API document: %v", err)
			continue
		}
		def := d.def()
		if !def.Active {
			inv.warnf("skipping inactive API %q (%s)", def.Name, def.APIID)
			continue
		}
		inv.APIs = append(inv.APIs, API{
			ID:       def.APIID,
			Name:     def.Name,
			Tags:     def.Tags,
			Versions: analyticsVersions(def.VersionData.NotVersioned, def.VersionData.Versions),
			Keyless:  def.UseKeyless,
			Active:   def.Active,
		})
	}
	return cur.Err()
}

// analyticsVersions returns the version names the gateway can record for an
// API: requests that do not select a version are recorded as NonVersioned,
// otherwise the selected version's name.
func analyticsVersions(notVersioned bool, versions map[string]bson.Raw) []string {
	out := []string{NonVersioned}
	if notVersioned {
		return out
	}
	names := make([]string, 0, len(versions))
	for name := range versions {
		if name != NonVersioned {
			names = append(names, name)
		}
	}
	sort.Strings(names)
	return append(out, names...)
}

// LoadPolicies reads policies from the Dashboard's tyk_policies collection.
// It returns each policy's tags keyed by every ID a session may use for it.
func LoadPolicies(ctx context.Context, db *mongo.Database, inv *Inventory) (map[string][]string, error) {
	cur, err := db.Collection("tyk_policies").Find(ctx, bson.M{"org_id": inv.OrgID})
	if err != nil {
		return nil, fmt.Errorf("query tyk_policies: %w", err)
	}
	defer cur.Close(ctx)

	tags := map[string][]string{}
	for cur.Next(ctx) {
		var d policyDoc
		if err := cur.Decode(&d); err != nil {
			inv.warnf("skipping undecodable policy document: %v", err)
			continue
		}
		p := Policy{ID: d.MID.Hex(), Name: d.Name}
		if d.ID != "" && d.ID != p.ID {
			p.CustomID = d.ID
			tags[d.ID] = d.Tags
		}
		tags[p.ID] = d.Tags
		for apiID := range d.AccessRights {
			p.APIs = append(p.APIs, apiID)
		}
		sort.Strings(p.APIs)
		if d.IsInactive {
			inv.warnf("policy %q (%s) is inactive", d.Name, p.ID)
		}
		inv.Policies = append(inv.Policies, p)
	}
	return tags, cur.Err()
}
