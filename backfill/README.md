# Backfill

A one-time CLI that replays your historical Shazam identifications through the
same `/search` + `/add-to-playlist` endpoints the phone uses — so your whole
listening history lands in the playlist, matched by identical logic.

Runs locally. Nothing to deploy.

## Getting your history

Shazam's own CSV export wasn't available from the app or website on my account,
so the route is an Apple data request:

1. [privacy.apple.com](https://privacy.apple.com) → *Request a copy of your data*
   → select the Shazam data.
2. Wait — this takes **hours to several days**.
3. Unzip and find the CSV of identifications.

*Found a faster export path? Please [open an issue](../../../issues) — that would
help everyone.*

## Usage

Column names vary between export formats, so **dry-run first, every time**:

```bash
pip install -r requirements.txt

python3 backfill.py --csv <export.csv> \
  --backend-url https://<your-service> \
  --api-key <your key> \
  --dry-run
```

That prints the first 20 parsed rows without touching the backend. If the titles
and artists look wrong, remap the columns and dry-run again:

```bash
python3 backfill.py --csv <export.csv> ... \
  --title-column "Track Name" --artist-column "Artist Name" --dry-run
```

When the parse looks right, drop `--dry-run`.

### Options

| Flag | Default | What it does |
|---|---|---|
| `--csv` | *required* | Path to the export |
| `--backend-url` | *required* | Your backend, no trailing slash |
| `--api-key` | *required* | Must match the backend's `API_KEY` |
| `--title-column` | `title` | Column holding the song title |
| `--artist-column` | `artist` | Column holding the artist(s) |
| `--delay` | `0.5` | Seconds between rows |
| `--log` | `backfill_results.csv` | Per-row result log |
| `--dry-run` | off | Parse and print, don't call the backend |

## Results

Every row is written to `backfill_results.csv` with one of:

| Status | Meaning |
|---|---|
| `added` | Matched and added |
| `already_present` | Matched, already in the playlist |
| `not_found` | No YouTube Music match |
| `error (...)` | Network or HTTP failure, with detail |

Afterwards, filter for `not_found` and `error` and handle those by hand. A handful
of misses across a few hundred songs is normal — usually regional catalogue gaps
or unusual artist formatting.

> `backfill_results.csv` is your listening history. It's gitignored; keep it that
> way.

**Rerunning is safe.** The backend's duplicate check means already-added songs
come back as `already_present` rather than piling up. If a run dies halfway, just
run it again.

## Notes

- On a free-tier host, the **first** request wakes the instance (30–50s) and the
  rest are fast. Hitting `/health` first avoids an early timeout.
- Everything failing with `error (search: 401)` means your `--api-key` is wrong.
- More in [docs/troubleshooting.md](../docs/troubleshooting.md#backfill-columns--do-not-contain-title--artist).

## Tests

```bash
pip install -r requirements.txt pytest
pytest
```
