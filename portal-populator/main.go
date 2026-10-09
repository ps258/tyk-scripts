// portal-populator creates Tyk Enterprise Developer Portal objects (products,
// plans, a catalogue, organisations, developers, apps and approved access
// requests) for the APIs in a Tyk Dashboard, to build test environments.
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"regexp"
	"sort"
	"strings"
	"syscall"

	"github.com/TykTechnologies/portal-populator/internal/portal"
)

const usage = `portal-populator <plan|provision|export|cleanup> [flags]

  plan       read the Dashboard's APIs and print what would be created (no portal changes)
  provision  create products, plans, a catalogue, organisations, developers, apps and
             approved access requests in the portal; safe to re-run. Writes the
             developers CSV at the end
  export     write the developers CSV (one row per app: developer, organisation,
             app ID, portal tags and keys) from what is in the portal
  cleanup    delete everything provision created for --prefix

Run "portal-populator <command> -h" for flags. Secrets can be passed via the
DASHBOARD_SECRET, PORTAL_TOKEN and PORTAL_DEV_PASSWORD environment variables.
`

var prefixRe = regexp.MustCompile(`^[a-z][a-z0-9]*$`)

type portalFlags struct {
	portalURL, portalToken string
	insecure               bool
	prefix                 string
	concurrency            int
}

func (p *portalFlags) register(fs *flag.FlagSet) {
	fs.StringVar(&p.portalURL, "portal-url", os.Getenv("PORTAL_URL"), "portal base URL, e.g. http://localhost:3001 (env PORTAL_URL)")
	fs.StringVar(&p.portalToken, "portal-token", os.Getenv("PORTAL_TOKEN"), "portal admin API token (env PORTAL_TOKEN)")
	fs.BoolVar(&p.insecure, "insecure", false, "skip TLS verification for the portal and Dashboard")
	fs.StringVar(&p.prefix, "prefix", "stress", "lowercase alphanumeric prefix for every object name; cleanup uses it to find them")
	fs.IntVar(&p.concurrency, "concurrency", 4, "parallel portal requests; use 1-2 for a portal on SQLite, which allows one writer at a time")
}

func (p *portalFlags) client() (*portal.Client, error) {
	if !prefixRe.MatchString(p.prefix) {
		return nil, fmt.Errorf("--prefix must be lowercase letters and digits, starting with a letter")
	}
	if p.portalURL == "" || p.portalToken == "" {
		return nil, fmt.Errorf("--portal-url and --portal-token are required")
	}
	base := strings.TrimRight(p.portalURL, "/")
	if !strings.HasSuffix(base, "/portal-api") {
		base += "/portal-api"
	}
	return portal.NewClient(base, p.portalToken, p.insecure), nil
}

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
	case "plan":
		err = runProvision(ctx, os.Args[2:], true)
	case "provision":
		err = runProvision(ctx, os.Args[2:], false)
	case "export":
		err = runExport(ctx, os.Args[2:])
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

