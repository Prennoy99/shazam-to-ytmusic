# Architecture

Small enough to read in one sitting: ~400 lines across Python and Kotlin. This
explains the shape of it and — more usefully — *why* a few odd-looking decisions
are the way they are, so you don't undo them.

## The flow

```
┌─────────────┐
│   Shazam    │  identifies a song
└──────┬──────┘
       │ Android share sheet, ACTION_SEND text/plain
       │ "295 by Sidhu Moose Wala https://shazam.com/track/…"
       ▼
┌────────────────────────────────────────────┐
│ ShareReceiverActivity   (transparent, no   │
│                          launcher icon)    │
│  1. ShazamShareParser.parse(text)          │
│     → title + [artists]                    │
└──────┬─────────────────────────────────────┘
       │ POST /search   { title, artists }     X-API-Key
       ▼
┌────────────────────────────────────────────┐
│ backend  (FastAPI + ytmusicapi)            │
│  matching.find_best_match()                │
│   · ytmusicapi search, filter="songs"      │
│   · artist-overlap tiebreaker              │
└──────┬─────────────────────────────────────┘
       │ { found: true, video_id: "…" }
       ▼
┌────────────────────────────────────────────┐
│ ShareReceiverActivity                      │
│  ┌──────────────────┐  ┌─────────────────┐ │
│  │ 2. play now      │  │ 3. fire-and-    │ │
│  │  ACTION_VIEW +   │  │    forget       │ │
│  │  setPackage()    │  │  POST /add-to-  │ │
│  │       ↓          │  │    playlist     │ │
│  │  Morphe/ReVanced │  │       ↓         │ │
│  │  plays the track │  │  dedupe, append │ │
│  └──────────────────┘  └─────────────────┘ │
│         activity finishes immediately      │
└────────────────────────────────────────────┘
```

The backfill script enters at the same `POST /search` step, replacing Shazam and
the phone with a CSV row.

## Why three pieces

**The backend exists to hold the cookies.** `ytmusicapi` authenticates with
request headers copied from a logged-in browser session — full Google session
credentials. Those cannot ship inside an APK sitting on a phone, where anyone
with the file can extract them. Putting the credentials on a server you control,
behind a shared secret, is the whole reason there's a server at all.

It has a second benefit: **the backend is the single source of truth for
matching.** The Android app and the backfill script call the same two endpoints,
so a matching improvement lands for both at once and they can never drift apart.

**The Android app is deliberately thin.** It parses, calls, launches, and exits.
No matching logic, no caching, no state. It only exists because the share sheet
is an Android-only integration point.

**The backfill is local** because it's a one-time job with no reason to live on
a server.

## Design decisions worth keeping

### Two endpoints, not one

`/search` and `/add-to-playlist` are separate so the app can fire the play intent
the *instant* the search resolves, without waiting on the playlist write. Merging
them into one `/identify` call would add a round trip before any audio starts —
which is exactly the latency the user notices.

The playlist write is fire-and-forget: `BackendApi.addToPlaylist()` ignores its
own response. If it fails, the song still played. (The trade-off: a silent
playlist failure. See the [roadmap](roadmap.md).)

### `ytmusicapi`, not the YouTube Data API v3

The Data API's quota doesn't survive this use case. A search costs 100 units and
a playlist insert 50, against a 10,000/day default — so a 200-song backfill is
roughly 30,000 units, three days of quota. Worse, personal OAuth apps that stay
unverified hit refresh-token expiry every few days.

Browser-cookie auth has a real cost — it expires and needs manual renewal — but
it works at this scale, today, with no quota application and no OAuth consent
screen.

### Shared-secret header auth

`X-API-Key`, checked in [`auth.py`](../backend/app/auth.py), rather than platform
IAM. It's the simplest thing adequate for a single-user tool, and it's
platform-portable — the same code runs on Render, Fly, or a Pi without rewriting
the auth layer. The service is intentionally publicly reachable; the header is
the gate.

### Explicit `setPackage()` targeting

The play intent names your client's package directly, so the track always lands
in the client you configured and Android never shows an app-chooser. This is why
`targetPackageName` is a build-time config value rather than a hardcode — swapping
clients is a one-line change and a rebuild.

### <a name="the-resolveactivity-trap"></a>The `resolveActivity()` trap

**This one cost a real debugging session and is the most likely thing for a
well-meaning contributor to "fix" back into a bug.**

The obvious way to write `playTrack()` is to check before you leap:

```kotlin
// DON'T DO THIS
if (playIntent.resolveActivity(packageManager) != null) {
    startActivity(playIntent)
} else {
    toast("Target app not installed")
}
```

That code reports "target app not installed" for an app that is **installed and
works perfectly**.

