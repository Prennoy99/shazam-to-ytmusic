"""Test-wide setup.

`app.main` reads PLAYLIST_ID at import time and `app.auth` reads API_KEY per
request, so both have to exist before any app module is imported.
"""
import os

os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("PLAYLIST_ID", "PLtest")
os.environ.setdefault("YTMUSIC_AUTH_JSON", "{}")
