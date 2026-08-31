# Security

## Reporting a vulnerability

Please **don't** open a public issue for a security problem.

Use GitHub's private reporting: the **Security** tab → *Report a vulnerability*.
That opens a private channel with the maintainers.

This is a small personal project maintained in spare time — expect a reply within
a week or so, not within hours.

## What you're trusting when you run this

Worth understanding before you deploy it, because the threat model is unusual.

### Your backend holds live Google session credentials

`YTMUSIC_AUTH_JSON` contains request headers copied from a logged-in
`music.youtube.com` browser session — including session cookies. Anyone who
obtains that value can act as your Google account against YouTube Music.

Consequences:

- **Never commit it.** `backend/.gitignore` covers `.env`, but the responsibility
  is yours. Check `git diff --staged` before committing.
- **Delete `browser.json` after use.** `ytmusicapi browser` writes it to disk in
  the backend directory. It's gitignored as a safety net, but the safe state is
  for it not to exist at all.
- **Use your host's secret storage**, not a committed file.
- If you think it leaked: sign out of all Google sessions (which invalidates the
  cookies), then re-run `ytmusicapi browser` for a fresh set.

### Your backend is publicly reachable

By design — your phone has to reach it. The `X-API-Key` header is the only thing
protecting it.

- **Generate a real key**: `openssl rand -hex 32`. Never ship the `changeme`
  placeholder.
- **Use HTTPS.** The key travels in a header on every request; over plain HTTP
  it's readable by anything on the path. Managed platforms give you TLS by
  default. Self-hosting, put it behind a reverse proxy or a tunnel.
- The worst case if the key leaks is bounded — an attacker can search YouTube
  Music and append tracks to one playlist as you. Rotate the key (update it in
  both the backend env *and* `secrets.properties`, then rebuild the app).

### The API key is embedded in your APK

`backendApiKey` is compiled into `BuildConfig` at build time, so it is extractable
from the installed APK by anyone with access to the device or the file.

This is an accepted trade-off for a personal-scale tool: the key's blast radius is
one playlist. **Don't distribute a built APK** containing your key, and don't
reuse that key for anything else.

### Known limitations

Deliberate, given the scale this is built for:

- **No rate limiting.** Someone with the key could hammer the endpoints.
- **No key rotation mechanism.** Rotating means updating the env var and
  rebuilding the app.
- **Constant-time comparison isn't used** for the API key check. Timing attacks
  against a 256-bit random key over the internet aren't a practical concern here,
  but a PR switching to `hmac.compare_digest` would be welcome.
- **No audit log** of what was added, beyond the playlist itself.

If you're extending this beyond single-user use, all four need revisiting.

## Third-party components

- [`ytmusicapi`](https://github.com/sigma67/ytmusicapi) — unofficial YouTube Music
  library. No public API exists for playlist writes; this is the practical
  alternative, with the caveats above.
- Patched clients (Morphe, ReVanced) are **not** distributed by or affiliated with
  this project. It only sends them a standard `music.youtube.com` deep link, and
  works identically with the official app.

Automating a service in ways its terms don't anticipate carries some account risk.
This makes a handful of requests a day; judge that for yourself.
