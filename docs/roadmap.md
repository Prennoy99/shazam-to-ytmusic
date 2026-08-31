# Ideas & roadmap

Everything here is **unclaimed and open**. Nothing is assigned, nothing is
secretly half-built. If something looks interesting, say so in an issue and go —
you won't be duplicating hidden work.

Each item says roughly what it touches and how big it is, because "good first
issue" labels never tell you the part you actually want to know.

---

## 🟢 Small — an evening, or less

Good entry points. Each is self-contained and touches one file.

### Replace toasts with a notification
`ShareReceiverActivity.kt`

Toasts vanish in ~2s and can't be reviewed. A notification could show the matched
title and artist, whether the playlist add succeeded, and tapping it could open
the playlist. This also fixes a real gap: right now a **failed playlist write is
completely silent** because the add call is fire-and-forget.

### Show what was actually matched
`ShareReceiverActivity.kt`, `BackendApi.kt`

`/search` already returns `matched_title` and `matched_artists`, and the app
throws them away. Showing "Playing: *295* — Sidhu Moose Wala" would let you spot
a wrong match instantly instead of noticing three songs later.

### `--limit` and `--start-at` for the backfill
`backfill/backfill.py`

Test on 10 rows before committing to 400. `--start-at` lets you resume after an
interruption without re-walking the whole file.

### Retry `not_found` rows from a results log
`backfill/backfill.py`

The script already writes `backfill_results.csv` with a per-row status. Add
`--retry-from <log>` to reprocess only the failures — useful when the first
misses were timeouts rather than genuine absences.

### Make the search query smarter about "feat."
`backend/app/matching.py`

Shazam often reports `"Song (feat. X)"` while YouTube Music lists it as `"Song"`
with X as a second artist. Stripping `feat.` / `ft.` / `featuring` from the title
and folding it into the artist list would improve a whole category of misses.

### Structured backend logging
`backend/app/main.py`

Log each search with query, chosen result, and how the tiebreaker decided.
Debugging a bad match currently means reproducing it by hand with `curl`.

### Docker Compose for local dev
new file

One `docker compose up` for the backend with `.env` wired in, so contributors can
run it without touching Python or a virtualenv.

---

## 🟡 Medium — a weekend

Real features. Each needs a bit of design thinking, so **open an issue to talk it
through first** — especially the queue.

### An offline queue so shares survive a dead backend ⭐
`android/` — needs WorkManager

**The most valuable thing on this list.** Right now, if the backend is down, your
laptop is off, or you're on a train with no signal, the share is simply lost. Your
only recovery is remembering to re-share from Shazam's history later.

Persist the parsed share to local storage and let `WorkManager` retry with backoff
until it succeeds. It would make self-hosting on a home server genuinely viable,
which is currently the main argument against it (see
[setup.md](setup.md#docker-anywhere-vps-raspberry-pi-home-server)). This is the
single change that would most improve the project.

### Fuzzy artist matching ⭐
`backend/app/matching.py`

The current overlap check is exact-match after lowercase and trim, so
"Sidhu Moose Wala" vs "Sidhu Moosewala" scores zero. Normalising punctuation and
whitespace, and using a similarity ratio with a sensible threshold, would fix a
lot of near-misses.

**Especially valuable for non-Latin scripts**, where transliteration differs
between Shazam and YouTube Music constantly. This project was built and tested
against a mostly Tamil/Punjabi library and still misses there — if that's your
music too, you're better placed to fix this than most.

`matching.py` is 26 lines with [tests already in place](../backend/tests/test_matching.py),
so it's a contained change with a fast feedback loop.

### iOS support via Shortcuts
`docs/`, maybe a small helper

The backend is platform-agnostic — it's just two HTTP endpoints. An iOS Shortcut
accepting a share from Shazam, POSTing to `/search`, and opening the resulting
`music.youtube.com` URL should be entirely doable **with no new server code**.
This would roughly double who can use the project. Someone with an iPhone and an
afternoon could do it.

### Route to different playlists by genre or time
`backend/`

One playlist for everything is simple but blunt. Optional rules — by genre from
YouTube Music metadata, or "everything I Shazam'd this month" — without giving up
the zero-interaction flow.

### Support other music services as the target
`backend/`, `android/`

Nothing about the pipeline is YouTube-Music-specific except the client module.
A Spotify or Apple Music target behind the same two endpoints is a clean
extension — the interesting design question is whether one share can fan out to
several services at once.

### A real test for the backfill CLI
`backfill/tests/`

`split_artists` is covered; the CSV walking and result-log writing aren't. A test
using a temp CSV and a stubbed HTTP session would catch column-handling
regressions.

---

## 🔴 Ambitious — a proper project

Worth doing, but think them through and discuss before starting.

### OAuth instead of scraped browser cookies
`backend/`

The biggest structural weakness: cookie auth expires and needs a manual DevTools
ritual to renew (see [troubleshooting](troubleshooting.md#almost-always-your-cookies-expired)).
Proper OAuth would be far more durable — but note the quota problem that pushed
the project to `ytmusicapi` in the first place
([architecture.md](architecture.md#ytmusicapi-not-the-youtube-data-api-v3)).
A hybrid — OAuth for playlist writes, `ytmusicapi` for search — might get both.

### Confidence scoring and a "did you mean?" notification
`backend/`, `android/`

Return a confidence score alongside the match. Play immediately when it's high
(preserving the one-tap flow), and when it's low, play anyway but post a
notification offering the runners-up. Fixes wrong matches **without** adding a
prompt to the common case, which is the design constraint that has ruled out a
disambiguation UI so far.

### Ship a prebuilt APK via GitHub Releases
`.github/workflows/`

Right now everyone must build from source, which rules out anyone without
Android Studio. The obstacle is real: config values are compiled into
`BuildConfig` at build time, so a generic APK needs a **runtime settings screen**
instead — which means giving the app a launcher activity it currently, and
deliberately, doesn't have. Needs signing-key management too. A meaningful shift
in what this project is, so worth discussing first.

### A single self-hosted bundle
new

Backend + a lightweight web UI + setup wizard in one container, so getting
started is `docker run` and a browser page rather than a six-stage manual setup.
The setup guide being as long as it is *is* the barrier to entry here.

---

## Non-goals

Not accepting these, so nobody wastes a weekend:

- **A launcher UI for browsing your finds.** YouTube Music already shows the
  playlist. Being invisible is the point.
- **Multi-user hosted service.** Per-user credential storage for scraped Google
  cookies is a security burden this project shouldn't take on. Self-host your own.
- **Bundling or distributing patched clients.** Not this project's business.
- **A disambiguation prompt on every share.** Kills the one-tap flow. The
  confidence-scored version above is the acceptable form of this idea.

---

## Just want to help without writing code?

All of these genuinely matter:

- **Report your client + phone**, working or not — there's an
  [issue template](../../issues/new/choose) for it, and results go into the
  compatibility table in [setup.md](setup.md#4a-find-your-clients-package-name).
- **Report Shazam share-format changes.** Include the raw share text. This is the
  failure that breaks the pipeline for *everyone* simultaneously, and it's
  invisible until someone reports it.
- **Tell us where the setup guide lost you.** It was written by the person who
  already knew the answers, which is the worst possible author for it.
- **Report songs that match wrong**, with the title and artist Shazam reported.
  Real failure cases are what make the matching improvements above testable.
