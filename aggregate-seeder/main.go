// aggregate-seeder writes synthetic Tyk Pump aggregate analytics into MongoDB,
// attributed to the live APIs, policies and keys of a deployment.
package main

import (
	"context"
	"crypto/tls"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/redis/go-redis/v9"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"

	"github.com/TykTechnologies/aggregate-seeder/internal/agg"
	"github.com/TykTechnologies/aggregate-seeder/internal/gen"
	"github.com/TykTechnologies/aggregate-seeder/internal/inventory"
	"github.com/TykTechnologies/aggregate-seeder/internal/profile"
	"github.com/TykTechnologies/aggregate-seeder/internal/store"
	"github.com/TykTechnologies/aggregate-seeder/internal/verify"
)

const usage = `aggregate-seeder <command> [flags]

Commands:
  inventory   read APIs and policies (Dashboard Mongo) and keys (Redis) into a JSON file
  generate    write synthetic aggregate documents into a collection
  verify      check the consistency of documents in a collection
  cleanup     delete documents written by this tool

Run "aggregate-seeder <command> -h" for flags. Secrets can be passed via the
MONGO_URL, ANALYTICS_MONGO_URL and REDIS_PASSWORD environment variables.
`

func main() {
	log.SetFlags(log.Ltime)
	if len(os.Args) < 2 {
		fmt.Fprint(os.Stderr, usage)
		os.Exit(2)
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	var err error
	switch os.Args[1] {
	case "inventory":
		err = runInventory(ctx, os.Args[2:])
	case "generate":
		err = runGenerate(ctx, os.Args[2:])
	case "verify":
		err = runVerify(ctx, os.Args[2:])
	case "cleanup":
		err = runCleanup(ctx, os.Args[2:])
	case "-h", "--help", "help":
		fmt.Print(usage)
	default:
		fmt.Fprint(os.Stderr, usage)
		os.Exit(2)
	}
	if err != nil {
		log.Fatalf("error: %v", err)
	}
}

// --- shared flags ---

type sourceFlags struct {
	mongoURL, mongoDB, org     string
	redisAddrs, redisUser      string
	redisPass                  string
	redisDB                    int
	redisTLS, redisTLSInsecure bool
	includeExpired             bool
}

func (s *sourceFlags) register(fs *flag.FlagSet) {
	fs.StringVar(&s.mongoURL, "mongo-url", os.Getenv("MONGO_URL"), "Dashboard MongoDB URI (env MONGO_URL)")
	fs.StringVar(&s.mongoDB, "mongo-db", "", "Dashboard database name (default: from the URI)")
	fs.StringVar(&s.org, "org", "", "org ID (required)")
	fs.StringVar(&s.redisAddrs, "redis-addrs", "localhost:6379", "comma separated Redis addresses; more than one means cluster")
	fs.StringVar(&s.redisUser, "redis-username", "", "Redis username")
	fs.StringVar(&s.redisPass, "redis-password", os.Getenv("REDIS_PASSWORD"), "Redis password (env REDIS_PASSWORD)")
	fs.IntVar(&s.redisDB, "redis-db", 0, "Redis database (non-cluster only)")
	fs.BoolVar(&s.redisTLS, "redis-tls", false, "use TLS for Redis")
	fs.BoolVar(&s.redisTLSInsecure, "redis-tls-insecure", false, "skip Redis TLS verification")
	fs.BoolVar(&s.includeExpired, "include-expired", false, "include expired keys")
}

func (s *sourceFlags) build(ctx context.Context) (*inventory.Inventory, error) {
	if s.org == "" {
		return nil, fmt.Errorf("--org is required")
	}
	client, db, err := store.Connect(ctx, s.mongoURL, s.mongoDB)
	if err != nil {
		return nil, fmt.Errorf("dashboard mongo: %w", err)
	}
	defer client.Disconnect(context.Background())

	opts := &redis.UniversalOptions{
		Addrs:    strings.Split(s.redisAddrs, ","),
		Username: s.redisUser,
		Password: s.redisPass,
		DB:       s.redisDB,
	}
	if s.redisTLS {
		opts.TLSConfig = &tls.Config{InsecureSkipVerify: s.redisTLSInsecure}
	}
	rdb := redis.NewUniversalClient(opts)
	defer rdb.Close()
	if err := rdb.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("ping redis: %w", err)
	}

	inv, err := inventory.Build(ctx, db, rdb, s.org, s.includeExpired)
	if err != nil {
		return nil, err
	}
	return inv, nil
}

func printInventory(inv *inventory.Inventory) {
	log.Print(inv.Summary())
	for _, w := range inv.Warnings {
		log.Printf("  warning: %s", w)
	}
}

