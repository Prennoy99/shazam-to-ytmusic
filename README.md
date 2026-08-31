# Shazam → YouTube Music

**Shazam a song, hit Share, and it's already playing in full — and saved to a playlist.**

[![Backend](https://github.com/Prennoy99/shazam-sync/actions/workflows/backend.yml/badge.svg)](https://github.com/Prennoy99/shazam-sync/actions/workflows/backend.yml)
[![Android](https://github.com/Prennoy99/shazam-sync/actions/workflows/android.yml/badge.svg)](https://github.com/Prennoy99/shazam-sync/actions/workflows/android.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## The problem this solves

Shazam is great at telling you *what* the song is. It is not great at letting you
**hear the rest of it**. You get a 30-second preview, a wall of streaming-service
buttons, and — if you use a patched YouTube Music client like
[Morphe](https://github.com/Morphe-Team) or [ReVanced](https://revanced.app/) —
your client isn't in that list at all. So the ritual becomes:

> identify → open YouTube Music → retype the title → squint at six near-identical
> results → pick one → remember to add it to a playlist → forget to add it to a playlist

This replaces all of that with **one tap on the Android share sheet.**

```
  Shazam ──share──▶  Shazam Sync  ──▶  backend  ──▶  YouTube Music search
  (any song)         (this app)         (yours)          │
                          │                              ▼
                          │                        best match (video id)
                          ▼                              │
              ┌───────────┴───────────┐                  │
              ▼                       ▼◀─────────────────┘
     plays the full track      appended to your
     in Morphe / ReVanced /    "shazam_finds" playlist
     official YT Music         (duplicates skipped)
```

You never see a UI. The app has no launcher icon. It's a share target and nothing
else — tap, and the song is playing.

## What you get

- **One-tap play.** Full track, in *your* YouTube Music client, not a preview.
- **An automatic "songs I Shazam'd" playlist**, building itself forever, with
  duplicate protection.
- **Works with patched clients.** The target app is a config value, not a
  hardcode — Morphe, ReVanced, or stock YouTube Music.
- **A backfill script** to replay your entire Shazam history (hundreds of songs)
  into that same playlist in one go.
- **No cost.** The backend runs fine on a free tier with no card on file.

## Status & honesty

This started as a personal side project — I built it because the manual ritual
above finally annoyed me enough. It's been running end-to-end on my own phone
(a realme RMX3085, Android 13, Morphe) and it does exactly what it says.

That said, be clear-eyed about what this is:

- It's a **personal-scale tool**, not a product. One user, one playlist, one phone.
- It leans on **unofficial interfaces** (see [the note below](#a-note-on-unofficial-clients-and-apis)),
  so things can break when Shazam, YouTube Music, or your patched client updates.
- It's been tested on a sample size of *one phone and one music library*. Your
  regional catalogue, your artist-name formatting, and your client's deep-link
  handling may differ.

If it breaks for you, that's genuinely useful information —
**[open an issue](../../issues/new/choose)**, especially the "client
compatibility" one. Every report makes the next person's setup smoother.

## Requirements

| | |
|---|---|
| **Phone** | Android 8.0+ (API 26), with Shazam and a YouTube Music client installed |
| **A Google account** | The playlist gets created under it; the backend acts as you |
| **Somewhere to host the backend** | Free Render / Fly.io / a Raspberry Pi / anything that runs Docker |
| **To build the app** | Android Studio, or just a JDK 17 + the Android SDK for command-line builds |

You do **not** need a Google Cloud project, a billing account, or a credit card.

## Quick start

Three stages, in order — each one produces a value the next one needs.
Full detail lives in **[docs/setup.md](docs/setup.md)**; this is the shape of it.

### 1. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Auth as your own account (opens a prompt — paste browser request headers)
ytmusicapi browser

cp .env.example .env      # then fill in the three values
set -a && source .env && set +a
uvicorn app.main:app --reload
```

Confirm it works before you go near Android:

```bash
curl -X POST localhost:8000/search \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"title": "295", "artists": ["Sidhu Moose Wala"]}'
```

Then deploy it — [docs/setup.md](docs/setup.md#3-deploy-the-backend) covers Render
(free, no card), Fly.io, Docker anywhere, and Cloud Run.

### 2. Android app

```bash
cd android
cp app/secrets.properties.example app/secrets.properties
# fill in: targetPackageName, backendUrl, backendApiKey

./gradlew installDebug          # phone connected, USB debugging on
```

> **Android Studio will say "Error running 'app' — Default Activity not found"
> after installing. That is expected and not a bug.** The app deliberately has no
> launcher activity. Its only entry point is the share sheet.

### 3. Use it

Shazam a song → **Share** → **Shazam Sync**. It plays, and it's in the playlist.

To replay your listening history, see **[backfill/](backfill/)**.

## How it works

Three pieces, deliberately kept small:

| Component | What it is | Why it's separate |
|---|---|---|
| **[`backend/`](backend/)** | FastAPI service wrapping [`ytmusicapi`](https://ytmusicapi.readthedocs.io/). Two endpoints: `POST /search`, `POST /add-to-playlist`. | It holds the Google session cookies, which must not ship inside an APK on your phone. It's also the single source of truth for matching, so the Android app and the backfill script can't drift apart. |
| **[`android/`](android/)** | A headless `ACTION_SEND` share-target activity. Parses Shazam's share text, calls the backend, fires an explicit `ACTION_VIEW` intent. | It's the only part that can hook into the share sheet. Kept as thin as possible — no matching logic lives here. |
| **[`backfill/`](backfill/)** | A local CLI that reads a CSV of past identifications and replays each row through the same two endpoints. | One-time job, no reason to live on a server. Reuses the backend so history and live shares match identically. |

A few decisions worth knowing about, since they're the non-obvious ones:

- **`ytmusicapi` (browser cookies), not the YouTube Data API.** The Data API's
  quota doesn't survive a backfill — ~200 songs costs roughly 30,000 units against
  a 10,000/day default — and unverified personal OAuth apps hit refresh-token
  expiry. Cookie auth has its own downside (it expires; see
  [troubleshooting](docs/troubleshooting.md)) but it actually works at this scale.
- **Two endpoints, not one.** The app fires the play intent the instant `/search`
  returns, without waiting on the playlist write. Playback feels instant.
- **An explicit `setPackage()` intent**, so the track goes to *your* chosen client
  and never opens an app-chooser dialog.
- **No `resolveActivity()` pre-check.** Android's package-visibility rules (API
  30+) make it return a false negative for undeclared packages, which produces a
  bogus "target app not installed" error even when the intent works perfectly.
  See [docs/architecture.md](docs/architecture.md) for the full story — it cost a
  debugging session and is a nice trap to know about.

More in **[docs/architecture.md](docs/architecture.md)**.

## When it breaks

**[docs/troubleshooting.md](docs/troubleshooting.md)** is organised by symptom —
nothing happens on share, the wrong song plays, songs stop reaching the playlist,
the app says the target isn't installed. Start there.

The single most likely failure over time: **your `ytmusicapi` cookies expire.**
Songs keep playing, but they quietly stop landing in the playlist. Re-run
`ytmusicapi browser` and update the env var.

## Want to make it better?

Genuinely, please do. This is a small enough codebase to read in one sitting
(~400 lines across three languages), and there's a lot of obvious headroom.
**[docs/roadmap.md](docs/roadmap.md)** lists concrete ideas grouped by effort —
from half-hour wins to real features:

- 🟢 **Good first issues** — a proper notification instead of a toast, a
  `--limit` flag on the backfill, iOS Shortcuts equivalent, better artist
  normalisation for non-Latin scripts.
- 🟡 **Meaty** — an offline queue so shares survive a dead backend, per-genre
  playlist routing, a Spotify/Apple Music target alongside YouTube Music.
- 🔴 **Ambitious** — OAuth instead of scraped cookies, a disambiguation
  notification when the match is low-confidence, a self-hosted all-in-one build.

The most valuable contribution isn't code, though: it's **telling us which
YouTube Music client and which phone worked for you**. There's
[an issue template](../../issues/new/choose) for exactly that, and the results
go straight into the compatibility table in [docs/setup.md](docs/setup.md).

See **[CONTRIBUTING.md](CONTRIBUTING.md)** — it covers running the tests
(`pytest` + `./gradlew test`, all of which run in CI) and the project's one
firm rule: matching logic stays in the backend.

## A note on unofficial clients and APIs

Being upfront, because you're about to point this at your own Google account:

- `ytmusicapi` authenticates using **request headers copied from your logged-in
  browser session**. It is an unofficial library; YouTube Music has no public API
  for playlist writes. Those headers are as sensitive as your password — they go
  in an environment variable, never in the repo. `.gitignore` covers `.env` and
  `secrets.properties`, but the responsibility is yours.
- Modified clients like Morphe and ReVanced are not affiliated with this project
  and are not distributed by it. This app just sends them a standard
  `music.youtube.com` deep link — it works the same with the official app.
- Automating a service in ways its terms of service don't anticipate carries some
  risk to your account. This is a personal-scale tool making a handful of requests
  a day; judge that for yourself.

Not affiliated with Apple, Shazam, Google, or YouTube.

## License

[MIT](LICENSE) — do what you like with it. If you build something better on top,
I'd love to hear about it.
