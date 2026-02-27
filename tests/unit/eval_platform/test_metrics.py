from datetime import UTC, datetime

from eval.metrics import compute_quality_metrics
from eval.schemas.summary import QualityMetrics
from eval.telemetry import TelemetryEvent, TelemetryPayload


def _make_event(
    event_type: str,
    request_id: str,
    idempotency_key: str,
    is_synthetic: bool = True,
    anchor_id: str = "book_1",
    **kwargs,
) -> TelemetryEvent:
    payload = TelemetryPayload(
        request_id=request_id, idempotency_key=idempotency_key, anchor_book_id=anchor_id, **kwargs
    )
    return TelemetryEvent(
        event_name=event_type,
        run_id="run_1",
        is_synthetic=is_synthetic,
        ts=datetime.now(UTC),
        payload=payload,
    )


def _make_impression(
    request_id: str,
    shown: list[str],
    positions: list[int],
    is_synthetic: bool = True,
    idempotency_key: str | None = None,
    anchor_id: str = "book_1",
) -> TelemetryEvent:
    ik = idempotency_key or f"imp_{request_id}"
    return _make_event(
        "similar_impression",
        request_id,
        ik,
        is_synthetic,
        anchor_id,
        shown_book_ids=shown,
        positions=positions,
    )


def _make_click(
    request_id: str,
    clicked: str,
    position: int,
    is_synthetic: bool = True,
    idempotency_key: str | None = None,
    anchor_id: str = "book_1",
) -> TelemetryEvent:
    ik = idempotency_key or f"click_{request_id}"
    return _make_event(
        "similar_click",
        request_id,
        ik,
        is_synthetic,
        anchor_id,
        clicked_book_id=clicked,
        position=position,
    )


def test_empty_events():
    metrics = compute_quality_metrics([])
    assert isinstance(metrics, QualityMetrics)
    assert metrics.k == 10
    assert metrics.by_traffic_type == {}


def test_deduplication():
    # Submit the same event multiple times
    imp1 = _make_impression("r1", ["b1"], [0], idempotency_key="imp_1")
    imp2 = _make_impression("r1", ["b1"], [0], idempotency_key="imp_1")
    click1 = _make_click("r1", "b1", 0, idempotency_key="click_1")
    click2 = _make_click("r1", "b1", 0, idempotency_key="click_1")

    events = [imp1, imp2, click1, click2]
    metrics = compute_quality_metrics(events, k=10)

    bucket = metrics.by_traffic_type["synthetic"]
    assert bucket.impressions == 1
    assert bucket.clicks == 1
    assert bucket.ctr_at_k == 1.0


def test_attribution_rules():
    # Valid impression
    imp = _make_impression("r1", ["b1", "b2"], [0, 1])

    # 1. Matched click
    matched_click = _make_click("r1", "b2", 1)

    # 2. Click with wrong book ID for position
    wrong_book_click = _make_click("r1", "b3", 1, idempotency_key="click_wrong_book")

    # 3. Click with wrong request ID
    wrong_req_click = _make_click("r2", "b2", 1, idempotency_key="click_wrong_req")

    # 4. Click with wrong position
    wrong_pos_click = _make_click("r1", "b2", 0, idempotency_key="click_wrong_pos")

    events = [imp, matched_click, wrong_book_click, wrong_req_click, wrong_pos_click]
    metrics = compute_quality_metrics(events, k=10)

    bucket = metrics.by_traffic_type["synthetic"]
    assert bucket.impressions == 1
    # Total clicks should be 4
    assert bucket.clicks == 4
    # But only 1 matched click
    assert bucket.coverage["matched_clicks"] == 1
    # Thus CTR is 1/1 = 1.0 (since there is only 1 impression)
    assert bucket.ctr_at_k == 1.0

    # CTR by position:
    # Position 0: 0 clicks / 1 impression = 0.0
    # Position 1: 1 matched click / 1 impression = 1.0
    assert bucket.ctr_by_position[0] == 0.0
    assert bucket.ctr_by_position[1] == 1.0