type targetFlags struct {
	url, db, collection string
}

func (t *targetFlags) register(fs *flag.FlagSet) {
	def := os.Getenv("ANALYTICS_MONGO_URL")
	fs.StringVar(&t.url, "analytics-mongo-url", def, "MongoDB URI holding the aggregate collection (env ANALYTICS_MONGO_URL; default: --mongo-url)")
	fs.StringVar(&t.db, "analytics-mongo-db", "", "analytics database name (default: from the URI)")
	fs.StringVar(&t.collection, "collection", "", "aggregate collection, e.g. z_tyk_analyticz_aggregate_<org> or tyk_analytics_aggregates (required)")
}

func (t *targetFlags) open(ctx context.Context, fallbackURL string) (*mongo.Client, *mongo.Collection, error) {
	if t.collection == "" {
		return nil, nil, fmt.Errorf("--collection is required")
	}
	url := t.url
	if url == "" {
		url = fallbackURL
	}
	if url == "" {
		return nil, nil, fmt.Errorf("--analytics-mongo-url or --mongo-url is required")
	}
	client, db, err := store.Connect(ctx, url, t.db)
	if err != nil {
		return nil, nil, fmt.Errorf("analytics mongo: %w", err)
	}
	return client, db.Collection(t.collection), nil
}

// --- inventory ---

func runInventory(ctx context.Context, args []string) error {
	fs := flag.NewFlagSet("inventory", flag.ExitOnError)
	var src sourceFlags
	src.register(fs)
	out := fs.String("out", "inventory.json", "output file")
	fs.Parse(args)

	inv, err := src.build(ctx)
	if err != nil {
		return err
	}
	printInventory(inv)
	if err := inv.Save(*out); err != nil {
		return err
	}
	log.Printf("wrote %s", *out)
	return nil
}

// --- generate ---

func runGenerate(ctx context.Context, args []string) error {
	fs := flag.NewFlagSet("generate", flag.ExitOnError)
	var src sourceFlags
	var tgt targetFlags
	src.register(fs)
	tgt.register(fs)
	invPath := fs.String("inventory", "", "inventory file from the inventory command (default: read live from Mongo and Redis)")
	profPath := fs.String("profile", "", "traffic profile YAML (default: built-in profile)")
	fromS := fs.String("from", "", "start, YYYY-MM-DD or RFC3339 (default: --to minus 365 days)")
	toS := fs.String("to", "", "end (exclusive), YYYY-MM-DD or RFC3339 (default: start of the current hour)")
	granularity := fs.String("granularity", "hour", `bucket size: "hour" or minutes such as "1m", "5m", "15m"`)
	seed := fs.Uint64("seed", 1, "random seed; the same seed, inventory and profile give the same documents")
	runID := fs.String("run-id", "", "value written to _seed for cleanup (default: seed-<timestamp>)")
	expireS := fs.String("expire-at", "", "expireAt for every document (default: 10 years from now; the TTL index deletes documents once it passes)")
	dryRun := fs.Bool("dry-run", false, "generate a sample without writing; prints estimates and writes --sample-out")
	sampleOut := fs.String("sample-out", "sample-doc.json", "where --dry-run writes the busiest sample document")
	overwrite := fs.Bool("overwrite", false, "allow replacing documents in the range that were not written by this tool")
	workers := fs.Int("workers", 4, "document builders")
	batch := fs.Int("batch", 50, "documents per bulk write")
	noIndexes := fs.Bool("no-indexes", false, "do not create indexes on the collection")
	fs.Parse(args)

	bucketMinutes, err := parseGranularity(*granularity)
	if err != nil {
		return err
	}
	to := time.Now().UTC().Truncate(time.Hour)
	if *toS != "" {
		if to, err = parseTime(*toS); err != nil {
			return fmt.Errorf("--to: %w", err)
		}
	}
	from := to.AddDate(0, 0, -365)
	if *fromS != "" {
		if from, err = parseTime(*fromS); err != nil {
			return fmt.Errorf("--from: %w", err)
		}
	}
	expireAt := time.Now().UTC().AddDate(10, 0, 0).Truncate(time.Second)
	if *expireS != "" {
		if expireAt, err = parseTime(*expireS); err != nil {
			return fmt.Errorf("--expire-at: %w", err)
		}
	}
	if *runID == "" {
		*runID = "seed-" + time.Now().UTC().Format("20060102T150405Z")
	}

	prof, err := profile.Load(*profPath)
	if err != nil {
		return err
	}
	var inv *inventory.Inventory
	if *invPath != "" {
		if inv, err = inventory.Load(*invPath); err != nil {
			return err
		}
		if src.org != "" && src.org != inv.OrgID {
			return fmt.Errorf("--org %s does not match inventory org %s", src.org, inv.OrgID)
		}
	} else if inv, err = src.build(ctx); err != nil {
		return err
	}
	printInventory(inv)

	g, err := gen.New(inv, prof, gen.Options{
		OrgID:         inv.OrgID,
		From:          from,
		To:            to,
		BucketMinutes: bucketMinutes,
		Seed:          *seed,
		ExpireAt:      expireAt,
		RunID:         *runID,
	})
	if err != nil {
		return err
	}
	buckets := g.Buckets()
	log.Printf("range %s → %s, %d-minute buckets: %d buckets, run id %s",
		from.Format(time.RFC3339), to.Format(time.RFC3339), bucketMinutes, len(buckets), *runID)

	if *dryRun {
		return dryRunReport(g, buckets, *sampleOut)
	}

	client, coll, err := tgt.open(ctx, src.mongoURL)
	if err != nil {
		return err
	}
	defer client.Disconnect(context.Background())

	n, err := store.CountForeign(ctx, coll, inv.OrgID, buckets[0], to)
	if err != nil {
		return err
	}
	if n > 0 && !*overwrite {
		return fmt.Errorf("%s already has %d documents for org %s in this range that this tool did not write; pass --overwrite to replace them", coll.Name(), n, inv.OrgID)
	}
	if !*noIndexes {
		if err := store.EnsureIndexes(ctx, coll); err != nil {
			return fmt.Errorf("create indexes: %w", err)
		}
	}
	return write(ctx, g, buckets, store.NewWriter(coll, *batch), *workers)
}

