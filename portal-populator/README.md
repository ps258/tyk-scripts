# portal-populator

Builds a Tyk Enterprise Developer Portal test environment for the APIs
already in a Tyk Dashboard. You create the APIs; this tool creates
products, plans, a catalogue, organisations, developers, apps and approved
access requests at a chosen scale.

```sh
go build -o portal-populator .
```

It has no dependencies outside the Go standard library. It uses the
Dashboard API to list the APIs, and the portal admin API (`/portal-api`)
for everything else.

## Usage

The result is real portal credentials, tagged `portal-org-N` / `portal-app-N`, which other
tools can use, for example `aggregate-seeder` to generate analytics.

```sh
export DASHBOARD_SECRET='<dashboard user API key>'
export PORTAL_TOKEN='<portal admin API token>'

# Preview: reads the Dashboard's APIs only.
./portal-populator plan --dashboard-url http://dash:3000 --tier medium

# Create everything. Safe to re-run: existing objects are found by name and reused.
./portal-populator provision --dashboard-url http://dash:3000 \
  --portal-url http://portal:3001 --tier medium --developer-password 'S3cret-pass!'

# Rewrite the developers CSV at any time (provision writes it at the end).
./portal-populator export --portal-url http://portal:3001 --developer-password 'S3cret-pass!'

# Remove everything created under the prefix (counts only without --yes).
./portal-populator cleanup --portal-url http://portal:3001 --yes
```

What `provision` creates, in order:

1. **Products.** Each one bundles `--apis-per-product` of the eligible APIs
   (active, auth-token only), taken in consecutive windows so every API is
   used. The portal creates an access-only policy in the Dashboard for each
   product.
2. **Plans.** Rate limit and quota tiers with auto-approve on. The portal
   creates a rate-limit/quota policy in the Dashboard for each plan.
3. **One public catalogue** holding every product and plan.
4. **Organisations.** Developers are spread evenly across them, with the
   first developer in each org as `consumer-admin` and the rest as
   `consumer-team-member`.
5. **Developers.** Half own one app and half (`--heavy-developers`,
   default half of `--developers`) own `--heavy-apps` apps each, unless
   `--single-app` is given. Each kind is spread evenly across the
   organisations. The email says which kind a developer is (see
   [Names](#names)).
6. **Apps**, created for their developer through the admin API. The
   default visibility is `personal`, so each developer's analytics only
   cover their own apps.
7. **Access requests**, provisioned immediately through
   `PUT /apps/{id}/provision` with one product plus one plan each,
   `--credentials-per-app` per app on average. Each one creates a Dashboard
   key with the product and plan policies applied and the portal tags set.

| Tier | Plans | Products | Orgs | Developers (heavy × apps) | Apps | Access requests |
|---|---|---|---|---|---|---|
| small | 5 | 20 | 5 | 50 (25 × 25) | 650 | ~975 |
| medium | 10 | 50 | 20 | 500 (250 × 50) | 12,750 | ~19,000 |
| large | 20 | 100 | 50 | 2,000 (1,000 × 50) | 51,000 | ~64,000 |
| xlarge | 20 | 100 | 50 | 2,500 (1,250 × 50) | 63,750 | ~89,000 |

### One app per developer (`--single-app`)

`--single-app` gives every developer exactly one app that only they can
see. It turns off heavy developers and puts every developer in the
portal's **Default Organisation** as a `consumer-admin` (`--default-org`
does only the second part). This matters because portals before v1.14
show a developer in any other organisation every app in that
organisation. The portal then sends the Dashboard one tag per app, and
any query with more than one tag is answered from raw logs instead of
aggregates.

Use `--developers` to choose the number of apps. For example,
`--tier large --single-app --developers 4000` makes 4,000 apps and
~5,000 credentials.

Developers are reused by email, so `provision` refuses to run if
existing developers with the prefix are in a different organisation
from the one this run would use. Run `cleanup` first, or use another
`--prefix`.

Any tier value can be overridden with flags (`--developers`,
`--products`, …).

## Names

All names start with `--prefix` (default `stress`), and `cleanup` only
touches objects whose names match. Developers are named by how many apps
they have, and each kind is numbered from 0001:

| | Developer (login) | Display name | Apps |
|---|---|---|---|
| One app | `stress-single-0001@stress.test` | Single 0001 | `stress-single-0001-app` |
| Many apps | `stress-multi-0001@stress.test` | Multi 0001 | `stress-multi-0001-app-01` … `-app-50` |

Single and multi developers alternate through the list, and each kind
is dealt round-robin across the organisations, so every organisation has
both. Other objects are named `stress-product-001`, `stress-plan-01`,
`stress-org-01` and `stress-catalogue`. `cleanup` also removes developers
and apps with the older names (`stress-dev-0001@stress.test`,
`stress-app-00001`). A re-run of `provision` does not recognise those, so
clean up an environment made with them before provisioning it again.

## Developers CSV

At the end, `provision` writes `<prefix>-developers.csv` (choose the file
with `--csv`, or skip it with `--csv -`). `export` writes the same file
from what is in the portal, so you can regenerate it at any time. There
is one row per app, singles first and then multis, each in number order:

| Column | |
|---|---|
| `email`, `kind`, `number`, `app_count` | the developer, `single` or `multi`, its number and how many apps it owns |
| `password` | `--developer-password`, since the portal does not return it |
| `role`, `organisation`, `org_tag` | portal role, organisation name and its `portal-org-N` tag |
| `app_name`, `app_id`, `app_tag` | the app and its `portal-app-N` tag, which the developer dashboard filters analytics on |
| `keys`, `key_hashes` | the app's Dashboard keys and their hashes, space-separated |

To find a developer: `grep stress-multi-0003 stress-developers.csv`.
Search the aggregate docs with the `app_tag` (`tags.portal-app-N`). To
search the `apikeys` section, use `keys` when the Dashboard has
`hash_keys: false`, and `key_hashes` otherwise.

Notes:
- **Developer passwords are unverified.** The admin API's user create
  attributes don't list `Password`, although a setter for it exists. After
  the first run, log in as one persona. If that fails, set passwords for
  the personas in the portal admin UI.
- If the portal has SMTP configured, creating users may send emails.
- **SQLite-backed portals** allow only one write at a time. "database is
  locked" responses are retried automatically, but use `--concurrency 1`
  or `2` to avoid them. The default is 4, which suits PostgreSQL or MySQL.

## Flags

Run `portal-populator <plan|provision|cleanup> -h`. Secrets can come from
the `DASHBOARD_SECRET`, `PORTAL_TOKEN` and `PORTAL_DEV_PASSWORD`
environment variables. `--portal-url` takes the portal base URL;
`/portal-api` is added automatically.
