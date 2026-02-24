# Import Scripts

This document describes the Goodbooks import scripts in [`scripts/`](/Users/val/ml/projects/books-rec/semantic-shelf/scripts).

## Prerequisites

1. Start DB:
```bash
make db
```
2. Apply migrations:
```bash
make migrate
```
3. Ensure dataset repo exists (expected path example):
`../goodbooks-10k-extended`

## First-Boot Auto Import (docker-entrypoint-initdb.d + COPY)

`docker-compose.yml` mounts:
- `./docker/postgres/init` -> `/docker-entrypoint-initdb.d`
- `${GOODBOOKS_DATASET_DIR}/books_enriched.csv` -> `/docker-entrypoint-seed/books_enriched.csv`

On first initialization of the `postgres_data` volume, Postgres runs:
1. [`docker/postgres/init/01_schema.sql`](/Users/val/ml/projects/books-rec/semantic-shelf/docker/postgres/init/01_schema.sql)
2. [`docker/postgres/init/02_seed_books.sql`](/Users/val/ml/projects/books-rec/semantic-shelf/docker/postgres/init/02_seed_books.sql)

This creates the schema and preloads `books` via SQL `COPY`.

Important notes:
- This runs only when the DB volume is empty.
- For an already initialized volume, these scripts are skipped by design.
- To re-run first-boot seed scripts, run:
```bash
make reset-db
```
then start again with `make run` or `make dev`.

## Scripts Overview

1. [`import_goodbooks_books.py`](/Users/val/ml/projects/books-rec/semantic-shelf/scripts/import_goodbooks_books.py)
- Imports book catalog into `books`.
- Source:
  - full: `books_enriched.csv`
  - sample mode: `samples/books.csv`

2. [`import_goodbooks_interactions.py`](/Users/val/ml/projects/books-rec/semantic-shelf/scripts/import_goodbooks_interactions.py)
- Imports interaction tables:
  - `dataset_users`
  - `ratings`
  - `tags`
  - `book_tags`
  - `to_read`
- Source:
  - full: `ratings.csv`, `tags.csv`, `book_tags.csv`, `to_read.csv`
- sample mode: corresponding files under `samples/`

## Schema and Entity Reasoning

This project uses the existing `public` schema and extends the current app entities rather than introducing a separate `goodbooks` schema.  
Reason: keep API/repository wiring simple and avoid duplicate book sources.

### Core Entities

1. `books`
- Canonical catalog entity for API reads (`/books` endpoints already use it).
- Primary key: `id` (`str`), populated from Goodbooks `book_id`.
- `goodreads_book_id` is unique for tag-link joins.
- JSON `authors`/`genres` are preserved for current API contract and filtering behavior.
- Additional Goodbooks metadata columns are nullable to preserve backward compatibility and allow incremental enrichment.

2. `dataset_users`
- Canonical registry of dataset user IDs (`BIGINT`).
- Purpose: normalize interaction ownership and enforce referential integrity.
- Built from distinct user IDs observed in `ratings` and `to_read`.

3. `ratings`
- Relationship between dataset user and book with explicit signal strength (`rating` 1..5).
- Composite PK: `(user_id, book_id)` prevents duplicates per user-book pair.
- `user_id` -> `dataset_users.user_id`, `book_id` -> `books.id`.

4. `to_read`
- User intent list (future-read signal), separate from explicit ratings.
- Composite PK: `(user_id, book_id)`.
- Same FK pattern as `ratings`.

5. `tags`
- Tag dictionary (`tag_id`, `tag_name`) used by `book_tags`.
- Separate table avoids repeating tag text across large relation table.

6. `book_tags`
- Bridge between Goodreads-level book identity and tag IDs.
- Composite PK: `(goodreads_book_id, tag_id)`.
- `goodreads_book_id` -> `books.goodreads_book_id`, `tag_id` -> `tags.tag_id`.
- Stores `count` as tag strength/popularity signal.

### Why These Keys and FKs

1. `books.id` uses Goodbooks `book_id` because ratings/to-read files reference `book_id`.
2. `book_tags` uses `goodreads_book_id` because source file keys are Goodreads IDs, not `book_id`.
3. Composite keys on relation tables prevent duplicate edges and simplify idempotent upserts.
4. FK constraints ensure import failures happen early when data is inconsistent.

### Why Upsert-Based Imports

1. Idempotency: rerunning scripts should not create duplicate rows.
2. Incremental refresh: updated metadata/scores can overwrite stale values.
3. Operational safety: imports can be retried after partial failures.

### Import Order Rationale

1. Books first: required parent entity for ratings and to-read.
2. Dataset users before user-linked tables: satisfies FK constraints.
3. Tags before book_tags: ensures tag references exist.
4. Book tags last: depends on both books (`goodreads_book_id`) and tags.

## Books Import

Run full import:
```bash
uv run python scripts/import_goodbooks_books.py \
  --data-dir ../goodbooks-10k-extended \
  --truncate-books
```

Run sample import:
```bash
uv run python scripts/import_goodbooks_books.py \
  --data-dir ../goodbooks-10k-extended \
  --use-samples \
  --truncate-books
```

### Flags

- `--data-dir` (required): path to dataset repo.
- `--use-samples`: read from `samples/books.csv`.
- `--truncate-books`: truncates `books` before loading.
- `--batch-size` (default `1000`): upsert chunk size.

### Output

Script prints:
- `total`: rows read
- `processed`: rows mapped successfully
- `inserted`: new rows by PK (`books.id`)
- `updated`: existing rows upserted
- `skipped`: rows not processed (currently derived counter)
- `errors`: parse failures

## Interactions Import

Run full import:
```bash
uv run python scripts/import_goodbooks_interactions.py \
  --data-dir ../goodbooks-10k-extended \
  --truncate-tables
```

Run sample import:
```bash
uv run python scripts/import_goodbooks_interactions.py \
  --data-dir ../goodbooks-10k-extended \
  --use-samples \
  --truncate-tables
```

### Flags

- `--data-dir` (required): path to dataset repo.
- `--use-samples`: read CSVs from `samples/`.
- `--truncate-tables`: truncates `ratings`, `book_tags`, `tags`, `to_read`, `dataset_users`.
- `--batch-size` (default `5000`): bulk upsert size.

### Load Order

The importer uses FK-safe order:
1. `dataset_users` (derived from distinct user IDs in `ratings` + `to_read`)
2. `tags`
3. `ratings`
4. `to_read`
5. `book_tags`

### Output

Per-table line:
- `total`: source rows read
- `inserted`: rows newly inserted by conflict key
- `updated`: rows touched by upsert update path (`0` for `to_read` and `dataset_users` because they use `DO NOTHING`)
- `errors`: parse failures

## Quick Validation SQL

Run:
```bash
docker compose exec -T db psql -U myuser -d books_rec \
  -c "select count(*) from books;" \
  -c "select count(*) from dataset_users;" \
  -c "select count(*) from ratings;" \
  -c "select count(*) from tags;" \
  -c "select count(*) from book_tags;" \
  -c "select count(*) from to_read;"
```

## Common Issues

1. `Operation not permitted` / Docker access denied:
- Re-run with proper local Docker permissions.

2. Duplicate-key upsert conflicts in `book_tags`:
- Current importer deduplicates conflict keys per batch before upsert.

3. Very long import time:
- Full interactions import is large (`ratings.csv` is multi-million rows).
- Increase `--batch-size` cautiously based on local CPU/RAM/DB behavior.
