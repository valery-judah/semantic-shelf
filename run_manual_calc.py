import json

impressions = 0
clicks = 0
matched_clicks = 0
k = 10

with open("artifacts/eval/run_307db40b/raw/telemetry_extract.jsonl", "r") as f:
    for line in f:
        event = json.loads(line)
        if event["event_name"] == "similar_impression":
            impressions += 1
        elif event["event_name"] == "similar_click":
            clicks += 1
            pos = event["payload"].get("position")
            if pos is not None and pos < k:
                matched_clicks += 1

ctr = (matched_clicks / impressions) if impressions > 0 else None

print(f"Total events: {impressions + clicks}")
print(f"Impressions: {impressions}")
print(f"Clicks: {clicks}")
print(f"Matched Clicks at < K ({k}): {matched_clicks}")
print(f"CTR@K ({k}): {ctr}")