def test_formulas_ctr_at_k():
    # k = 2
    # Imp 1: positions 0, 1, 2
    imp1 = _make_impression("r1", ["a", "b", "c"], [0, 1, 2])
    # Click on pos 0 (counts for k=2)
    click1 = _make_click("r1", "a", 0)

    # Imp 2: positions 2, 3 (no items < k) -> should NOT count towards denominator of CTR@K
    imp2 = _make_impression("r2", ["x", "y"], [2, 3])
    # Click on pos 2 (does not count for k=2)
    click2 = _make_click("r2", "x", 2)

    # Imp 3: positions 0 (counts for k=2)
    imp3 = _make_impression("r3", ["z"], [0])
    # No click

    events = [imp1, click1, imp2, click2, imp3]
    metrics = compute_quality_metrics(events, k=2)

    bucket = metrics.by_traffic_type["synthetic"]

    # Denominator (impressions_with_position_lt_k): imp1 and imp3 have pos < 2, so 2.
    assert bucket.coverage["impressions_with_position_lt_k"] == 2

    # Numerator (matched_clicks_at_positions_lt_k): only click1 is < 2, so 1.
    assert bucket.coverage["matched_clicks_at_positions_lt_k"] == 1

    # CTR@2 = 1 / 2 = 0.5
    assert bucket.ctr_at_k == 0.5

    # Verify by position
    assert bucket.ctr_by_position[0] == 0.5  # 1 click (r1) / 2 impressions (r1, r3)
    assert bucket.ctr_by_position[1] == 0.0  # 0 clicks / 1 impression (r1)
    assert bucket.ctr_by_position[2] == 0.5  # 1 click (r2) / 2 impressions (r1, r2)
    assert bucket.ctr_by_position[3] == 0.0  # 0 clicks / 1 impression (r2)


def test_traffic_splitting():
    # Real traffic
    real_imp = _make_impression("real_r1", ["a"], [0], is_synthetic=False)
    real_click = _make_click("real_r1", "a", 0, is_synthetic=False)

    # Synthetic traffic
    syn_imp = _make_impression("syn_r1", ["b"], [0], is_synthetic=True)

    events = [real_imp, real_click, syn_imp]
    metrics = compute_quality_metrics(events, k=10)

    assert "real" in metrics.by_traffic_type
    assert "synthetic" in metrics.by_traffic_type
    assert "combined" in metrics.by_traffic_type

    # Real bucket
    real_b = metrics.by_traffic_type["real"]
    assert real_b.impressions == 1
    assert real_b.clicks == 1
    assert real_b.ctr_at_k == 1.0

    # Synthetic bucket
    syn_b = metrics.by_traffic_type["synthetic"]
    assert syn_b.impressions == 1
    assert syn_b.clicks == 0
    assert syn_b.ctr_at_k == 0.0

    # Combined bucket
    comb_b = metrics.by_traffic_type["combined"]
    assert comb_b.impressions == 2
    assert comb_b.clicks == 1
    assert comb_b.ctr_at_k == 0.5


def test_missing_payload_fields():
    # Impression with missing positions
    payload = TelemetryPayload(
        request_id="r1", idempotency_key="imp_1", shown_book_ids=None, positions=None
    )
    imp = TelemetryEvent(
        event_name="similar_impression",
        run_id="run_1",
        is_synthetic=True,
        ts=datetime.now(UTC),
        payload=payload,
    )

    # Click with missing click/position
    payload2 = TelemetryPayload(
        request_id="r1", idempotency_key="click_1", clicked_book_id=None, position=None
    )
    click = TelemetryEvent(
        event_name="similar_click",
        run_id="run_1",
        is_synthetic=True,
        ts=datetime.now(UTC),
        payload=payload2,
    )

    events = [imp, click]
    metrics = compute_quality_metrics(events, k=10)

    bucket = metrics.by_traffic_type["synthetic"]
    assert bucket.impressions == 1
    assert bucket.clicks == 1
    assert bucket.ctr_at_k is None  # no pos < k
    assert bucket.coverage["matched_clicks"] == 0


def test_offline_reproducibility(tmp_path):
    from eval.telemetry import read_telemetry_extract

    # Create a dummy telemetry_extract.jsonl
    extract_path = tmp_path / "telemetry_extract.jsonl"

    # Valid impression
    imp = _make_impression("r1", ["b1", "b2"], [0, 1])
    # Matched click
    matched_click = _make_click("r1", "b2", 1)

    with open(extract_path, "w") as f:
        f.write(imp.model_dump_json(by_alias=True) + "\n")
        f.write(matched_click.model_dump_json(by_alias=True) + "\n")

    # Run read_telemetry_extract
    events = read_telemetry_extract(extract_path)
    assert len(events) == 2

    # Run compute_quality_metrics
    metrics = compute_quality_metrics(events, k=10)

    # Assert computed metrics
    bucket = metrics.by_traffic_type["synthetic"]
    assert bucket.impressions == 1
    assert bucket.clicks == 1
    assert bucket.ctr_at_k == 1.0
    assert bucket.coverage["matched_clicks"] == 1
