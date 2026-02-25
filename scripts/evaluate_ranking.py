import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta


# ISO 8601 format parser
def parse_ts(ts_str: str) -> datetime:
    # Handle "Z" and fractional seconds
    ts_str = ts_str.replace("Z", "+00:00")
    return datetime.fromisoformat(ts_str)


def compute_ndcg_at_k(click_position: int | None, k: int) -> float:
    """
    Computes NDCG@K given a single click position (0-indexed).
    Since we dedup to max 1 click per impression, IDCG is always 1.0
    (best case is click at position 0: 1 / log2(1+1) = 1.0).
    """
    if click_position is None or click_position >= k:
        return 0.0
    # DCG = rel / log2(rank + 1). Here rank is 1-indexed, so rank = pos + 1
    # Thus, log2(pos + 1 + 1) = log2(pos + 2)
    return 1.0 / math.log2(click_position + 2)


def click_matches_impression(click: dict, impression: dict) -> bool:
    shown_book_ids = impression.get("shown_book_ids", [])
    positions = impression.get("positions", [])
    clicked_book_id = click.get("clicked_book_id")
    click_position = click.get("position")

    if clicked_book_id is None or click_position is None:
        return False
    if click_position not in positions:
        return False

    for pos, shown_book_id in zip(positions, shown_book_ids, strict=False):
        if pos == click_position:
            return shown_book_id == clicked_book_id
    return False