func runProvision(ctx context.Context, args []string, planOnly bool) error {
	fs := flag.NewFlagSet("provision", flag.ExitOnError)
	var pf portalFlags
	pf.register(fs)
	dashURL := fs.String("dashboard-url", os.Getenv("DASHBOARD_URL"), "Dashboard URL (env DASHBOARD_URL)")
	dashSecret := fs.String("dashboard-secret", os.Getenv("DASHBOARD_SECRET"), "Dashboard user API key (env DASHBOARD_SECRET)")
	apiMatch := fs.String("api-match", "", "only use APIs whose name matches this regular expression")
	tierName := fs.String("tier", "small", "size preset: "+strings.Join(portal.TierNames(), ", "))
	plans := fs.Int("plans", 0, "override the tier's number of plans")
	products := fs.Int("products", 0, "override the tier's number of products")
	apisPer := fs.Int("apis-per-product", 0, "override APIs per product")
	orgs := fs.Int("orgs", 0, "override the number of portal organisations")
	devs := fs.Int("developers", 0, "override the number of developers")
	heavy := fs.Int("heavy-developers", -1, "number of developers with many apps (default: half the developers)")
	heavyApps := fs.Int("heavy-apps", 0, "override apps per heavy developer")
	creds := fs.Float64("credentials-per-app", 0, "override average access requests per app")
	seed := fs.Uint64("seed", 1, "random seed for product/plan assignment")
	providerID := fs.Uint("provider-id", 0, "portal provider for the Dashboard (default: the only provider)")
	password := fs.String("developer-password", os.Getenv("PORTAL_DEV_PASSWORD"), "password for every developer (env PORTAL_DEV_PASSWORD); verify one login after the first run")
	visibility := fs.String("app-visibility", "personal", "app visibility: personal, team or organisation (portal v1.14+)")
	defaultOrg := fs.Bool("default-org", false, "put every developer in the portal's Default Organisation instead of creating organisations")
	singleApp := fs.Bool("single-app", false, "one app per developer, each visible only to its owner: no heavy developers, all in the Default Organisation")
	csvPath := fs.String("csv", "", `developers CSV to write after provisioning (default "<prefix>-developers.csv"; "-" for none)`)
	fs.Parse(args)

	tier, ok := portal.Tiers[*tierName]
	if !ok {
		return fmt.Errorf("unknown --tier %q", *tierName)
	}
	override := func(dst *int, v, unset int) {
		if v != unset {
			*dst = v
		}
	}
	override(&tier.Plans, *plans, 0)
	override(&tier.Products, *products, 0)
	override(&tier.APIsPerProduct, *apisPer, 0)
	override(&tier.Orgs, *orgs, 0)
	override(&tier.Developers, *devs, 0)
	tier.HeavyDevelopers = tier.DefaultHeavy()
	override(&tier.HeavyDevelopers, *heavy, -1)
	override(&tier.HeavyApps, *heavyApps, 0)
	if *creds != 0 {
		tier.CredentialsPerApp = *creds
	}
	if *singleApp {
		if *heavy > 0 {
			return fmt.Errorf("--single-app cannot be combined with --heavy-developers")
		}
		tier.HeavyDevelopers = 0
		*defaultOrg = true
	}
	tier.DefaultOrg = *defaultOrg
	switch *visibility {
	case "personal", "team", "organisation":
	default:
		return fmt.Errorf("--app-visibility must be personal, team or organisation")
	}
	if !prefixRe.MatchString(pf.prefix) {
		return fmt.Errorf("--prefix must be lowercase letters and digits, starting with a letter")
	}

	if *dashURL == "" || *dashSecret == "" {
		return fmt.Errorf("--dashboard-url and --dashboard-secret are required")
	}
	dash := portal.NewClient(*dashURL, *dashSecret, pf.insecure)
	apis, err := portal.ListDashboardAPIs(ctx, dash)
	if err != nil {
		return err
	}
	var re *regexp.Regexp
	if *apiMatch != "" {
		if re, err = regexp.Compile(*apiMatch); err != nil {
			return fmt.Errorf("--api-match: %w", err)
		}
	}
	var eligible []string
	skipped := map[string][]string{}
	for _, a := range apis {
		reason := a.Ineligible()
		if reason == "" && re != nil && !re.MatchString(a.Name) {
			reason = "excluded by --api-match"
		}
		if reason != "" {
			skipped[reason] = append(skipped[reason], a.Name)
			continue
		}
		eligible = append(eligible, a.APIID)
	}
	log.Printf("dashboard: %d APIs, %d eligible (active, auth token only)", len(apis), len(eligible))
	reasons := make([]string, 0, len(skipped))
	for r := range skipped {
		reasons = append(reasons, r)
	}
	sort.Strings(reasons)
	for _, r := range reasons {
		log.Printf("  skipped %d %s: %s", len(skipped[r]), r, abbreviate(skipped[r], 8))
	}

	plan, err := portal.BuildPlan(pf.prefix, tier, eligible, *seed)
	if err != nil {
		return err
	}
	heavyCount := 0
	for _, d := range plan.Devs {
		if d.Heavy {
			heavyCount++
		}
	}
	orgDesc := fmt.Sprintf("%d organisations", len(plan.Orgs))
	if tier.DefaultOrg {
		orgDesc = "Default Organisation"
	}
	devDesc := fmt.Sprintf("%d developers (%d with %d apps)", len(plan.Devs), heavyCount, tier.HeavyApps)
	if heavyCount == 0 {
		devDesc = fmt.Sprintf("%d developers (1 app each)", len(plan.Devs))
	}
	log.Printf("plan (%s): %d products x %d APIs, %d plans, 1 catalogue, %s, %s, %d apps, %d access requests",
		*tierName, len(plan.Products), len(plan.Products[0].APIIDs), len(plan.Plans), orgDesc,
		devDesc, len(plan.Apps), plan.Credentials())
	if covered := coveredAPIs(plan); covered < len(eligible) {
		log.Printf("  note: products cover %d of %d eligible APIs; raise --products or --apis-per-product to cover all", covered, len(eligible))
	}
	if planOnly {
		return nil
	}

	c, err := pf.client()
	if err != nil {
		return err
	}
	pid, err := portal.ResolveProvider(ctx, c, *providerID)
	if err != nil {
		return err
	}
	log.Printf("provisioning into %s (provider %d)", pf.portalURL, pid)
	res, err := portal.Provision(ctx, c, plan, portal.Options{
		ProviderID:  pid,
		Concurrency: pf.concurrency,
		Password:    *password,
		Visibility:  *visibility,
	})
	for _, k := range []string{"products", "plans", "catalogues", "organisations", "developers", "apps", "access requests"} {
		if res != nil && res.Created[k]+res.Existing[k] > 0 {
			log.Printf("  %-16s %6d created, %6d already present", k, res.Created[k], res.Existing[k])
		}
	}
	if n := c.LockRetries(); n > 0 {
		log.Printf("  the portal database was busy %d times (retried); a SQLite-backed portal handles --concurrency 2 or less best", n)
	}
	if err != nil {
		return fmt.Errorf("%w (re-run the same command to resume)", err)
	}
	printPersonas(plan)
	log.Printf("credentials are in Redis and Mongo now; tools that read keys live (e.g. aggregate-seeder inventory) will pick them up")
	if *csvPath == "-" {
		return nil
	}
	return writeCSV(ctx, c, pf, *csvPath, *password)
}

