#!/usr/bin/env python3
"""
merge_state.py

Safely merges newly-processed document URLs into state.json.
The agent should NOT hand-edit state.json directly. Instead, it writes a
small JSON file (new_urls.json) listing the URLs it processed this run,
then calls this script to merge them in.

Usage:
    python3 merge_state.py --state state.json --new new_urls.json

new_urls.json format:
    ["https://drive.google.com/file/d/abc123/view", "https://example.com/minutes.pdf"]
"""

import json
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"ERROR reading {path}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, help="Path to state.json")
    parser.add_argument("--new", required=True, help="Path to new_urls.json")
    parser.add_argument("--log", default="run_log.jsonl", help="Path to append-only run log")
    args = parser.parse_args()

    state_path = Path(args.state)
    new_path = Path(args.new)

    state = load_json(state_path, {"seen_pdf_urls": []})
    new_urls = load_json(new_path, [])

    if not isinstance(new_urls, list):
        print("ERROR: new_urls.json must be a JSON array of URL strings", file=sys.stderr)
        sys.exit(1)

    existing = set(state.get("seen_pdf_urls", []))
    added = [u for u in new_urls if u not in existing]

    state["seen_pdf_urls"] = sorted(existing.union(new_urls))
    state["last_run"] = datetime.now(timezone.utc).isoformat()

    # Write state.json back atomically (write to temp, then rename)
    tmp_path = state_path.with_suffix(".tmp")
    with open(tmp_path, "w") as f:
        json.dump(state, f, indent=2)
    tmp_path.replace(state_path)

    # Append a one-line log entry so failures/empty runs are visible over time
    log_entry = {
        "timestamp": state["last_run"],
        "new_urls_added": len(added),
        "total_seen": len(state["seen_pdf_urls"]),
    }
    with open(args.log, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(f"Merged {len(added)} new URL(s). Total seen: {len(state['seen_pdf_urls'])}.")


if __name__ == "__main__":
    main()