func write(ctx context.Context, g *gen.Generator, buckets []time.Time, w *store.Writer, workers int) error {
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	jobs := make(chan time.Time)
	docs := make(chan *agg.Doc, workers*2)
	go func() {
		defer close(jobs)
		for _, b := range buckets {
			select {
			case jobs <- b:
			case <-ctx.Done():
				return
			}
		}
	}()
	var wg sync.WaitGroup
	for range max(1, workers) {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for b := range jobs {
				if d := g.Bucket(b); d != nil {
					select {
					case docs <- d:
					case <-ctx.Done():
						return
					}
				}
			}
		}()
	}
	go func() { wg.Wait(); close(docs) }()

	start := time.Now()
	tick := time.NewTicker(10 * time.Second)
	defer tick.Stop()
	var hits int64
	for {
		select {
		case d, ok := <-docs:
			if !ok {
				if err := w.Flush(ctx); err != nil {
					return err
				}
				log.Printf("done: %d documents, %d simulated requests in %s", w.Written, hits, time.Since(start).Round(time.Second))
				return nil
			}
			hits += int64(d.Total.Hits)
			if err := w.Add(ctx, d); err != nil {
				return err
			}
		case <-tick.C:
			log.Printf("%d documents written, %d simulated requests", w.Written, hits)
		case <-ctx.Done():
			return ctx.Err()
		}
	}
}

func dryRunReport(g *gen.Generator, buckets []time.Time, sampleOut string) error {
	// Sample a week spread across the range (or every bucket if fewer).
	const samples = 168
	step := max(1, len(buckets)/samples)
	var (
		n, nonEmpty    int
		bytes, hits    int64
		busiest        *agg.Doc
		busiestSize    int
		maxTags, maxKs int
	)
	for i := 0; i < len(buckets); i += step {
		n++
		d := g.Bucket(buckets[i])
		if d == nil {
			continue
		}
		raw, err := bson.Marshal(d)
		if err != nil {
			return err
		}
		nonEmpty++
		bytes += int64(len(raw))
		hits += int64(d.Total.Hits)
		maxTags = max(maxTags, len(d.Tags))
		maxKs = max(maxKs, len(d.APIKeys))
		if busiest == nil || d.Total.Hits > busiest.Total.Hits {
			busiest, busiestSize = d, len(raw)
		}
	}
	if nonEmpty == 0 {
		return fmt.Errorf("no sampled bucket had traffic; raise daily_requests")
	}
	docs := int64(len(buckets)) * int64(nonEmpty) / int64(n)
	avg := bytes / int64(nonEmpty)
	log.Printf("sampled %d buckets: avg doc %s, busiest doc %s (%d hits), up to %d tags and %d keys per doc",
		n, human(avg), human(int64(busiestSize)), busiest.Total.Hits, maxTags, maxKs)
	log.Printf("estimate: %d documents, %s total, ~%d simulated requests",
		docs, human(docs*avg), int64(len(buckets))*hits/int64(n))
	if busiestSize > 16<<20 {
		log.Printf("warning: busiest document exceeds MongoDB's 16MB limit")
	}
	out, err := bson.MarshalExtJSONIndent(busiest, false, false, "", "  ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(sampleOut, out, 0o644); err != nil {
		return err
	}
	log.Printf("wrote busiest sample document to %s", sampleOut)
	return nil
}

