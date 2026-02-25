# Similar Books Feature Spec
## 1. Overview
### 1.1 Purpose

Provide an API that returns an ordered list of book IDs that are similar to a given **anchor** book.

### 1.2 Primary user experience

- **Surface (typical):** Book Details page -> "Similar books" shelf
- **System contract:** Backend returns ordered IDs; clients render the shelf and handle presentation.

### 1.3 Core principle

The online path is a **pure read**: one lookup for neighbors + optional lookup for a popularity fallback.

## 2. Goals and Non-goals
### 2.1 Goals

**MVP (v0)**

- Serve `GET /v1/books/{book_id}/similar` with deterministic output.
- Ensure **non-empty** results for valid `book_id` unless `limit=0` by filling with popularity fallback.
- Provide operational signals: latency, error rate, fallback rate, offline job freshness.

**v1 (evaluation-ready)**

- Add **impression telemetry** (exposure + position) so ranking quality can be evaluated.
- Add basic click/open interaction telemetry.

**v2 (outcome-optimized)**

- Add downstream outcome telemetry (e.g., start/finish) and A/B test support.

### 2.2 Non-goals (explicitly deferred from MVP)

- Personalization / user-aware filtering
- Diversity constraints, category balancing
- Policy filtering and complex eligibility rules
- Near-real-time updates / streaming pipeline
- ANN/vector DB serving
- Multi-armed bandits / exploration

## 3. Definitions

- **Anchor book:** The `book_id` in the request path.
- **Neighbor list:** Precomputed ordered list of similar book IDs for an anchor.
- **Fallback list:** Precomputed ordered list of popular books (global) used to fill gaps.
- **K:** The maximum number of neighbors stored per anchor (e.g., 200).
- **limit:** The number of IDs requested by the client (e.g., 20).
- **algo_id:** Identifier for the recommendation algorithm (e.g., `meta_v0`, `emb_v1`).
- **recs_version:** A monotonically increasing version for published recommendation artifacts.
- **request_id / trace_id:** Correlation identifier propagated across client logs, server logs, and telemetry.

## 4. API Contract
### 4.1 Endpoint

`GET /v1/books/{book_id}/similar?limit=20`

### 4.2 Query parameters

- `limit` (optional, integer)
    - default: 20
    - min: 0
    - max: 100

### 4.3 Response (MVP)

```json
{
  "book_id": "A",
  "similar_book_ids": ["B", "C", "D"],
  "trace_id": "01J...XYZ"
}
```

### 4.4 Response (recommended from v1)

```json
{
  "book_id": "A",
  "similar_book_ids": ["B", "C", "D"],
  "trace_id": "01J...XYZ",
  "algo_id": "meta_v0",
  "recs_version": "2026-02-25T03:00Z"
}
```

### 4.5 Error semantics

- `400 Bad Request`
    - invalid `limit` (non-integer, negative, > max)
- `404 Not Found`
    - unknown `book_id` (anchor is not in catalog)
- `200 OK`
    - even if neighbor list missing/short, service fills from fallback (unless `limit=0`).

### 4.6 Ordering and content rules

- Output is ordered: most similar first.
- Do not return the anchor `book_id`.
- No duplicates.
- If neighbor list shorter than `limit`, fill remaining positions from fallback.

## 5. Functional Requirements
### 5.1 MVP behavior

- **Input:** anchor `book_id`, `limit`
- **Output:** ordered list of up to `limit` book IDs, always filled to `limit` when possible.

### 5.2 Fallback behavior

- Fallback list is global popularity.
- Fill only remaining slots.
- Ensure no duplicates across neighbor + fallback.

### 5.3 Determinism

- For a fixed `(book_id, limit, recs_version)` results should be stable.
- After a publish, results may change.

## 6. Non-functional Requirements
### 6.1 Latency / availability

- p95 latency target: < 100ms (excluding client/network variance)
- Availability: 99.9% for online serving endpoint

### 6.2 Online dependency budget

- Target: 1 store read (neighbors)
- Max: 2 store reads (neighbors + fallback)

### 6.3 Capacity

- Must support typical book-details traffic bursts.
- Must degrade gracefully if store latency spikes (timeout + fallback).

## 7. System Design
### 7.1 High-level architecture

- **Offline batch jobs** compute:
    - `neighbors_by_book` (top-K per book)
    - `popular_global` (top-N)
- **Online service** reads these artifacts and returns results.

### 7.2 Online serving flow (MVP)

1. Validate `book_id` exists in catalog (or treat unknown as 404).
2. Parse `limit` (default 20; cap 100).
3. Lookup `neighbors_by_book[book_id]`.
4. Filter: remove anchor and duplicates.
5. If results < `limit`, lookup `popular_global` and fill remaining.
6. Return response + `trace_id` (+ `algo_id`, `recs_version` when available).

### 7.3 Storage options

Choose one for MVP.

