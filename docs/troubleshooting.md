# Troubleshooting

Organised by **what you're actually seeing**. Find your symptom and work down.

If none of this matches, [open an issue](../../issues/new/choose) — include your
phone, Android version, YouTube Music client, and where the pipeline stops.

---

## First: which half is broken?

Almost every problem is either "the backend can't be reached / can't find the
song" or "the phone can't hand the song to your music app". One command tells
you which:

```bash
curl https://<your-service>/health
```

- **`{"status":"ok"}`** → the backend is alive. Skip to the Android sections.
- **Hangs 30–50s, then responds** → normal free-tier cold start, not a bug.
- **Fails or times out entirely** → backend problem. Start below.

---

## Sharing does nothing, or "Couldn't find '<title>' — not added"

This toast means the backend was asked and didn't return a match. Three causes,
in order of likelihood:

### 1. The API key doesn't match

By far the most common cause, and it's disguised: a wrong key returns HTTP 401,
which the app reports as "not found". Verify directly:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://<your-service>/search \
  -H "X-API-Key: <the key from android/app/secrets.properties>" \
  -H "Content-Type: application/json" \
  -d '{"title":"295","artists":["Sidhu Moose Wala"]}'
```

`401` → the key in `secrets.properties` doesn't match the backend's `API_KEY`.
Fix it and **rebuild the app** — it's compiled in at build time, so editing the
file alone changes nothing.

`200` → the key is fine, move on.

### 2. The backend is down or asleep

Check `/health` as above, then your host's logs. On Render: dashboard → your
service → **Logs**. A crash on startup usually means a missing or malformed
environment variable.

### 3. Shazam changed its share text format

The parser expects `"<title> by <artist1, artist2 & artist3> <url>"`. An update
to Shazam could change that and break parsing silently.

To see what's actually arriving:

```bash
adb logcat | grep -i shazamsync
```

…or temporarily add `toast(sharedText)` at the top of `onCreate` in
[`ShareReceiverActivity.kt`](../android/app/src/main/java/com/shazamsync/app/ShareReceiverActivity.kt)
and rebuild.

If the format has changed, **please open an issue with the raw share text** —
that fix helps every user at once. The regex lives in
[`ShazamShareParser.kt`](../android/app/src/main/java/com/shazamsync/app/ShazamShareParser.kt)
and has unit tests you can extend.

---

## "Couldn't parse shared text"

You shared something that isn't a Shazam identification — a plain link, a text
selection, a song shared from a different app. Share from Shazam's own result
screen.

If it *was* from Shazam, that's the format-change case above. Please report it.

---

## "Target app not installed: <package>"

The explicit intent found no such package on the device.

1. **Confirm the package name:**
   ```bash
   adb shell pm list packages | grep -i music
   ```
   Compare against `targetPackageName` in `android/app/secrets.properties`.
   Typos here are easy and produce exactly this error.

2. **If it differs**, update `secrets.properties` and rebuild
   (`./gradlew installDebug`). Package names essentially never change across
   updates — Android treats a renamed package as a different app entirely — but
   different patch configurations of ReVanced/Morphe can produce different names.

3. **If it matches exactly**, the client was genuinely uninstalled or is
   corrupted. Reinstall it.

> [!NOTE]
> If you're modifying this code: do **not** "fix" this by adding a
> `resolveActivity()` check before `startActivity()`. That reintroduces a
> false-negative bug — see [architecture.md](architecture.md#the-resolveactivity-trap).

---

## "Shazam Sync isn't configured"

You built without filling in `android/app/secrets.properties`. Copy
`app/secrets.properties.example` to `app/secrets.properties`, fill in all three
values, and rebuild.

---

## Your music app opens but doesn't play the song

The intent arrived, but the client didn't act on the deep link. This is the one
real risk from a Morphe/ReVanced update: deep-link handling comes from the
YouTube Music manifest the patches build on, and a future patch could change it.

**Isolate it — take this app out of the picture entirely:**

```bash
adb shell am start -a android.intent.action.VIEW \
  -d "https://music.youtube.com/watch?v=dQw4w9WgXcQ" \
  <your target package>
