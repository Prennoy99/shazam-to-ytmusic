# Android app

A headless share-target app. It has **no launcher icon and no UI** — its only
entry point is the Android share sheet.

> First-time setup lives in
> **[docs/setup.md](../docs/setup.md#stage-4--build-the-android-app)**. This page
> is for working on the code.

## What it does

1. Receives an `ACTION_SEND` / `text/plain` intent from Shazam.
2. Parses `"<title> by <artists> <url>"` into a title and artist list.
3. `POST /search` on your backend.
4. Fires an explicit `ACTION_VIEW` intent at your configured YouTube Music
   client — playback starts here, immediately.
5. Fires `POST /add-to-playlist` fire-and-forget, and finishes.

The activity is transparent, `noHistory`, and `excludeFromRecents`, so it never
appears as a screen or in your recents list.

## Configuration

`app/secrets.properties` (gitignored) becomes `BuildConfig` fields at build time:

| Key | Value |
|---|---|
| `targetPackageName` | Package of the client that should play the track |
| `backendUrl` | Your deployed backend, no trailing slash |
| `backendApiKey` | Must match the backend's `API_KEY` exactly |

```bash
cp app/secrets.properties.example app/secrets.properties
```

Missing keys build with an `UNSET` placeholder and the app says it isn't
configured, rather than failing in a confusing way. That's what lets CI and a
fresh clone build with no setup — but it means **a build that "works" isn't
necessarily configured.**

> Config is compiled in at build time. Editing `secrets.properties` does nothing
> until you rebuild.

## Building

```bash
./gradlew test           # unit tests — no device, no config needed
./gradlew assembleDebug  # APK at app/build/outputs/apk/debug/
./gradlew installDebug   # install to a connected device
```

Needs JDK 17 and the Android SDK. Android Studio works too — just note the
"Default Activity not found" message after install is **expected**, because there
is no launcher activity by design.

Low on RAM? `gradle.properties` is already tuned conservatively (1536m heap,
daemon off, no parallelism); see
[the setup guide](../docs/setup.md#4c-build-and-install).

## Code map

| File | What it does |
|---|---|
| [`ShareReceiverActivity.kt`](app/src/main/java/com/shazamsync/app/ShareReceiverActivity.kt) | Entry point, orchestration, the play intent |
| [`ShazamShareParser.kt`](app/src/main/java/com/shazamsync/app/ShazamShareParser.kt) | Regex parse of Shazam's share text |
| [`BackendApi.kt`](app/src/main/java/com/shazamsync/app/BackendApi.kt) | OkHttp calls to the two endpoints |

## Two things not to "fix"

Both look like mistakes and are load-bearing. Full explanations in
[docs/architecture.md](../docs/architecture.md).

**1. `playTrack()` has no `resolveActivity()` check.**
Adding one reintroduces a bug: Android 11+ package-visibility rules make
`resolveActivity()` return `null` for an installed, working app, producing a
false "target app not installed" error. Starting an explicit intent doesn't need
visibility — only *querying* does. The `try`/`catch` is the correct guard.

**2. The OkHttp timeouts are 60s, not the 10s default.**
Free-tier hosts sleep and take 30–50s to cold-start. Lower them and the first
share of the day reports "not found".

Also: the theme's parent must stay a real `Theme.AppCompat.*` style, since
`ShareReceiverActivity` extends `AppCompatActivity`. Note that
`Theme.AppCompat.Translucent.NoTitleBar` does not exist — that name is from the
old platform themes and fails at resource-linking time.