#### Option A: Postgres

- Table: `book_similarities`
    - `book_id` (PK)
    - `neighbor_ids` (array/json)
    - `recs_version` (text)
    - `algo_id` (text)
    - `updated_at`
- Table: `book_popularity`
    - `scope` (PK, e.g., `global`)
    - `book_ids` (array/json)
    - `recs_version`
    - `updated_at`

#### Option B: Redis / KV

- Key: `book:similar:{book_id}` -> value: `[ids...]`
- Key: `book:popular:global` -> value: `[ids...]`
- Optional: `book:recs:meta` -> current `recs_version`, `algo_id`

### 7.4 Offline pipeline (MVP)
#### 7.4.1 Inputs

- Catalog data (book_id, author, series, genres/tags)
- Optional: description text (deferred for MVP algorithm unless already available)

#### 7.4.2 Algorithm (MVP: metadata heuristic)

Compute similarity score between anchor and candidate using weighted features:

- same author
- same series
- genre/tag overlap (e.g., Jaccard)

Output: top-K candidates per anchor.

#### 7.4.3 Jobs

- `job_compute_neighbors`
    - outputs `neighbors_by_book`
- `job_compute_popularity`
    - outputs `popular_global`

#### 7.4.4 Schedule and freshness

- Batch frequency: daily (initially)
- Freshness SLO: publish within 24h of schedule
- Serve last known good artifacts if job fails.

#### 7.4.5 Publish strategy

**MVP:** write-in-place.

**v1+:** publish to versioned location + atomic pointer flip.

## 8. Telemetry
### 8.1 Principles

- Telemetry must support **debugging now** and **evaluation later**.
- Use stable join keys so impressions and interactions can be joined:
    - `request_id` (server-generated) must be returned (as `trace_id`) and logged by clients.
- Avoid PII. If user identity is required later for experimentation, use pseudonymous IDs.

### 8.2 Event taxonomy

- **Request events:** server-side generation and response details
- **Impression events:** what the user was shown and in what positions
- **Interaction events:** what the user clicked or acted on
- **Outcome events:** downstream engagement (start/finish), if/when available

### 8.3 Phase 0 (MVP): Request-only telemetry

Event: `similar_request`

**When:** emitted on every API call

**Schema (recommended fields)**

|Field|Type|Required|Notes|
|---|--:|:-:|---|
|event_name|string|yes|`similar_request`|
|ts|string|yes|ISO-8601 UTC|
|request_id|string|yes|same as `trace_id`|
|anchor_book_id|string|yes||
|limit|int|yes||
|returned_count|int|yes||
|neighbors_count|int|yes|number taken from neighbors list|
|fallback_count|int|yes|number filled from popularity|
|algo_id|string|no (v0) / yes (v1)|e.g., `meta_v0`|
|recs_version|string|no (v0) / yes (v1)|artifact version|
|latency_ms|int|yes|end-to-end service latency|
|status_code|int|yes|HTTP status|
|error_type|string|no|if non-200|

**Payload example**

```json
{
  "event_name": "similar_request",
  "ts": "2026-02-25T18:10:11Z",
  "request_id": "01J...XYZ",
  "anchor_book_id": "A",
  "limit": 20,
  "returned_count": 20,
  "neighbors_count": 12,
  "fallback_count": 8,
  "algo_id": "meta_v0",
  "recs_version": "2026-02-25T03:00Z",
  "latency_ms": 24,
  "status_code": 200
}
```

### 8.4 Phase 1 (Evaluation-ready): Impression telemetry

Event: `similar_impression`

**When:** emitted by the client when the shelf is actually rendered.

**Schema**

|Field|Type|Required|Notes|
|---|--:|:-:|---|
|event_name|string|yes|`similar_impression`|
|ts|string|yes|ISO-8601 UTC|
|request_id|string|yes|MUST match API `trace_id`|
|surface|string|yes|e.g., `book_detail_similar`|
|anchor_book_id|string|yes||
|shown_book_ids|array|yes|ordered as shown|
|positions|array|yes|typically 0..k-1|
|algo_id|string|yes||
|recs_version|string|yes||
|client_platform|string|no|ios/android/web|
|app_version|string|no||

**Payload example**

```json
{
  "event_name": "similar_impression",
  "ts": "2026-02-25T18:10:15Z",
  "request_id": "01J...XYZ",
  "surface": "book_detail_similar",
  "anchor_book_id": "A",
  "shown_book_ids": ["B","C","D"],
  "positions": [0,1,2],
  "algo_id": "meta_v0",
  "recs_version": "2026-02-25T03:00Z",
  "client_platform": "ios",
  "app_version": "1.12.0"
}
```

### 8.5 Phase 2 (Outcome-ready): Interaction telemetry

At minimum, capture a click/open event attributable to the impression.

Event: `similar_click`

**Schema**