// --- verify ---

func runVerify(ctx context.Context, args []string) error {
	fs := flag.NewFlagSet("verify", flag.ExitOnError)
	var tgt targetFlags
	tgt.register(fs)
	mongoURL := fs.String("mongo-url", os.Getenv("MONGO_URL"), "fallback MongoDB URI (env MONGO_URL)")
	run := fs.String("run", "", "only check documents from this run id")
	org := fs.String("org", "", "only check documents for this org")
	fromS := fs.String("from", "", "only check documents at or after this time")
	toS := fs.String("to", "", "only check documents before this time")
	fs.Parse(args)

	filter := bson.M{}
	if *run != "" {
		filter["_seed"] = *run
	}
	if *org != "" {
		filter["orgid"] = *org
	}
	ts := bson.M{}
	if *fromS != "" {
		t, err := parseTime(*fromS)
		if err != nil {
			return err
		}
		ts["$gte"] = t
	}
	if *toS != "" {
		t, err := parseTime(*toS)
		if err != nil {
			return err
		}
		ts["$lt"] = t
	}
	if len(ts) > 0 {
		filter["timestamp"] = ts
	}

	client, coll, err := tgt.open(ctx, *mongoURL)
	if err != nil {
		return err
	}
	defer client.Disconnect(context.Background())

	cur, err := coll.Find(ctx, filter)
	if err != nil {
		return err
	}
	defer cur.Close(ctx)
	rep := verify.NewReport()
	for cur.Next(ctx) {
		var d agg.Doc
		if err := cur.Decode(&d); err != nil {
			return fmt.Errorf("decode: %w", err)
		}
		rep.Add(&d)
	}
	if err := cur.Err(); err != nil {
		return err
	}
	fmt.Print(rep.String())
	if rep.Failed > 0 {
		return fmt.Errorf("%d documents failed checks", rep.Failed)
	}
	return nil
}

// --- cleanup ---

func runCleanup(ctx context.Context, args []string) error {
	fs := flag.NewFlagSet("cleanup", flag.ExitOnError)
	var tgt targetFlags
	tgt.register(fs)
	mongoURL := fs.String("mongo-url", os.Getenv("MONGO_URL"), "fallback MongoDB URI (env MONGO_URL)")
	run := fs.String("run", "", "run id to delete")
	all := fs.Bool("all", false, "delete documents from every run")
	yes := fs.Bool("yes", false, "actually delete (otherwise only count)")
	fs.Parse(args)

	if (*run == "") == !*all {
		return fmt.Errorf("pass exactly one of --run or --all")
	}
	client, coll, err := tgt.open(ctx, *mongoURL)
	if err != nil {
		return err
	}
	defer client.Disconnect(context.Background())

	n, err := store.Cleanup(ctx, coll, *run, !*yes)
	if err != nil {
		return err
	}
	if !*yes {
		log.Printf("%d documents would be deleted from %s; re-run with --yes to delete", n, coll.Name())
		return nil
	}
	log.Printf("deleted %d documents from %s", n, coll.Name())
	return nil
}

// --- helpers ---

func parseGranularity(s string) (int, error) {
	if s == "hour" || s == "1h" || s == "60m" {
		return 60, nil
	}
	n, err := strconv.Atoi(strings.TrimSuffix(s, "m"))
	if err != nil || n < 1 || n > 60 || 60%n != 0 {
		return 0, fmt.Errorf(`--granularity must be "hour" or a number of minutes that divides 60, e.g. "1m", "5m"`)
	}
	return n, nil
}

func parseTime(s string) (time.Time, error) {
	if t, err := time.Parse(time.RFC3339, s); err == nil {
		return t.UTC(), nil
	}
	return time.Parse("2006-01-02", s)
}

func human(b int64) string {
	switch {
	case b >= 1<<30:
		return fmt.Sprintf("%.1fGB", float64(b)/(1<<30))
	case b >= 1<<20:
		return fmt.Sprintf("%.1fMB", float64(b)/(1<<20))
	case b >= 1<<10:
		return fmt.Sprintf("%.1fKB", float64(b)/(1<<10))
	}
	return fmt.Sprintf("%dB", b)
}
