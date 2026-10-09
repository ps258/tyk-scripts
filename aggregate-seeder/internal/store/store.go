// Package store writes aggregate documents to MongoDB.
package store

import (
	"context"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"go.mongodb.org/mongo-driver/x/mongo/driver/connstring"

	"github.com/TykTechnologies/aggregate-seeder/internal/agg"
)

// Connect opens a client and returns the database named in the URI, or name
// when given.
func Connect(ctx context.Context, uri, name string) (*mongo.Client, *mongo.Database, error) {
	cs, err := parseDBName(uri)
	if err != nil {
		return nil, nil, err
	}
	if name == "" {
		name = cs
	}
	if name == "" {
		return nil, nil, fmt.Errorf("no database in the mongo URI; pass --mongo-db")
	}
	client, err := mongo.Connect(ctx, options.Client().ApplyURI(uri))
	if err != nil {
		return nil, nil, err
	}
	if err := client.Ping(ctx, nil); err != nil {
		return nil, nil, fmt.Errorf("ping mongo: %w", err)
	}
	return client, client.Database(name), nil
}

// EnsureIndexes creates the indexes the Mongo aggregate pump creates
// (tyk-pump/pumps/mongo_aggregate.go ensureIndexes), plus one on _seed.
func EnsureIndexes(ctx context.Context, coll *mongo.Collection) error {
	_, err := coll.Indexes().CreateMany(ctx, []mongo.IndexModel{
		{Keys: bson.D{{Key: "expireAt", Value: 1}}, Options: options.Index().SetExpireAfterSeconds(0)},
		{Keys: bson.D{{Key: "timestamp", Value: 1}}},
		{Keys: bson.D{{Key: "orgid", Value: 1}}},
		{Keys: bson.D{{Key: "_seed", Value: 1}}, Options: options.Index().SetSparse(true)},
	})
	return err
}

// CountForeign counts documents for orgID in [from, to) that were not written
// by this tool, i.e. real pump data that an upsert would overwrite.
func CountForeign(ctx context.Context, coll *mongo.Collection, orgID string, from, to time.Time) (int64, error) {
	return coll.CountDocuments(ctx, bson.M{
		"orgid":     orgID,
		"timestamp": bson.M{"$gte": from, "$lt": to},
		"_seed":     bson.M{"$exists": false},
	})
}

// Writer upserts documents in unordered bulk batches, keyed on orgid and
// timestamp so re-running a range replaces it.
type Writer struct {
	coll    *mongo.Collection
	size    int
	pending []mongo.WriteModel
	Written int64
}

func NewWriter(coll *mongo.Collection, batchSize int) *Writer {
	return &Writer{coll: coll, size: batchSize}
}

func (w *Writer) Add(ctx context.Context, doc *agg.Doc) error {
	w.pending = append(w.pending, mongo.NewReplaceOneModel().
		SetFilter(bson.M{"orgid": doc.OrgID, "timestamp": doc.TimeStamp}).
		SetReplacement(doc).
		SetUpsert(true))
	if len(w.pending) >= w.size {
		return w.Flush(ctx)
	}
	return nil
}

func (w *Writer) Flush(ctx context.Context) error {
	if len(w.pending) == 0 {
		return nil
	}
	_, err := w.coll.BulkWrite(ctx, w.pending, options.BulkWrite().SetOrdered(false))
	if err != nil {
		return fmt.Errorf("bulk write: %w", err)
	}
	w.Written += int64(len(w.pending))
	w.pending = w.pending[:0]
	return nil
}

// Cleanup removes documents written by run, or by any run when run is empty.
// With dryRun it only counts them.
func Cleanup(ctx context.Context, coll *mongo.Collection, run string, dryRun bool) (int64, error) {
	filter := bson.M{"_seed": bson.M{"$exists": true}}
	if run != "" {
		filter = bson.M{"_seed": run}
	}
	if dryRun {
		return coll.CountDocuments(ctx, filter)
	}
	res, err := coll.DeleteMany(ctx, filter)
	if err != nil {
		return 0, err
	}
	return res.DeletedCount, nil
}

func parseDBName(uri string) (string, error) {
	cs, err := connstring.ParseAndValidate(uri)
	if err != nil {
		return "", fmt.Errorf("parse mongo URI: %w", err)
	}
	return cs.Database, nil
}
