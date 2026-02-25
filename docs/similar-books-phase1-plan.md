# Similar Books Phase 1 Implementation Plan

## 1. Overview
Phase 0 delivered the serving path for `GET /v1/books/{book_id}/similar`.

Phase 1 makes the feature evaluation-ready by adding telemetry and an offline metrics pipeline.
The key outcome is reliable measurement of ranking quality (CTR@K, NDCG@K) with
joinable request, impression, and click data.

## 2. Phase 1 Requirements (from `docs/similar-books.md`)
- Add client-side `similar_impression` telemetry with ordered shown IDs and positions.
- Add client-side `similar_click` telemetry attributable to the same request.
- Ensure clients can emit required `algo_id` and `recs_version` fields.
- Build an offline evaluation script to compute CTR@K and NDCG@K with explicit policies for:
  - evaluation window after impression
  - click deduplication
  - position-bucket reporting

## 3. Implementation Steps

### 3.1 Similar API Response Contract (`src/books_rec_api/schemas/similar_books.py`, route handler)
Guarantee that Phase 1 required telemetry fields are available to clients from the read API:
- Include `algo_id` and `recs_version` on successful similar-books responses.
- Keep `trace_id` as the request join key.
- Add/update API tests for response schema and required fields.

### 3.2 Telemetry Schemas (`src/books_rec_api/schemas/telemetry.py`)
Define Pydantic models for strict validation of telemetry payloads.
- `SimilarImpressionEvent` required fields:
  - `event_name`, `ts`, `request_id`, `surface`, `anchor_book_id`
  - `shown_book_ids`, `positions`, `algo_id`, `recs_version`
- `SimilarImpressionEvent` optional fields:
  - `client_platform`, `app_version`
- `SimilarClickEvent` required fields:
  - `event_name`, `ts`, `request_id`, `anchor_book_id`
  - `clicked_book_id`, `position`, `algo_id`, `recs_version`
- `EventBatchRequest` supports batched mixed event types.
- Add validation rules:
  - `event_name` must match the model type
  - `positions` length must equal `shown_book_ids` length
  - position values must be non-negative integers

### 3.3 Telemetry Service (`src/books_rec_api/services/telemetry_service.py`)
Create a service that receives validated events and emits structured JSON logs.
- Method: `process_events(events: list[SimilarImpressionEvent | SimilarClickEvent])`
- Include stable fields in every log line (`event_name`, `ts`, `request_id`, `algo_id`, `recs_version`).
- Reject no events at this layer if schema validation already passed.

### 3.4 Dependencies (`src/books_rec_api/dependencies/telemetry.py`)
Create FastAPI dependency `get_telemetry_service` for router injection.

### 3.5 API Endpoint (`src/books_rec_api/api/routes/telemetry.py`)
Add a new router to ingest generic batched events from clients.
- `POST /v1/telemetry/events`:
  - accepts `EventBatchRequest`
  - delegates processing to `TelemetryService`
  - returns `202 Accepted`
- Register router in `src/books_rec_api/api/__init__.py` and include in `main.py`.

### 3.6 Client Instrumentation Plan (mobile/web repos)
Implement or update client emission logic:
- `similar_impression` emitted when shelf is rendered, using:
  - `request_id <- trace_id` from API response
  - `algo_id`, `recs_version` from API response
  - ordered `shown_book_ids` and matching `positions`
- `similar_click` emitted on item open/click with the same `request_id`, `algo_id`, `recs_version`.
- Add a client-side guard so clicks without a known request context are dropped or marked as invalid telemetry.

### 3.7 Offline Evaluation Script (`scripts/evaluate_ranking.py`)
Create an evaluation script that reads JSONL telemetry from file or stdin and computes ranking metrics.
- Join events primarily on `request_id`; enforce event type filters.
- Apply explicit evaluation policies:
  - window: clicks within 24h after impression timestamp
  - dedup: at most one click credit per impression (first click)
  - attribution integrity: only clicks matching the matched impression payload are eligible
    - `clicked_book_id` must be present in `shown_book_ids`
    - `position` must match the shown position for that `clicked_book_id`
  - relevance: binary relevance from click attribution
- Compute:
  - CTR@K
  - NDCG@K
  - metrics by position bucket (for position-bias visibility)

### 3.8 Testing
- Unit tests:
  - telemetry schema validation and edge cases
  - telemetry service logging behavior
  - evaluation metric correctness and policy handling
- Integration tests:
  - `POST /v1/telemetry/events` accepts valid mixed event batches
  - invalid payloads return `422`
- API contract tests:
  - similar-books responses include `trace_id`, `algo_id`, `recs_version` in Phase 1 mode

## 4. Acceptance Criteria
1. `GET /v1/books/{book_id}/similar` responses include `trace_id`, `algo_id`, and `recs_version` for successful responses.
2. `POST /v1/telemetry/events` accepts valid `similar_impression` and `similar_click` event batches and returns `202`.
3. Invalid telemetry payloads are rejected with `422 Unprocessable Entity`.
4. Accepted events are emitted in structured JSON logs with joinable keys.
5. `scripts/evaluate_ranking.py` computes correct CTR@K and NDCG@K from sample logs and honors:
   - 24h evaluation window
   - first-click dedup policy
   - impression-consistent click attribution (book and position must match shown shelf)
   - position-bucket output
6. Required checks for this API/logic change pass: `make fmt`, `make lint`, `make type`, and `make test`.
