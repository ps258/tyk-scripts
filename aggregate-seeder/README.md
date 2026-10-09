# aggregate-seeder

Writes synthetic Tyk Pump **aggregate** analytics (the documents the Mongo
aggregate pump writes) straight into MongoDB, for any time range, without
producing raw analytics records. Traffic is attributed to the deployment's
live APIs, policies and keys, so tags such as `pol-<id>`, `portal-app-<n>`,
`api-<id>` and the API definitions' own tags match real objects and the
Dashboard and Portal can query them.

## How it works

1. **Inventory**. Reads the live deployment:
   - APIs from the Dashboard's `tyk_apis` collection: ID, name, tags and versions. Inactive APIs are skipped.
   - Policies from `tyk_policies`: IDs and tags.
   - Keys from Redis `apikey-*` sessions for the org: alias, `apply_policies`, tags, developer ID, OAuth client ID and `access_rights`.

   Each key's tags are its session tags plus the tags of its policies,
   merged the way the gateway does when it applies policies.
2. **Traffic model** (`profile.example.yaml`). Sets:
   - daily volume and growth across the range
   - day/night and weekday curves
   - Zipf spread across APIs and keys
   - log-normal noise
   - per-API error codes and rates, latency and bytes
   - incident windows

   All randomness is seeded, and each bucket is generated independently,
   so the same inputs always produce the same documents.
3. **Buckets**. For each hour (or N-minute bucket), traffic is simulated as
   *cells*: key × API × version counters. Every section of the document is
   built by summing cells: `apiid`, `versions`, `apikeys`, `oauthids`,
   `tags`, `errors`, `total`, `lists.*` and the averages. The gateway's tag
   rules and the pump's trimming are applied (`.` removed, `key-*` dropped).
   Because everything comes from the same cells, totals, tags and lists
   always agree.
4. **Write**. Each document is replaced whole, in unordered bulk upserts
   keyed on `{orgid, timestamp}`, into the collection you name. The pump's
   indexes are created (`expireAt` TTL, `timestamp`, `orgid`). Each document
   carries `_seed: <run id>` so a run can be removed later.

Minute buckets (`--granularity 1m|5m|…`) work like the pump's
`aggregation_time`: `timestamp` is rounded down to the bucket and `timeid`
stays at hour level.

## Usage

```sh
go build -o aggregate-seeder .

# 1. Read the deployment and review what will be emitted.
export MONGO_URL='mongodb://user:pass@host:27017/tyk_analytics'
export REDIS_PASSWORD='…'
./aggregate-seeder inventory --org <orgid> --redis-addrs host:6379 --out inventory.json

# 2. Preview: doc count/size estimate and the busiest sample doc in sample-doc.json.
./aggregate-seeder generate --inventory inventory.json \
  --collection z_tyk_analyticz_aggregate_<orgid> \
  --from 2025-10-08 --to 2026-10-08 --profile profile.example.yaml --dry-run

# 3. Write.
./aggregate-seeder generate --inventory inventory.json \
  --collection z_tyk_analyticz_aggregate_<orgid> \
  --from 2025-10-08 --to 2026-10-08 --profile profile.example.yaml --run-id year1

# 4. Check, and remove when done.
./aggregate-seeder verify  --collection z_tyk_analyticz_aggregate_<orgid> --run year1
./aggregate-seeder cleanup --collection z_tyk_analyticz_aggregate_<orgid> --run year1 --yes
```

- `generate` without `--inventory` reads the deployment live (it takes the same Redis and Mongo flags as `inventory`).
- If the aggregates live in a different MongoDB from the Dashboard, use `--analytics-mongo-url` / `ANALYTICS_MONGO_URL`.
- Redis Cluster: pass several comma-separated `--redis-addrs`. TLS: `--redis-tls`.

## Portal test environments

To give the generated traffic real portal credentials (tags
`portal-org-N` / `portal-app-N`), populate the portal first with the
separate `portal-populator` tool (`../portal-populator`). Then run
`inventory` so the new keys are picked up from Redis.

## Safety

- `generate` refuses to run when the range already has documents for the
  org that this tool did not write (real pump data). Pass `--overwrite` to
  replace them.
- `expireAt` defaults to 10 years ahead. Setting it relative to the
  historical timestamp would let the TTL index delete the data within a
  minute.
- `cleanup` only counts unless you pass `--yes`, and only touches documents
  with `_seed`.

## Sizing

Document size grows with the number of distinct tags and keys active in a
bucket. All keys are usually active in every bucket at high volumes. With
about 40 APIs, 400 keys and about 250 tags, a document is about 1 MB:

| Range / granularity | Documents | Size |
|---|---|---|
| 1 year hourly | 8,760 | ~8 GB |
| 1 day per-minute | 1,440 | ~1.4 GB |
| 1 year per-minute | 525,600 | ~500 GB (impractical) |

Use `--dry-run` for an estimate. For minute-level data over a long period,
write hourly documents for most of the range and per-minute documents for a
recent window (two runs over adjacent ranges).

## Fidelity notes

- Cells stand in for individual requests. Per-error-code latency totals in
  `errors.<code>` are apportioned by request count. Minimum latency only
  takes cells containing a success, approximating the pump's "don't lower
  min on errors" rule.
- As in the pump, a tag that appears twice on a record (for example a
  session tag that equals an API tag) is counted twice.
- `geo`, `endpoints`, `apiendpoints`, `keyendpoints` and `oauthendpoints`
  are not generated. Their `lists.*` arrays are written empty, matching a
  pump with `track_all_paths` off and no GeoIP.
- Not supported yet: GraphQL aggregates, and Dashboard-API-based inventory
  (Mongo is read directly).
