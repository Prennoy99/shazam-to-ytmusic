"""Endpoint behaviour, including the API-key gate that is the only thing
standing between a public URL and someone else's playlist."""
import pytest
from fastapi.testclient import TestClient

from app import main

KEY = {"X-API-Key": "test-api-key"}


@pytest.fixture
def client():
    return TestClient(main.app)


def test_health_needs_no_key(client):
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/search", "/add-to-playlist"])
def test_endpoints_reject_a_missing_key(client, path):
    assert client.post(path, json={}).status_code == 422


@pytest.mark.parametrize("path", ["/search", "/add-to-playlist"])
def test_endpoints_reject_a_wrong_key(client, path):
    resp = client.post(path, json={}, headers={"X-API-Key": "nope"})
    assert resp.status_code == 401


def test_search_reports_a_match(client, monkeypatch):
    monkeypatch.setattr(
        main,
        "find_best_match",
        lambda title, artists: {
            "videoId": "abc123",
            "title": "295",
            "artists": [{"name": "Sidhu Moose Wala"}],
        },
    )
    resp = client.post("/search", json={"title": "295", "artists": []}, headers=KEY)
    assert resp.json() == {
        "found": True,
        "video_id": "abc123",
        "matched_title": "295",
        "matched_artists": ["Sidhu Moose Wala"],
    }


def test_search_reports_a_miss(client, monkeypatch):
    monkeypatch.setattr(main, "find_best_match", lambda title, artists: None)
    resp = client.post("/search", json={"title": "???", "artists": []}, headers=KEY)
    assert resp.json()["found"] is False
    assert resp.json()["video_id"] is None


def test_add_to_playlist_reports_added(client, monkeypatch):
    monkeypatch.setattr(main, "add_to_playlist", lambda playlist, video: True)
    resp = client.post("/add-to-playlist", json={"video_id": "abc"}, headers=KEY)
    assert resp.json() == {"added": True}


def test_add_to_playlist_reports_a_duplicate_as_not_added(client, monkeypatch):
    monkeypatch.setattr(main, "add_to_playlist", lambda playlist, video: False)
    resp = client.post("/add-to-playlist", json={"video_id": "abc"}, headers=KEY)
    assert resp.json() == {"added": False}
