package inventory

import (
	"context"
	"time"

	"github.com/redis/go-redis/v9"
	"go.mongodb.org/mongo-driver/mongo"
)

// Build reads the live inventory for orgID from the Dashboard database and Redis.
func Build(ctx context.Context, db *mongo.Database, rdb redis.UniversalClient, orgID string, includeExpired bool) (*Inventory, error) {
	inv := &Inventory{OrgID: orgID, GeneratedAt: time.Now().UTC()}
	if err := LoadAPIs(ctx, db, inv); err != nil {
		return nil, err
	}
	policyTags, err := LoadPolicies(ctx, db, inv)
	if err != nil {
		return nil, err
	}
	if err := LoadKeys(ctx, rdb, inv, KeyOptions{IncludeExpired: includeExpired, PolicyTags: policyTags}); err != nil {
		return nil, err
	}
	inv.sort()
	inv.Validate()
	return inv, nil
}
