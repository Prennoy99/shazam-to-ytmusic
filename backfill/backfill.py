#!/usr/bin/env python3
"""
One-time backfill: read historical Shazam identifications from a CSV export
and run each one through the same backend /search + /add-to-playlist
endpoints used by the live Android pipeline.

The exact column names depend on how the export was produced (Shazam's own
CSV export vs. an Apple privacy-portal data request) -- pass --title-column
and --artist-column if the defaults ("title" / "artist") don't match your
file. Run with --dry-run first to confirm the column mapping before it
starts hitting the backend.

Usage:
    pip install -r requirements.txt
    python backfill.py --csv shazam_history.csv --backend-url https://... --api-key ... --dry-run
    python backfill.py --csv shazam_history.csv --backend-url https://... --api-key ...
"""
import argparse
import csv
import sys
import time

import requests


def split_artists(raw: str) -> list[str]:
    if not raw:
        return []
    parts = raw.replace("&", ",").split(",")
    return [p.strip() for p in parts if p.strip()]


def process_row(session: requests.Session, base_url: str, title: str, artists: list[str]) -> str:
    """Returns one of: 'added', 'already_present', 'not_found', 'error'."""
    try:
        resp = session.post(f"{base_url}/search", json={"title": title, "artists": artists}, timeout=30)
        resp.raise_for_status()
        result = resp.json()
    except requests.RequestException as e:
        return f"error (search: {e})"

    if not result.get("found"):
        return "not_found"

    video_id = result["video_id"]
    try:
        resp = session.post(f"{base_url}/add-to-playlist", json={"video_id": video_id}, timeout=30)
        resp.raise_for_status()
        added = resp.json().get("added", False)
    except requests.RequestException as e:
        return f"error (add: {e})"

    return "added" if added else "already_present"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--csv", required=True, help="Path to the Shazam history export CSV")
    parser.add_argument("--backend-url", required=True, help="Deployed backend URL, no trailing slash")
    parser.add_argument("--api-key", required=True, help="Must match the backend's API_KEY")
    parser.add_argument("--title-column", default="title")
    parser.add_argument("--artist-column", default="artist")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds to wait between rows")
    parser.add_argument("--log", default="backfill_results.csv", help="Where to write per-row results")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and print rows without calling the backend")
    args = parser.parse_args()

    backend_url = args.backend_url.rstrip("/")

    with open(args.csv, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if args.title_column not in reader.fieldnames or args.artist_column not in reader.fieldnames:
            print(f"Columns {reader.fieldnames} do not contain "
                  f"'{args.title_column}' / '{args.artist_column}'. "
                  f"Pass --title-column / --artist-column to match your export.", file=sys.stderr)
            sys.exit(1)
        rows = list(reader)

    print(f"Loaded {len(rows)} rows from {args.csv}")

    if args.dry_run:
        for row in rows[:20]:
            title = row[args.title_column].strip()
            artists = split_artists(row[args.artist_column])
            print(f"  {title!r} -> artists={artists}")
        if len(rows) > 20:
            print(f"  ... and {len(rows) - 20} more")
        return

    session = requests.Session()
    session.headers.update({"X-API-Key": args.api_key})

    counts: dict[str, int] = {}
    with open(args.log, "w", newline="", encoding="utf-8") as logfile:
        writer = csv.writer(logfile)
        writer.writerow(["title", "artists", "status"])

        for i, row in enumerate(rows, start=1):
            title = row[args.title_column].strip()
            artists = split_artists(row[args.artist_column])
            if not title:
                continue

            status = process_row(session, backend_url, title, artists)
            counts[status] = counts.get(status, 0) + 1
            writer.writerow([title, "; ".join(artists), status])
            logfile.flush()

            print(f"[{i}/{len(rows)}] {title} -> {status}")
            time.sleep(args.delay)

    print("\nDone.")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")
    print(f"\nFull results written to {args.log}")


if __name__ == "__main__":
    main()