Since Android 11 (API 30), [package visibility](https://developer.android.com/training/package-visibility)
restrictions mean an app can't *see* other installed packages unless they're
declared in a `<queries>` manifest block. `resolveActivity()` therefore returns
`null` for a perfectly valid intent — a false negative. The proof it's a
visibility issue and not a broken deep link: the identical intent fired from adb
(which isn't subject to the restriction) plays the track immediately.

```bash
adb shell am start -a android.intent.action.VIEW \
  -d "https://music.youtube.com/watch?v=<id>" <package>
```

The fix is to **not ask**. *Querying* package information requires visibility;
*starting* an explicit-package intent does not. So
[`playTrack()`](../android/app/src/main/java/com/shazamsync/app/ShareReceiverActivity.kt)
calls `startActivity()` directly inside a `try`/`catch` for
`ActivityNotFoundException`. Same safety, no false negatives, and no `<queries>`
entry that would have to be kept in sync with a build-time config value anyway.

### 60-second HTTP timeouts

OkHttp defaults to 10s. A free-tier host that sleeps after ~15 minutes idle takes
30–50s to cold-start, so the default guarantees a spurious "not found" on the
first share of the day. [`BackendApi`](../android/app/src/main/java/com/shazamsync/app/BackendApi.kt)
sets 60s connect/read/write. **Don't lower these** unless you're self-hosting
something always-on.

### Matching, and where it falls short

[`matching.py`](../backend/app/matching.py) is 26 lines:

1. Search `"<title> <artists joined>"` with `filter="songs"` — this alone
   eliminates most lyric videos and uploads, since the Songs category is
   catalogue tracks.
2. If Shazam gave artists, prefer the result with the largest artist-name
   overlap. `max()` keeps the first element among ties, so the tiebreaker only
   overrides the top hit when a later result *genuinely* matches better.

The known weakness is that artist comparison is exact-match after lowercase and
trim. "Sidhu Moose Wala" vs "Sidhu Moosewala", or differing transliterations of
non-Latin names, score zero overlap and fall back to raw relevance. Fixing this
is [the highest-value open contribution](roadmap.md).

### The Transparent theme must be AppCompat-based

`ShareReceiverActivity` extends `AppCompatActivity`, which throws at runtime
unless its theme descends from a real `Theme.AppCompat.*` style. `themes.xml`
uses `Theme.AppCompat.NoActionBar` as the parent and gets translucency from its
own items (`windowIsTranslucent`, `windowBackground`).

Note that `Theme.AppCompat.Translucent.NoTitleBar` **does not exist** — that
naming pattern is from the old platform themes, not AppCompat. Using it fails at
resource-linking time with `failed linking references`. (It was in the first
version of this repo and broke the very first build.)

## File map

| File | Lines | Responsibility |
|---|---|---|
| [`backend/app/main.py`](../backend/app/main.py) | ~70 | The two endpoints + `/health`, request/response models |
| [`backend/app/matching.py`](../backend/app/matching.py) | ~26 | Search and the artist-overlap tiebreaker |
| [`backend/app/ytmusic_client.py`](../backend/app/ytmusic_client.py) | ~34 | `ytmusicapi` client, auth-from-env, playlist dedupe |
| [`backend/app/auth.py`](../backend/app/auth.py) | ~10 | `X-API-Key` header check |
| [`android/…/ShareReceiverActivity.kt`](../android/app/src/main/java/com/shazamsync/app/ShareReceiverActivity.kt) | ~75 | Share-intent entry point, orchestration, play intent |
| [`android/…/ShazamShareParser.kt`](../android/app/src/main/java/com/shazamsync/app/ShazamShareParser.kt) | ~30 | Regex parse of Shazam's share text |
| [`android/…/BackendApi.kt`](../android/app/src/main/java/com/shazamsync/app/BackendApi.kt) | ~72 | OkHttp calls to the two endpoints |
| [`backfill/backfill.py`](../backfill/backfill.py) | ~120 | CSV replay CLI with dry-run and result log |

## Deliberate non-goals

Things left out on purpose — worth knowing before you propose them:

- **No dynamic playlist creation.** The playlist is made once by hand and its ID
  is fixed config. Nothing can scatter half-empty playlists across your account.
- **No disambiguation UI.** The point is one tap. A "did you mean?" prompt
  defeats it. (A *low-confidence-only* notification is a different, better idea —
  it's on the roadmap.)
- **No retry queue.** A failed share fails silently and you re-share from Shazam's
  history. This is the biggest honest gap; see the roadmap.
- **No multi-user support.** One deployment, one Google account, one playlist.
  Multi-tenancy would mean per-user credential storage — a much bigger project.
