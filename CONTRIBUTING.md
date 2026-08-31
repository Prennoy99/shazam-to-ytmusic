# Contributing

Contributions are genuinely welcome — this is a small personal project that
turned out to be useful, and it gets better the more setups it's been tested
against.

**You do not need to write code to help.** Jump to
[Reporting things](#reporting-things) if that's you; those reports are the most
useful contributions this project receives.

## Ways to help, roughly by value

1. **Tell us your client + phone worked** (or didn't). The compatibility table in
   [docs/setup.md](docs/setup.md#4a-find-your-clients-package-name) is built
   entirely from reports.
2. **Report a Shazam share-format change.** This breaks the pipeline for everyone
   at once and is invisible until reported. Include the raw share text.
3. **Report a song that matched wrong**, with what Shazam reported. These become
   test cases.
4. **Tell us where the setup guide confused you.** It was written by the person
   who already knew the answers.
5. **Code.** [docs/roadmap.md](docs/roadmap.md) has concrete ideas grouped by
   effort, all unclaimed.

## Before you start on something big

For anything in the 🟡 or 🔴 tiers of the roadmap, **open an issue first** and
sketch the approach. Not a formality — some of those touch design decisions with
non-obvious reasons behind them, and a five-minute conversation beats a rejected
weekend. Small fixes need no ceremony; just send the PR.

## Getting set up

You'll need a working deployment to test against end-to-end — follow
[docs/setup.md](docs/setup.md). But **most changes don't need one**: the tests
stub out both the network and YouTube Music entirely.

### Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

No credentials needed — `tests/conftest.py` sets placeholder environment
variables and `ytmusicapi` is stubbed.

Lint with `ruff check .` (also enforced in CI).

### Android

```bash
cd android
./gradlew test          # unit tests, no device or emulator needed
./gradlew assembleDebug # full build
```

Unit tests need no `secrets.properties` — missing values fall back to a
placeholder. You only need real values to install on a phone.

On a low-RAM machine, see the
[note in the setup guide](docs/setup.md#4c-build-and-install).

### Backfill

```bash
cd backfill
pip install -r requirements.txt pytest
pytest
```

## Project conventions

Only a few, but they matter:

- **Matching logic lives in the backend. Always.** The Android app and the
  backfill script both call the same two endpoints specifically so they can never
  disagree about what a song resolves to. A "quick fix" in `ShareReceiverActivity`
  breaks that and will be asked to move.
- **Keep the Android app thin.** Parse, call, launch, exit. No caching, no state,
  no business logic.
- **Never commit secrets.** `.env`, `secrets.properties`, and `browser.json` all
  carry live credentials. All three are gitignored, but that's a safety net, not
  a guarantee — check `git diff --staged` before committing.
- **Read [docs/architecture.md](docs/architecture.md) before changing
  `playTrack()`.** There's a package-visibility trap there that looks like a
  missing safety check and is actually a bug if you "fix" it.
- **Add a test when you change parsing or matching.** Both have fast, dependency-
  free test suites — `ShazamShareParserTest.kt` and `backend/tests/`. A real
  share string or a real bad match is worth more than a synthetic case.

## Pull requests

- Branch off `main`.
- Keep it focused — one change per PR. Unrelated refactors make review slow.
- Make sure `pytest` and `./gradlew test` pass; CI runs both.
- Describe **what broke or what was missing**, not just what you changed. If it's
  a compatibility fix, say which client and phone.
- Comment the *why*, not the *what*, when something looks unusual. The existing
  code does this and it's the reason the package-visibility trap is documented
  instead of being silently reintroduced every six months.

## Code of conduct

Be decent to each other. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Licensing

Contributions are accepted under the [MIT License](LICENSE).
