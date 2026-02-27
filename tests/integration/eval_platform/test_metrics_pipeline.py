from eval.metrics import compute_quality_metrics
from tests.unit.eval_platform.test_metrics import _make_click, _make_impression


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
