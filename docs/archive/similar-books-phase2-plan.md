# Similar Books Phase 2 Implementation Plan

## 1. Overview
Phase 1 made the feature evaluation-ready by adding `similar_impression` and `similar_click` telemetry plus offline CTR@K/NDCG@K evaluation.
Phase 2 makes the feature outcome-ready by adding downstream outcome telemetry, explicit attribution policies, and A/B-experiment logging requirements aligned with `docs/similar-books.md`.

## 2. Phase 2 Requirements (from `docs/similar-books.md`)
- Extend interaction telemetry with downstream events:
  - `similar_shelf_add`
  - `similar_reading_start`
  - `similar_reading_finish`
  - `similar_rating`
- Extend offline evaluation output with downstream conversion metrics:
  - Add-to-shelf rate
  - Reading start rate
  - Reading finish rate
  - Average attributed rating
- Define online experimentation requirements:
  - stable bucketing key
  - experiment assignment logging
  - rollback-ready evaluation metadata

## 3. Implementation Steps

### 3.1 Telemetry Schemas (`src/books_rec_api/schemas/telemetry.py`)
Add downstream interaction models inheriting from `TelemetryEventBase`.
All events must include:
- `ts`
- `request_id`
- `anchor_book_id`
- `algo_id`
- `recs_version`

Add the following models:
- `SimilarShelfAddEvent`
  - `event_name: Literal["similar_shelf_add"]`
  - `book_id: str`
- `SimilarReadingStartEvent`
  - `event_name: Literal["similar_reading_start"]`
  - `book_id: str`
- `SimilarReadingFinishEvent`
  - `event_name: Literal["similar_reading_finish"]`
  - `book_id: str`
- `SimilarRatingEvent`
  - `event_name: Literal["similar_rating"]`
  - `book_id: str`
  - `rating_value: int = Field(ge=1, le=5)`

Union updates:
- Add all four models to `TelemetryEvent` discriminated union.
- Preserve existing Phase 1 event parsing behavior.

Ingestion compatibility:
- Existing telemetry ingestion endpoint `POST /telemetry/events` continues to ingest mixed batches.

### 3.2 Attribution Policy (`scripts/evaluate_ranking.py`)
Extend evaluation logic with explicit outcome attribution rules.

Join and validation:
- Join by `request_id`.
- Require outcome `book_id` to exist in the matched impression `shown_book_ids`.
- Ignore outcomes outside the attribution window.

Windows:
- Click window remains configurable via `--window-hours` (default 24h).
- Add downstream window as a separate flag: `--outcome-window-hours` (default 168h / 7 days).

Dedup and credit policy (required for stable metrics):
- Per impression, credit at most one `shelf_add` event.
- Per impression, credit at most one `reading_start` event.
- Per impression, credit at most one `reading_finish` event.
- For ratings, use the most recent valid attributed rating per impression/book pair within window.

Metric formulas:
- `add_to_shelf_rate = attributed_shelf_add_impressions / total_impressions`
- `start_rate = attributed_start_impressions / total_impressions`
- `finish_rate = attributed_finish_impressions / total_impressions`
- `avg_attributed_rating = mean(attributed_rating_values)`

Output:
- Keep existing Phase 1 output (CTR@K, NDCG@K, position buckets).
- Append downstream metrics section with raw counts and rates.

### 3.3 Experimentation Logging Requirements
Define minimal, explicit experiment fields to support Phase 2 A/B analysis.

Required metadata on impression and downstream events:
- `experiment_id: str | None`
- `variant_id: str | None`
- `bucket_key_hash: str | None` (pseudonymous hash, not raw user/device ID)

Rules:
- Do not infer cohort from `algo_id`; `algo_id` remains model/version metadata.
- If experimentation is disabled, fields may be null.
- If experimentation is enabled for a request, the same assignment fields must be present and consistent across related events.

Rollback readiness:
- Keep `algo_id` + `recs_version` on all events for version-level rollback analysis.
- Document the fallback path to prior serving config in rollout docs.

### 3.4 Testing
Unit tests (`tests/unit/test_telemetry.py`):
- Validate discriminator parsing for all new event types.
- Validate rating bounds (`1..5`).
- Validate optional experiment fields if added to base schema.

Integration tests (`tests/integration/test_telemetry_api.py`):
- Mixed batch ingestion with impression, click, and new downstream events returns `202`.
- Invalid downstream payloads return `422`.

Evaluation script tests:
- Add fixtures covering:
  - in-window vs out-of-window outcomes
  - invalid `book_id` attribution
  - dedup behavior for repeated downstream events
  - average attributed rating computation

Regression coverage:
- Preserve Phase 1 CTR@K/NDCG@K behavior and output compatibility.

## 4. Acceptance Criteria
1. `src/books_rec_api/schemas/telemetry.py` includes the four downstream event schemas and updated `TelemetryEvent` union.
2. `POST /telemetry/events` accepts valid mixed event batches including downstream events and rejects invalid payloads with `422`.
3. `scripts/evaluate_ranking.py` reports:
   - Add-to-shelf rate
   - Start rate
   - Finish rate
   - Average attributed rating
4. Outcome attribution rules are implemented and tested:
   - request join by `request_id`
   - shown-book validation
   - separate downstream attribution window
   - explicit dedup/credit policy
5. Experiment logging requirements are documented and do not rely on `algo_id` as cohort assignment.
6. No regressions in Phase 1 telemetry behavior (impression/click ingestion and CTR@K/NDCG@K calculations).