func runExport(ctx context.Context, args []string) error {
	fs := flag.NewFlagSet("export", flag.ExitOnError)
	var pf portalFlags
	pf.register(fs)
	csvPath := fs.String("csv", "", `file to write (default "<prefix>-developers.csv"; "-" for stdout)`)
	password := fs.String("developer-password", os.Getenv("PORTAL_DEV_PASSWORD"), "password to show in the CSV (env PORTAL_DEV_PASSWORD); the portal does not return it")
	fs.Parse(args)

	c, err := pf.client()
	if err != nil {
		return err
	}
	return writeCSV(ctx, c, pf, *csvPath, *password)
}

func writeCSV(ctx context.Context, c *portal.Client, pf portalFlags, path, password string) error {
	if path == "" {
		path = pf.prefix + "-developers.csv"
	}
	w := os.Stdout
	if path != "-" {
		f, err := os.Create(path)
		if err != nil {
			return err
		}
		defer f.Close()
		w = f
	}
	log.Printf("exporting developers and apps")
	n, err := portal.Export(ctx, c, pf.prefix, password, pf.concurrency, w)
	if err != nil {
		return fmt.Errorf("export: %w", err)
	}
	if path != "-" {
		if err := w.Close(); err != nil {
			return err
		}
		log.Printf("wrote %d apps to %s", n, path)
	}
	return nil
}

func runCleanup(ctx context.Context, args []string) error {
	fs := flag.NewFlagSet("cleanup", flag.ExitOnError)
	var pf portalFlags
	pf.register(fs)
	yes := fs.Bool("yes", false, "actually delete (otherwise only count)")
	fs.Parse(args)

	c, err := pf.client()
	if err != nil {
		return err
	}
	counts, err := portal.Cleanup(ctx, c, pf.prefix, pf.concurrency, !*yes)
	verb := "deleted"
	if !*yes {
		verb = "would delete"
	}
	for _, k := range []string{"apps", "developers", "organisations", "catalogues", "plans", "products"} {
		log.Printf("  %s %d %s", verb, counts[k], k)
	}
	if err == nil && !*yes {
		log.Printf("re-run with --yes to delete")
	}
	return err
}

// printPersonas explains the developer names: single-app developers (one tag,
// aggregate queries) and heavy developers ("all apps" sends many tags, which
// the Dashboard serves from raw logs).
func printPersonas(plan *portal.Plan) {
	counts := map[string]int{}
	apps := map[string]int{}
	for _, a := range plan.Apps {
		apps[plan.Devs[a.Dev].Kind()]++
	}
	for _, d := range plan.Devs {
		counts[d.Kind()]++
	}
	log.Printf("developers:")
	for _, k := range []string{portal.KindSingle, portal.KindMulti} {
		if counts[k] == 0 {
			continue
		}
		log.Printf("  %-6s %s-%s-0001 … %s-%s-%04d@%s.test (%d developers, %d apps)",
			k, plan.Prefix, k, plan.Prefix, k, counts[k], plan.Prefix, counts[k], apps[k])
	}
}

func coveredAPIs(plan *portal.Plan) int {
	seen := map[string]bool{}
	for _, p := range plan.Products {
		for _, id := range p.APIIDs {
			seen[id] = true
		}
	}
	return len(seen)
}

func abbreviate(names []string, n int) string {
	if len(names) <= n {
		return strings.Join(names, ", ")
	}
	return strings.Join(names[:n], ", ") + fmt.Sprintf(", … (%d more)", len(names)-n)
}
