# Setup guide

End to end this takes about **45 minutes**, most of it waiting on Gradle and a
first deploy. Do the stages in order — each produces a value the next one needs.

By the end you'll have three secrets you keep track of:

| Value | Made in | Used by |
|---|---|---|
| `PLAYLIST_ID` | Stage 1 | backend |
| `YTMUSIC_AUTH_JSON` | Stage 2 | backend |
| `API_KEY` | Stage 2 | backend **and** the Android app |
| backend URL | Stage 3 | Android app, backfill script |

---

## Stage 1 — Create the playlist

1. Open [music.youtube.com](https://music.youtube.com) and sign in.
2. Create a new playlist. Name it whatever you like — `shazam_finds` is the
   convention here.
3. Set its privacy to **Private**. (Public works too; the API doesn't care.)
4. Open the playlist and copy the ID out of the address bar:

   ```
   music.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxx
                                   └──── this part ────┘
   ```

That string is your `PLAYLIST_ID`.

> **Don't be alarmed if yours is short.** Auto-generated playlist IDs are usually
> ~30 characters, but hand-created ones can be much shorter (mine is 14). Trust
> the address bar over any expectation about length.

The playlist is created **once, by hand, on purpose.** The backend never creates
or looks up playlists — one less thing to go wrong, and no chance of it
scattering half-empty playlists across your account.

---

## Stage 2 — Backend credentials

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2a. Authenticate with YouTube Music

`ytmusicapi` acts as *you*, using headers lifted from a logged-in browser
session. There's no OAuth app to register.

```bash
ytmusicapi browser
```

It will wait for you to paste something. Here's what to paste:

1. Open [music.youtube.com](https://music.youtube.com) in a browser where you're
   **signed in**.
2. Open DevTools (<kbd>F12</kbd>) → the **Network** tab.
3. Reload the page.
4. Click any request whose domain is `music.youtube.com`. A `POST` request is the
   most reliable choice — some `GET` requests don't carry the full cookie set.
5. Find the **Request Headers** block. In Firefox, right-click the request →
   *Copy* → *Copy Request Headers*. In Chrome, select the raw headers text and
   copy it.
6. Paste into the terminal, then send EOF: <kbd>Ctrl</kbd>+<kbd>D</kbd>
   (<kbd>Ctrl</kbd>+<kbd>Z</kbd> then <kbd>Enter</kbd> on Windows).

This writes `browser.json`. Collapse it to a single line:

```bash
python3 -c "import json; print(json.dumps(json.load(open('browser.json'))))"
```

That one-line string is your `YTMUSIC_AUTH_JSON`.

> [!IMPORTANT]
> **`browser.json` contains live session cookies for your Google account.**
> Once you've copied the value into `.env` (and into your host's environment
> settings), delete the file:
> ```bash
> rm browser.json
> ```
> It *is* gitignored as a safety net, but delete it anyway — the safest state is
> for it not to exist. Treat that string like a password.

### 2b. Generate the API key

This is the shared secret between your phone and your backend. Without it,
anyone who finds your URL can write to your playlist.

```bash
openssl rand -hex 32
```

Save it as `API_KEY`.

### 2c. Fill in `.env` and test locally

```bash
cp .env.example .env
```

Fill in all three values. **Single-quote `YTMUSIC_AUTH_JSON`** — it contains
spaces and commas that will otherwise break shell parsing.

```bash
set -a && source .env && set +a     # not `export $(cat .env | xargs)` — it mangles the JSON
uvicorn app.main:app --reload
```

In another terminal, prove it can find a real song:

```bash
curl -X POST localhost:8000/search \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"title": "295", "artists": ["Sidhu Moose Wala"]}'
```

Expect `"found": true` and a `video_id`. Then prove it can write:

```bash
curl -X POST localhost:8000/add-to-playlist \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"video_id": "<the video_id from above>"}'
```

Expect `{"added": true}`. **Run it a second time** — you should get
`{"added": false}`, which is the duplicate check doing its job. Check the
playlist in your browser; the song should be sitting there exactly once.

If you get an auth error here, redo 2a — a header copy that missed a line is by
far the most common cause.

---

## Stage 3 — Deploy the backend

Any host that runs a Docker container works. The `Dockerfile` reads `$PORT`, so
it fits the usual platform conventions.

Whichever you pick, set the same three environment variables — `API_KEY`,
`PLAYLIST_ID`, `YTMUSIC_AUTH_JSON` — using the **raw, unquoted** values (the
single quotes in `.env` are shell syntax, not part of the value).

### Render (free, no credit card)

This is what the project was built against.

1. Push your fork to GitHub.
2. Render dashboard → **New** → **Web Service** → connect the repo.
3. Configure:
   - **Language**: Docker
   - **Root Directory**: `backend`
   - **Dockerfile Path**: `backend/Dockerfile` — set this explicitly; the
     auto-filled `backend/` alone is ambiguous and the build fails
   - **Health Check Path**: `/health`
   - **Instance Type**: Free
4. Add the three environment variables.
5. Deploy, and verify from outside:
   `curl https://<your-service>.onrender.com/health` → `{"status":"ok"}`

> [!NOTE]
> **Render's free tier sleeps after ~15 minutes idle** and takes 30–50s to wake.
> Your first Shazam of the day will be slow. The Android client uses 60s timeouts
> specifically to ride this out — don't lower them.

### Fly.io

Free allowance, needs a card on file for verification.

```bash
cd backend
fly launch --no-deploy
fly secrets set API_KEY=... PLAYLIST_ID=... YTMUSIC_AUTH_JSON='...'
fly deploy
```

### Docker anywhere (VPS, Raspberry Pi, home server)

```bash
cd backend
docker build -t shazam-to-ytmusic .
docker run -d --restart unless-stopped -p 8080:8080 \
  -e API_KEY=... -e PLAYLIST_ID=... -e YTMUSIC_AUTH_JSON='...' \
  shazam-to-ytmusic
```

Put it behind HTTPS — the API key travels in a header on every request. A
Cloudflare Tunnel is a card-free way to expose it.

> **Self-hosting trade-off:** if the machine is off when you Shazam something, the
> request fails immediately and there's no retry or queue. You'd have to
> re-share the song from Shazam's history later. A sleepy free tier that's always
> *eventually* reachable beats a fast box that's sometimes off. (Building a
> proper offline queue is [on the roadmap](roadmap.md) and would fix this.)

### Google Cloud Run

Works, but note it requires an **active billing account** to enable the Run and
Build APIs at all — even entirely within the free tier. If "no card anywhere" is
a requirement for you, use Render.

```bash
gcloud run deploy shazam-to-ytmusic --source backend --region <region> \
  --allow-unauthenticated \
  --set-env-vars "API_KEY=...,PLAYLIST_ID=..." \
  --set-env-vars "YTMUSIC_AUTH_JSON=..."
```

`--allow-unauthenticated` is correct here: the `X-API-Key` header is the real
gate, not Cloud Run's IAM layer.

---

## Stage 4 — Build the Android app

### 4a. Find your client's package name

With the phone connected and USB debugging on:

```bash
adb shell pm list packages | grep -i music
```

Look for the YouTube Music client you actually use.

| Client | Package name |
|---|---|
| Morphe | `app.morphe.android.apps.youtube.music` |
| ReVanced | `app.revanced.android.apps.youtube.music` (varies by patch config) |
| Official YouTube Music | `com.google.android.apps.youtube.music` |

*Used a different client, or a different package? Please
[tell us](../../issues/new/choose) — this table grows from reports.*

### 4b. Configure

```bash
cd android
cp app/secrets.properties.example app/secrets.properties
```

Fill in `targetPackageName`, `backendUrl` (no trailing slash), and
`backendApiKey` — which must match the backend's `API_KEY` **exactly**. A
mismatch here shows up as every song "not being found", which is a confusing way
to discover a typo.

`secrets.properties` is gitignored. Values left blank build a working APK that
tells you it's unconfigured rather than failing cryptically.

### 4c. Build and install

Command line (no Android Studio needed if you have the SDK and JDK 17):

```bash
./gradlew installDebug
```

Or open `android/` in Android Studio and hit Run.

> **"Error running 'app' — Default Activity not found" is expected.** The app has
> no launcher icon by design; its only entry point is the share sheet. The install
> itself succeeded. Ignore this.

<details>
<summary><strong>Building on a low-RAM machine (under 8GB)</strong></summary>

A default Gradle + Android Studio build can exhaust memory and hard-crash the
whole system. `android/gradle.properties` is already tuned conservatively:
heap capped at 1536m, daemon off, no parallel execution, max 2 workers, Kotlin
daemon capped at 768m.

If you're still crashing, grow your swap:

```bash
sudo swapoff /swapfile
sudo fallocate -l 8G /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

(Fine on an SSD. No `/etc/fstab` change needed — it references the path, not the
size.) If you have plenty of RAM, feel free to raise those limits back up.
</details>

### 4d. Optional — default link handler

Android Settings → Apps → *[your YouTube Music client]* → **Open by default** →
**Open supported links** → enable for `music.youtube.com`.

This is a **fallback**, not a requirement — the app targets your client's package
explicitly via `setPackage()`, so the intent should land correctly regardless.

---

## Stage 5 — Test it

Shazam a song → **Share** → **Shazam Sync**.

Expected: a brief toast, the full track playing in your client, and the song
appearing in your playlist within a second or two.

If the first attempt is slow, that's the free-tier cold start. If something else
happens, **[docs/troubleshooting.md](troubleshooting.md)** is organised by exactly
what you're seeing.

---

## Stage 6 — Backfill your history (optional)

Replay everything you've ever Shazam'd into the same playlist.

### Getting your history as a CSV

Shazam's own export wasn't available from the app or website on my account, so the
route is an Apple data request:

1. Go to [privacy.apple.com](https://privacy.apple.com) → *Request a copy of your
   data* → select the Shazam data.
2. Wait. This can take **hours to several days**.
3. Unzip and find the CSV of identifications.

*If you find a faster export path that works, please open an issue — that would
help everyone.*

### Running it

Column names vary between export formats, so **always dry-run first**:

```bash
cd backfill
pip install -r requirements.txt

python3 backfill.py --csv <export.csv> \
  --backend-url https://<your-service> --api-key <key> \
  --dry-run
```

That prints the first 20 parsed rows. If titles and artists look wrong, point it
at the right columns with `--title-column` / `--artist-column` and dry-run again.

When the parse looks right, drop `--dry-run`:

```bash
python3 backfill.py --csv <export.csv> \
  --backend-url https://<your-service> --api-key <key> \
  --title-column <col> --artist-column <col>
```

It writes `backfill_results.csv` with a per-row status. Afterwards, filter that
for `not_found` and `error` rows and handle those by hand — a handful of misses
across a few hundred songs is normal, usually regional catalogue gaps or unusual
artist formatting.

> On a free tier, the first request wakes the instance (30–50s) and the rest are
> fast. `--delay` (default 0.5s) throttles between rows; raise it if you'd rather
> be gentle with the API.
