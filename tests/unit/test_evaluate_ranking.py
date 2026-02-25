import json
import subprocess
import sys
import tempfile

from scripts.evaluate_ranking import compute_ndcg_at_k


def test_compute_ndcg_at_k():
    assert compute_ndcg_at_k(0, 10) == 1.0
    assert round(compute_ndcg_at_k(1, 10), 2) == 0.63
    assert compute_ndcg_at_k(10, 10) == 0.0
    assert compute_ndcg_at_k(None, 10) == 0.0


def test_evaluate_ranking_script():
    logs = [
        {
            "event_name": "similar_impression",
            "ts": "2026-02-25T10:00:00Z",
            "request_id": "r1",
            "shown_book_ids": ["b1", "b2"],
            "positions": [0, 1],
        },
        {
            "event_name": "similar_click",
            "ts": "2026-02-25T10:05:00Z",
            "request_id": "r1",
            "clicked_book_id": "b1",
            "position": 0,
        },
        # Outside window click should be ignored
        {
            "event_name": "similar_click",
            "ts": "2026-02-26T10:05:00Z",
            "request_id": "r1",
            "clicked_book_id": "b1",
            "position": 0,
        },
        {
            "event_name": "similar_impression",
            "ts": "2026-02-25T11:00:00Z",
            "request_id": "r2",
            "shown_book_ids": ["b3", "b4"],
            "positions": [0, 1],
        },
    ]

    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        for log in logs:
            f.write(json.dumps(log) + "\n")
        f.flush()

        result = subprocess.run(
            [sys.executable, "-m", "scripts.evaluate_ranking", "--input", f.name],
            capture_output=True,
            text=True,
        )

        output = result.stdout
        assert "Total Impressions:   2" in output
        assert "Attributed Clicks:   1" in output
        assert "Overall CTR:         0.5000" in output
        assert "NDCG@10:           0.5000" in output
        assert "Pos  0: 0.5000" in output


def test_evaluate_ranking_ignores_clicks_not_in_impression():
    logs = [
        {
            "event_name": "similar_impression",
            "ts": "2026-02-25T10:00:00Z",
            "request_id": "r1",
            "shown_book_ids": ["b1", "b2"],
            "positions": [0, 1],
        },
        # Wrong clicked book for position 0 -> should be ignored
        {
            "event_name": "similar_click",
            "ts": "2026-02-25T10:01:00Z",
            "request_id": "r1",
            "clicked_book_id": "b9",
            "position": 0,
        },
        # Position 9 was not shown -> should be ignored
        {
            "event_name": "similar_click",
            "ts": "2026-02-25T10:02:00Z",
            "request_id": "r1",
            "clicked_book_id": "b1",
            "position": 9,
        },
        # First valid click should be attributed
        {
            "event_name": "similar_click",
            "ts": "2026-02-25T10:03:00Z",
            "request_id": "r1",
            "clicked_book_id": "b2",
            "position": 1,
        },
    ]

    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        for log in logs:
            f.write(json.dumps(log) + "\n")
        f.flush()

        result = subprocess.run(
            [sys.executable, "-m", "scripts.evaluate_ranking", "--input", f.name],
            capture_output=True,
            text=True,
        )

        output = result.stdout
        assert "Total Impressions:   1" in output
        assert "Attributed Clicks:   1" in output
        assert "Overall CTR:         1.0000" in output
        assert "Pos  0: 0.0000" in output
        assert "Pos  1: 1.0000" in output


def test_evaluate_ranking_outcomes_attribution():
    logs = [
        {
            "event_name": "similar_impression",
            "ts": "2026-02-25T10:00:00Z",
            "request_id": "r1",
            "shown_book_ids": ["b1", "b2"],
            "positions": [0, 1],
        },
        # Shelf add for b1 (should be attributed)
        {
            "event_name": "similar_shelf_add",
            "ts": "2026-02-25T11:00:00Z",
            "request_id": "r1",
            "book_id": "b1",
        },
        # Reading start for b1 (should be attributed)
        {
            "event_name": "similar_reading_start",
            "ts": "2026-02-25T12:00:00Z",
            "request_id": "r1",
            "book_id": "b1",
        },
        # Duplicate reading start (should be deduplicated to 1 start per impression)
        {
            "event_name": "similar_reading_start",
            "ts": "2026-02-25T13:00:00Z",
            "request_id": "r1",
            "book_id": "b1",
        },
        # Reading finish for b2 (should be attributed)
        {
            "event_name": "similar_reading_finish",
            "ts": "2026-02-26T10:00:00Z",
            "request_id": "r1",
            "book_id": "b2",
        },
        # Rating for b1 (first rating)
        {
            "event_name": "similar_rating",
            "ts": "2026-02-26T11:00:00Z",
            "request_id": "r1",
            "book_id": "b1",
            "rating_value": 4,
        },
        # Rating for b1 (latest rating, should overwrite previous)
        {
            "event_name": "similar_rating",
            "ts": "2026-02-26T12:00:00Z",
            "request_id": "r1",
            "book_id": "b1",
            "rating_value": 5,
        },
        # Rating for book not in impression (should be ignored)
        {
            "event_name": "similar_rating",
            "ts": "2026-02-26T12:00:00Z",
            "request_id": "r1",
            "book_id": "b9",
            "rating_value": 1,
        },
        # Another impression
        {
            "event_name": "similar_impression",
            "ts": "2026-02-27T10:00:00Z",
            "request_id": "r2",
            "shown_book_ids": ["b3", "b4"],
            "positions": [0, 1],
        },
    ]

    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        for log in logs:
            f.write(json.dumps(log) + "\n")
        f.flush()

        result = subprocess.run(
            [sys.executable, "-m", "scripts.evaluate_ranking", "--input", f.name],
            capture_output=True,
            text=True,
        )

        output = result.stdout
        # 2 impressions total
        # r1 has: 1 shelf add, 1 start, 1 finish, 1 rating of 5
        # r2 has: nothing
        assert "Total Impressions:   2" in output
        assert "Add-to-Shelf Rate:   0.5000 (1 attributed)" in output
        assert "Start Rate:          0.5000 (1 attributed)" in output
        assert "Finish Rate:         0.5000 (1 attributed)" in output
        assert "Avg Rating:          5.0000 (1 attributed)" in output


def test_evaluate_ranking_outcomes_window():
    logs = [
        {
            "event_name": "similar_impression",
            "ts": "2026-02-25T10:00:00Z",
            "request_id": "r1",
            "shown_book_ids": ["b1"],
            "positions": [0],
        },
        # Shelf add just outside of default 168h window (7 days = 168h)
        # 2026-02-25 + 7 days = 2026-03-04T10:00:00Z
        {
            "event_name": "similar_shelf_add",
            "ts": "2026-03-04T11:00:00Z",  # 169h later
            "request_id": "r1",
            "book_id": "b1",
        },
    ]

    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        for log in logs:
            f.write(json.dumps(log) + "\n")
        f.flush()

        result = subprocess.run(
            [sys.executable, "-m", "scripts.evaluate_ranking", "--input", f.name],
            capture_output=True,
            text=True,
        )

        output = result.stdout
        assert "Add-to-Shelf Rate:   0.0000 (0 attributed)" in output