def outcome_matches_impression(outcome: dict, impression: dict) -> bool:
    shown_book_ids = impression.get("shown_book_ids", [])
    book_id = outcome.get("book_id")
    return book_id is not None and book_id in shown_book_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate ranking from telemetry logs.")
    parser.add_argument(
        "--input",
        type=str,
        default="-",
        help="Input JSONL file containing telemetry events. Default is stdin.",
    )
    parser.add_argument("--k", type=int, default=10, help="K for NDCG@K and CTR@K evaluation.")
    parser.add_argument("--window-hours", type=int, default=24, help="Attribution window in hours.")
    parser.add_argument(
        "--outcome-window-hours",
        type=int,
        default=168,
        help="Attribution window for downstream outcomes in hours.",
    )
    args = parser.parse_args()

    impressions = {}
    clicks = defaultdict(list)
    shelf_adds = defaultdict(list)
    reading_starts = defaultdict(list)
    reading_finishes = defaultdict(list)
    ratings = defaultdict(list)

    input_file = sys.stdin if args.input == "-" else open(args.input)

    try:
        for line in input_file:
            line = line.strip()
            if not line:
                continue

            try:
                # Handle logs that are prefixed with "TELEMETRY: "
                if "TELEMETRY:" in line:
                    json_str = line.split("TELEMETRY:", 1)[1].strip()
                    event = json.loads(json_str)
                else:
                    event = json.loads(line)
            except json.JSONDecodeError:
                continue

            event_name = event.get("event_name")
            req_id = event.get("request_id")

            if not event_name or not req_id:
                continue

            if event_name == "similar_impression":
                impressions[req_id] = event
            elif event_name == "similar_click":
                clicks[req_id].append(event)
            elif event_name == "similar_shelf_add":
                shelf_adds[req_id].append(event)
            elif event_name == "similar_reading_start":
                reading_starts[req_id].append(event)
            elif event_name == "similar_reading_finish":
                reading_finishes[req_id].append(event)
            elif event_name == "similar_rating":
                ratings[req_id].append(event)
    finally:
        if args.input != "-":
            input_file.close()

    # Metrics computation
    total_impressions = 0
    total_clicks_attributed = 0
    ndcg_sum = 0.0
    impressions_by_pos = defaultdict(int)
    clicks_by_pos = defaultdict(int)

    # Outcome metrics
    total_shelf_adds_attributed = 0
    total_starts_attributed = 0
    total_finishes_attributed = 0
    attributed_ratings = []

    window = timedelta(hours=args.window_hours)
    outcome_window = timedelta(hours=args.outcome_window_hours)

    for req_id, imp in impressions.items():
        total_impressions += 1
        imp_ts = parse_ts(imp["ts"])
        positions = imp.get("positions", [])

        # Record impressions per position
        for p in positions:
            impressions_by_pos[p] += 1

        # Attribution: find the first click within the window
        valid_clicks = []
        for c in clicks.get(req_id, []):
            c_ts = parse_ts(c["ts"])
            if timedelta(0) <= (c_ts - imp_ts) <= window and click_matches_impression(c, imp):
                valid_clicks.append(c)

        # Sort by timestamp to enforce "first-click dedup"
        valid_clicks.sort(key=lambda c: parse_ts(c["ts"]))

        attributed_click_pos = None
        if valid_clicks:
            first_click = valid_clicks[0]
            attributed_click_pos = first_click.get("position")

            if attributed_click_pos is not None:
                total_clicks_attributed += 1
                clicks_by_pos[attributed_click_pos] += 1

        ndcg_sum += compute_ndcg_at_k(attributed_click_pos, args.k)

        # Outcomes Attribution

        has_shelf_add = any(
            timedelta(0) <= (parse_ts(sa["ts"]) - imp_ts) <= outcome_window
            and outcome_matches_impression(sa, imp)
            for sa in shelf_adds.get(req_id, [])
        )
        if has_shelf_add:
            total_shelf_adds_attributed += 1

        has_start = any(
            timedelta(0) <= (parse_ts(rs["ts"]) - imp_ts) <= outcome_window
            and outcome_matches_impression(rs, imp)
            for rs in reading_starts.get(req_id, [])
        )
        if has_start:
            total_starts_attributed += 1

        has_finish = any(
            timedelta(0) <= (parse_ts(rf["ts"]) - imp_ts) <= outcome_window
            and outcome_matches_impression(rf, imp)
            for rf in reading_finishes.get(req_id, [])
        )
        if has_finish:
            total_finishes_attributed += 1

        valid_ratings = [
            r
            for r in ratings.get(req_id, [])
            if timedelta(0) <= (parse_ts(r["ts"]) - imp_ts) <= outcome_window
            and outcome_matches_impression(r, imp)
        ]

        book_to_latest_rating = {}
        for r in valid_ratings:
            book_id = r["book_id"]
            if book_id not in book_to_latest_rating or parse_ts(r["ts"]) > parse_ts(
                book_to_latest_rating[book_id]["ts"]
            ):
                book_to_latest_rating[book_id] = r

        for r in book_to_latest_rating.values():
            if "rating_value" in r:
                attributed_ratings.append(r["rating_value"])

    if total_impressions == 0:
        print("No impressions found.")
        return

    overall_ctr = total_clicks_attributed / total_impressions
    avg_ndcg = ndcg_sum / total_impressions

    add_to_shelf_rate = total_shelf_adds_attributed / total_impressions
    start_rate = total_starts_attributed / total_impressions
    finish_rate = total_finishes_attributed / total_impressions
    avg_rating = sum(attributed_ratings) / len(attributed_ratings) if attributed_ratings else 0.0

    print("=== Evaluation Results ===")
    print(f"Total Impressions:   {total_impressions}")
    print(f"Attributed Clicks:   {total_clicks_attributed}")
    print(f"Overall CTR:         {overall_ctr:.4f}")
    print(f"NDCG@{args.k}:           {avg_ndcg:.4f}")

    print("\n=== Outcome Metrics ===")
    print(
        f"Add-to-Shelf Rate:   {add_to_shelf_rate:.4f} ({total_shelf_adds_attributed} attributed)"
    )
    print(f"Start Rate:          {start_rate:.4f} ({total_starts_attributed} attributed)")
    print(f"Finish Rate:         {finish_rate:.4f} ({total_finishes_attributed} attributed)")
    print(f"Avg Rating:          {avg_rating:.4f} ({len(attributed_ratings)} attributed)")

    print("\n--- CTR by Position ---")

    max_pos = max(impressions_by_pos.keys()) if impressions_by_pos else -1
    for p in range(max_pos + 1):
        i_count = impressions_by_pos.get(p, 0)
        c_count = clicks_by_pos.get(p, 0)
        ctr = (c_count / i_count) if i_count > 0 else 0.0
        print(f"Pos {p:2d}: {ctr:.4f} (clicks: {c_count}, impressions: {i_count})")


if __name__ == "__main__":
    main()
