# Backend

A small FastAPI service wrapping [`ytmusicapi`](https://ytmusicapi.readthedocs.io/).
It is the only component that holds YouTube Music credentials, and the single
source of truth for how a Shazam identification becomes a video ID.

> Setting this up for the first time? Follow
> **[docs/setup.md](../docs/setup.md)** instead — it walks the whole thing
> end to end. This page is the API and configuration reference.

## API

Every endpoint except `/health` requires:

```
X-API-Key: <your shared secret>
```

A missing header returns **422**, a wrong one **401**.

### `POST /search`

Resolve a title and artists to a YouTube Music video ID.

```jsonc
// request
{ "title": "295", "artists": ["Sidhu Moose Wala"] }   // artists optional

// response — match
{
  "found": true,
  "video_id": "n_FCrCQ6-bA",
  "matched_title": "295",
  "matched_artists": ["Sidhu Moose Wala"]
}

// response — no match (still HTTP 200)
{ "found": false, "video_id": null, "matched_title": null, "matched_artists": [] }
```

`matched_title` / `matched_artists` let a caller show or verify what was chosen.
"Not found" is a normal outcome, not an error status.

### `POST /add-to-playlist`

Append a video ID to the configured playlist, skipping duplicates.

```jsonc
// request
{ "video_id": "n_FCrCQ6-bA" }

// response
{ "added": true }    // added
{ "added": false }   // already in the playlist — not an error
```

Idempotent, which is what makes rerunning the backfill safe.

### `GET /health`

`{"status": "ok"}`. No auth — point your host's health check here.

## Configuration

All three are required environment variables. See
[`.env.example`](.env.example).

| Variable | What it is |
|---|---|
| `API_KEY` | Shared secret checked against `X-API-Key`. Generate with `openssl rand -hex 32`. |
| `PLAYLIST_ID` | The playlist you created by hand; from its URL. |
| `YTMUSIC_AUTH_JSON` | `browser.json` from `ytmusicapi browser`, collapsed to one line. **Live Google session cookies.** |

`PLAYLIST_ID` is read at import time, so the process won't start without it —
deliberate, so misconfiguration fails at deploy rather than on your first share.
`YTMUSIC_AUTH_JSON` is read lazily on the first real request.

## Running locally

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # fill in the three values
set -a && source .env && set +a
uvicorn app.main:app --reload
```

> Use `set -a && source .env && set +a`, **not** `export $(cat .env | xargs)` —
> the latter mangles `YTMUSIC_AUTH_JSON`, which contains spaces and commas.

Interactive API docs at http://localhost:8000/docs.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

No credentials or network needed — `ytmusicapi` is stubbed and `conftest.py`
sets placeholder env vars. Lint with `ruff check .`.

## Deploying

Any Docker host works; the image reads `$PORT`.

```bash
docker build -t shazam-to-ytmusic .
docker run -p 8080:8080 \
  -e API_KEY=... -e PLAYLIST_ID=... -e YTMUSIC_AUTH_JSON='...' \
  shazam-to-ytmusic
```

Platform-specific instructions — Render (free, no card), Fly.io, Cloud Run, and
self-hosting — are in
[docs/setup.md](../docs/setup.md#stage-3--deploy-the-backend).

**Always serve over HTTPS.** The API key travels in a header on every request.

## Code map

| File | What it does |
|---|---|
| [`app/main.py`](app/main.py) | The endpoints and their request/response models |
| [`app/matching.py`](app/matching.py) | Search + the artist-overlap tiebreaker |
| [`app/ytmusic_client.py`](app/ytmusic_client.py) | `ytmusicapi` client, auth from env, playlist dedupe |
| [`app/auth.py`](app/auth.py) | The `X-API-Key` check |

How matching works and why it's built this way:
[docs/architecture.md](../docs/architecture.md#matching-and-where-it-falls-short).
