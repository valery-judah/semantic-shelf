# Similar Books Implementation Plan (MVP)

## 1. Overview
The MVP implementation of the "Similar Books" feature involves creating an online serving layer that queries pre-computed artifacts to find similar books for a given anchor book. The design follows Option A from the spec (`docs/similar-books.md`), where we'll use Postgres for storing the offline pre-calculated lists. The endpoint `GET /v1/books/{book_id}/similar` will fetch up to `limit` books from the `book_similarities` table, and if the count is less than `limit`, it will pad the remaining with IDs from the `book_popularity` table. For the MVP, we will also create two offline jobs that compute similarity and popularity using metadata heuristics.

## 2. Key Changes
- `src/books_rec_api/models.py`: Add `BookSimilarity` and `BookPopularity` SQLAlchemy models.
- `Alembic Migration`: Create a migration for the new tables.
- `src/books_rec_api/schemas/recommendation.py`: Create the `SimilarBooksResponse` Pydantic model for the API response.
- `src/books_rec_api/repositories/books_repository.py`: Add methods to fetch a book by ID, fetch similarities for an anchor book, and fetch global popularity.
- `src/books_rec_api/services/book_service.py`: Add business logic `get_similar_books` to retrieve neighbors, filter duplicates, and fallback to popularity.
- `src/books_rec_api/api/routes/books.py`: Add the new endpoint `GET /v1/books/{book_id}/similar`.
- `scripts/job_compute_popularity.py`: Create an offline script to compute the global popularity list (e.g., top N highest rated/most rated books).
- `scripts/job_compute_neighbors.py`: Create an offline script to calculate book neighbors based on metadata similarity (authors, genres) and populate `book_similarities`.
- `tests/`: Add Unit tests and Integration tests for the service logic and new endpoint.

## 3. Implementation Steps

1. **Database Models & Migrations**
   - Add `BookSimilarity` model in `src/books_rec_api/models.py` with columns: `book_id` (PK), `neighbor_ids` (JSON), `recs_version` (String), `algo_id` (String), `updated_at` (DateTime).
   - Add `BookPopularity` model in `src/books_rec_api/models.py` with columns: `scope` (PK), `book_ids` (JSON), `recs_version` (String), `updated_at` (DateTime).
   - Generate and apply Alembic migration for the new tables (`alembic revision --autogenerate`).

2. **API Schemas**
   - Define `SimilarBooksResponse` in `src/books_rec_api/schemas/recommendation.py` with `book_id`, `similar_book_ids`, `trace_id` (and optional `algo_id`, `recs_version`).

3. **Repository Layer**
   - Update `BooksRepository` with a method `get_similarities(book_id)` to query the `BookSimilarity` table.
   - Update `BooksRepository` with a method `get_popularity(scope="global")` to query the `BookPopularity` table.

4. **Service Layer**
   - Add `get_similar_books(book_id: str, limit: int, trace_id: str)` to `BookService`.
   - Implement the logic: validate book exists (return `None` if not to trigger 404), fetch `neighbors_by_book`, remove anchor/duplicates, fetch `popular_global` if needed to pad up to `limit`. Ensure output size matches `limit` (unless total catalog < limit).

5. **API Route**
   - Add `GET /{book_id}/similar` in `src/books_rec_api/api/routes/books.py`.
   - Inject a random UUID for `trace_id` (for MVP request tracing).
   - Return `404 Not Found` if book doesn't exist.
   - Return `400 Bad Request` if limit < 0 or limit > 100.
   - Emit a rudimentary JSON log for the `similar_request` telemetry event.

6. **Offline Computation Jobs**
   - Implement `scripts/job_compute_popularity.py` using simple criteria (e.g., books with the highest `work_ratings_count` or `average_rating`). It should wipe the `BookPopularity` table and insert a new global row.
   - Implement `scripts/job_compute_neighbors.py` (heuristic based on common genres and authors) to calculate top K (e.g., K=100) neighbors per book and store them in `BookSimilarity`. *Note: we will do this efficiently, but simple enough for MVP.*

7. **Testing**
   - Create unit tests for `BookService.get_similar_books`.
   - Create integration tests for `GET /books/{book_id}/similar` handling valid limit, limit=0, and 404s.

## 4. Technical Considerations
- **Determinism**: The `limit` slicing and fallback mechanism must use sorted/ordered lists to guarantee stable results between job runs. JSON arrays in Postgres preserve order.
- **Latency Budget**: We will try to fetch the anchor book, similarities, and popularity in minimal queries. For example, the `book_service` might just fetch similarities and popularity in two simple queries (or fetch popularity only when needed).
- **Logging**: We'll write a simple JSON log for the `similar_request` event to standard out as specified in Phase 0.

## 5. Success Criteria
- The endpoint `GET /v1/books/{book_id}/similar?limit=N` returns a 200 OK with `limit` book IDs (padding with popular books if neighbors are scarce).
- It does not return the anchor book or any duplicate IDs.
- 400 errors returned for invalid limits and 404 for unknown book IDs.
- The `similar_request` JSON payload is logged to stdout.
- `make test`, `make lint`, `make type`, and `make fmt` all pass successfully.