|Field|Type|Required|Notes|
|---|--:|:-:|---|
|event_name|string|yes|`similar_click`|
|ts|string|yes|ISO-8601 UTC|
|request_id|string|yes|join to impression/request|
|anchor_book_id|string|yes||
|clicked_book_id|string|yes||
|position|int|yes|position at time of click|
|algo_id|string|yes||
|recs_version|string|yes||

Then extend with downstream actions as product supports:

- `shelf_add`
- `reading_start`
- `reading_finish`
- `rating`

### 8.6 Data retention and privacy

- Store event data under standard analytics retention.
- No raw PII.
- If user/device identifiers are required for A/B, use pseudonymous IDs and document access controls.

## 9. Observability
### 9.1 Service-level metrics (Phase 0)

- **Traffic:** QPS, request volume by status_code
- **Latency:** p50/p95/p99 overall; dependency latency for store calls
- **Errors:** 4xx/5xx rates; timeout counts
- **Fallback:**
    - fallback ratio = `fallback_count > 0` / total
    - avg fallback_count
- **Result integrity:**
    - empty result rate (should be ~0 except limit=0)
    - duplicate rate (should be 0)

### 9.2 Offline job metrics (Phase 0)

- job success/failure
- duration
- artifact publish timestamp
- coverage: % of books with >= K neighbors
- distribution of neighbor list lengths

### 9.3 Tracing (Phase 0)

- Propagate `request_id` / `trace_id` across:
    - edge/API gateway
    - service handler
    - store client calls
- Include spans for store reads with latency + errors.

### 9.4 Dashboards

**Dashboard: Similar Books API**

- Latency (p50/p95/p99)
- Error rate
- Fallback ratio over time
- QPS

**Dashboard: Offline Artifacts**

- Last publish time
- Job status history
- Coverage and distribution shifts

### 9.5 Alerts

- p95 latency regression above threshold
- 5xx error rate above threshold
- fallback ratio spike (possible artifact outage)
- offline publish freshness breach (no publish within N hours)

## 10. Evaluation
### 10.1 Evaluation strategy by phase

**Phase 0 (MVP): sanity and integrity checks only**

- Coverage: % anchors with neighbors
- Integrity: no duplicates, no anchor leakage
- Stability across requests for same `(book_id, recs_version)`

**Phase 1 (Evaluation-ready): exposure-aware offline evaluation**

Requires `similar_impression` + click/open events.

- Build datasets: impressions with positions + interactions within a time window
- Metrics:
    - CTR@K (clicks per impression)
    - NDCG@K / MAP@K using click/open as relevance proxy
    - Long-tail share, coverage, novelty (optional)

**Phase 2 (Outcome-ready): optimize for downstream outcomes**

Requires `reading_start`, `reading_finish`, etc.

- Online A/B metrics:
    - Primary: start rate, finish rate (choose based on product goal)
    - Secondary: CTR/open, add-to-shelf
    - Guardrails: latency, errors, bounce/back

### 10.2 Offline evaluation details (Phase 1)

- Define an evaluation window (e.g., 24h post-impression).
- Deduplicate multiple clicks per impression (policy: first click only, or any click).
- Handle position bias:
    - report metrics by position bucket
    - consider inverse propensity weighting later (optional)

### 10.3 Online experimentation requirements (Phase 2)

- Stable bucketing key (user_id/device_id/session_id)
- Always log `algo_id` and `recs_version` with impressions and interactions
- Rollback mechanism to prior version

## 11. Rollout Plan
### 11.1 Phase 0 (MVP)

- Implement endpoint + read path
- Implement offline jobs (neighbors + popularity)
- Implement request telemetry
- Implement dashboards/alerts for SLO + freshness

### 11.2 Phase 1 (Evaluation-ready)

- Add impression event instrumentation
- Add click/open instrumentation
- Add offline evaluation notebook/pipeline that computes ranking metrics

### 11.3 Phase 2 (Outcome-ready)

- Add downstream outcome events
- Add A/B testing framework integration
- Iterate algorithms (embeddings, collaborative signals, rerankers)

## 12. Risks and Edge Cases
### 12.1 Cold start

- New books without metadata -> sparse neighbors
- Mitigation: popularity fallback + minimum metadata requirements

### 12.2 Feedback loops

- Popularity fallback can amplify already-popular items.
- Mitigation (later): diversify fallback, cap repeats, explore long-tail.

### 12.3 Data quality

- Missing genres/tags/author fields reduces neighbor quality.
- Mitigation: data validation in offline job; coverage monitoring.

### 12.4 Operational failures

- Offline job fails -> stale recs.
- Mitigation: serve last known good, freshness alerting.

## 13. Open Questions (track explicitly)

- What is the desired freshness cadence (daily vs weekly) given catalog change rate?
- What is the first outcome metric we want to optimize beyond CTR?
- What surfaces will emit impressions (details page only vs more)?
- Do we need dedupe across editions/series in v1?