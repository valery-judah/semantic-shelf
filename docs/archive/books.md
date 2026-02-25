# Goodbooks -> Existing Books Subsystem Plan

Goal: import Goodbooks metadata into the existing `books` subsystem (`models.Book`, `BooksRepository`, `BookService`, `/books` routes), not a parallel schema.

Input analysis is based on:
- `goodbooks-10k-extended/export.md`
- `goodbooks-10k-extended/samples/*`
- CSV headers from full dataset files

## 1) Direction

Keep current API contract working:
- `BookRead.id` stays `str`
- `authors` and `genres` stay list-like JSON fields
- existing `/books` endpoints continue to read from `books` table

Use Goodbooks `book_id` as canonical record id in this app by storing it as string in `books.id`.

## 2) Phase 1: Adapt existing `books` table (first)

Create one Alembic migration that extends the current `books` table.

Add nullable metadata columns needed for import:
- `source` (`text`, default `goodbooks`)
- `goodreads_book_id` (`bigint`, unique index)
- `best_book_id` (`bigint`)
- `work_id` (`bigint`)
- `books_count` (`integer`)
- `isbn` (`text`)
- `isbn13` (`text`)
- `language_code` (`text`)
- `average_rating` (`numeric(3,2)`)
- `ratings_count` (`integer`)
- `work_ratings_count` (`integer`)
- `work_text_reviews_count` (`integer`)
- `ratings_1`..`ratings_5` (`integer`)
- `original_title` (`text`)
- `description` (`text`)
- `pages` (`integer`)
- `publish_date_raw` (`text`)
- `image_url` (`text`)
- `small_image_url` (`text`)

Notes:
- Keep existing `publication_year` as main year field.
- `authors_2` from source is not required in DB if it duplicates `authors`; skip unless needed later.
- Do not replace current `id/title/authors/genres/publication_year/created_at` behavior.

## 3) Phase 2: Import script for existing subsystem

Create `scripts/import_goodbooks_books.py` (CLI entrypoint) and `scripts/goodbooks_books_importer.py` (core logic).

CLI:
- `--data-dir` path to `goodbooks-10k-extended`
- `--use-samples` for dry-run input
- `--truncate-books` optional full reload
- `--batch-size` default 1000

Source file:
- `books_enriched.csv` (or `samples/books.csv` when `--use-samples`)

Transform rules:
- `id = str(book_id)`
- parse `authors` / `genres` list-like strings with `ast.literal_eval` fallback to empty list
- `publication_year` from `original_publication_year` (safe int conversion)
- `publish_date_raw` from `publishDate` CSV column
- numeric fields parsed with nullable-safe converters
- keep ISBNs as strings

Write strategy:
- PostgreSQL upsert on `books.id`
- update all metadata columns on conflict
- keep `created_at` unchanged for existing rows

## 4) Phase 3: Start DB and run import

Execution:
1. `make db`
2. `make migrate`
3. sample load:
   - `uv run python scripts/import_goodbooks_books.py --data-dir ../goodbooks-10k-extended --use-samples`
4. full load:
   - `uv run python scripts/import_goodbooks_books.py --data-dir ../goodbooks-10k-extended`

## 5) Validation

Quick checks from `make db-shell`:
1. `select count(*) from books;`
2. `select id, title, authors, genres from books order by created_at desc limit 5;`
3. `select count(*) from books where goodreads_book_id is not null;`
4. `select count(*) from books where description is not null and description <> '';`

API checks:
1. `GET /books?page=1&size=20`
2. `GET /books/{id}` for a known imported id (for example `1`)
3. `GET /books?genre=fantasy` to verify genre filtering still works

## 6) Next increment (optional after books import)

If you later need collaborative-signal tables for recommendations, add `ratings`, `tags`, and `book_tags` in a second migration. Keep that separate from initial books-catalog import to reduce risk.

## 7) Implemented interaction tables

Added schema entities:
1. `dataset_users(user_id)` as canonical dataset user registry
2. `ratings(user_id, book_id, rating)` with PK `(user_id, book_id)` and rating check `1..5`
3. `tags(tag_id, tag_name)`
4. `book_tags(goodreads_book_id, tag_id, count)` with PK `(goodreads_book_id, tag_id)`
5. `to_read(user_id, book_id)` with PK `(user_id, book_id)`

`ratings.user_id` and `to_read.user_id` now reference `dataset_users.user_id`.

Importer scripts (CLI and logic):
- `scripts/import_goodbooks_interactions.py` (CLI entrypoint)
- `scripts/goodbooks_interactions_importer.py` (core logic)

Importer script execution:
- `uv run python scripts/import_goodbooks_interactions.py --data-dir ../goodbooks-10k-extended --truncate-tables`

Optional arguments:
- `--use-samples` for dry-run input
- `--batch-size` default 5000