```

- **It plays** → the client is fine, the bug is in this app. Check that
  `playTrack()` in `ShareReceiverActivity.kt` hasn't regressed to a
  `resolveActivity()` pre-check.
- **It doesn't play** (opens to home/library, or errors) → the client's
  deep-link intent filter is the problem. Nothing this app can do. Options:
  roll back the client update, wait for a fixed patch, or point
  `targetPackageName` at a different client. **Please open an issue** noting the
  client and version — a compatibility warning saves the next person the same
  debugging.

---

## The wrong song plays — a cover, a live version, a remix

Matching takes `ytmusicapi`'s top `filter="songs"` result, then prefers any
result whose artist names overlap what Shazam reported. There's no
disambiguation UI by design.

Check what the backend actually resolves:

```bash
curl -X POST https://<your-service>/search \
  -H "X-API-Key: <key>" -H "Content-Type: application/json" \
  -d '{"title":"<title>","artists":["<artist>"]}'
```

The response includes `matched_title` and `matched_artists`, so you can see what
it picked and why.

Common causes:
- **Artist name formatting differs** between Shazam and YouTube Music — different
  transliteration, "&" vs "and", featured artists in the title. The overlap check
  is exact-match after lowercasing and trimming, so near-misses don't help.
- **Regional catalogue** genuinely lacks the original.

Improving this is [the most valuable open contribution](roadmap.md) — fuzzy
artist matching and better non-Latin-script normalisation would help a lot of
people. [`matching.py`](../backend/app/matching.py) is 26 lines and has tests.

---

## Songs play fine, but stop appearing in the playlist

Playback and playlist-add are separate calls — playback succeeding tells you
nothing about the write. **This is the most likely long-term failure.**

### Almost always: your cookies expired

`ytmusicapi` browser auth expires eventually — after enough time, a password
change, or signing out of the browser session you captured from.

The fix is to redo [setup Stage 2a](setup.md#2a-authenticate-with-youtube-music)
and update `YTMUSIC_AUTH_JSON` in **both** places:

1. Local `backend/.env` (for local testing)
2. Your host's environment settings (on Render, saving triggers a redeploy)

Confirm the write path works again:

```bash
curl -X POST https://<your-service>/add-to-playlist \
  -H "X-API-Key: <key>" -H "Content-Type: application/json" \
  -d '{"video_id":"dQw4w9WgXcQ"}'
```

### Less likely: the playlist is gone or its ID changed

Visit `music.youtube.com/playlist?list=<your PLAYLIST_ID>`. If it 404s, create a
new playlist and update `PLAYLIST_ID` in the same two places.

### Or: it's already there

`{"added": false}` isn't an error — it's the duplicate check. Re-sharing a song
you've already Shazam'd plays it again but won't double up the playlist.

---

## Backfill: "Columns [...] do not contain 'title' / 'artist'"

Your export uses different column headers. The error prints the actual headers it
found — pass the right ones:

```bash
python3 backfill.py --csv export.csv --backend-url ... --api-key ... \
  --title-column "Track Name" --artist-column "Artist Name" --dry-run
```

Always `--dry-run` until the parsed output looks right.

---

## Backfill: lots of `not_found` rows

A few misses per few hundred songs is expected. A *lot* means something
systematic:

- **Every row failed** → check the first entry in `backfill_results.csv`. If it
  says `error (search: 401)`, your `--api-key` is wrong.
- **Titles look mangled in `--dry-run`** → wrong column mapping, or the export
  packs artist into the title field.
- **Timeouts early on** → the free-tier instance was asleep. Hit `/health` first
  to wake it, then rerun. Already-added songs are skipped, so rerunning is safe.

The script is **idempotent** — the duplicate check means you can rerun it as
often as you like without polluting the playlist.

---

## After making any change

- **Backend** → redeploy (on Render with auto-deploy, just push to `main`).
- **Android** → rebuild *and* reinstall: `./gradlew installDebug`. Config values
  are compiled into `BuildConfig` at build time, so editing
  `secrets.properties` without rebuilding changes nothing.
