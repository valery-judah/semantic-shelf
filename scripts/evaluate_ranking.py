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

    for pos, shown_book_id in zip(positions, shown_book_ids):
        if pos == click_position:
            return shown_book_id == clicked_book_id
    return False


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
    args = parser.parse_args()

    impressions = {}
    clicks = defaultdict(list)

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
    finally:
        if args.input != "-":
            input_file.close()

    # Metrics computation
    total_impressions = 0
    total_clicks_attributed = 0

    # For NDCG@K
    ndcg_sum = 0.0

    # For CTR by position
    impressions_by_pos = defaultdict(int)
    clicks_by_pos = defaultdict(int)

    window = timedelta(hours=args.window_hours)

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

    if total_impressions == 0:
        print("No impressions found.")
        return

    overall_ctr = total_clicks_attributed / total_impressions
    avg_ndcg = ndcg_sum / total_impressions

    print("=== Evaluation Results ===")
    print(f"Total Impressions:   {total_impressions}")
    print(f"Attributed Clicks:   {total_clicks_attributed}")
    print(f"Overall CTR:         {overall_ctr:.4f}")
    print(f"NDCG@{args.k}:           {avg_ndcg:.4f}")
    print("\n--- CTR by Position ---")

    max_pos = max(impressions_by_pos.keys()) if impressions_by_pos else -1
    for p in range(max_pos + 1):
        i_count = impressions_by_pos.get(p, 0)
        c_count = clicks_by_pos.get(p, 0)
        ctr = (c_count / i_count) if i_count > 0 else 0.0
        print(f"Pos {p:2d}: {ctr:.4f} (clicks: {c_count}, impressions: {i_count})")


if __name__ == "__main__":
    main()
