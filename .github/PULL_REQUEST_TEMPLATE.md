<!--
Thanks for contributing! Keep this short — a couple of sentences per section
is plenty. Delete anything that doesn't apply.
-->

## What and why

<!-- What was broken or missing? What does this change? Link an issue if there is one. -->

## How I tested it

<!--
Say what you actually ran. Automated tests alone are fine for backend/parser
changes; anything touching the intent or the share flow really wants a real
device check.
-->

- [ ] `pytest` passes (`backend/`)
- [ ] `./gradlew test` passes (`android/`)
- [ ] Tested end-to-end on a real phone
  - Client / phone:

## Checklist

- [ ] No secrets in the diff — API keys, cookies, `.env`, `secrets.properties`
      (`git diff --staged` is worth one last look)
- [ ] Matching logic stayed in the backend, not the Android app
- [ ] Added or updated a test, if this touches parsing or matching
- [ ] Updated the docs, if this changes setup or behaviour

<!--
Heads up: if you touched playTrack(), please read
docs/architecture.md#the-resolveactivity-trap — there's a package-visibility
trap there that looks like a missing safety check but is a bug if you add it.
-->
