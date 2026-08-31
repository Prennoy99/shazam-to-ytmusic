"""Matching is the only real logic in the backend, and it's the part most
worth protecting: it decides whether you get the studio track, a cover, or a
20-minute "extended mix"."""
import pytest

from app import matching


def song(title: str, *artists: str, video_id: str = "vid") -> dict:
    return {
        "title": title,
        "videoId": video_id,
        "artists": [{"name": a} for a in artists],
    }


@pytest.fixture
def results(monkeypatch):
    """Stub ytmusicapi so tests never touch the network or need credentials."""
    holder: list[list[dict]] = [[]]

    class FakeClient:
        def search(self, query, filter=None):
            return holder[0]

    monkeypatch.setattr(matching, "get_client", lambda: FakeClient())
    return holder


def test_returns_none_when_search_is_empty(results):
    results[0] = []
    assert matching.find_best_match("Nothing", ["Nobody"]) is None


def test_keeps_top_hit_when_no_artists_given(results):
    results[0] = [song("A", "X"), song("B", "Y")]
    assert matching.find_best_match("A", [])["title"] == "A"


def test_prefers_the_result_whose_artist_matches(results):
    """The whole point of the tiebreaker: a cover can outrank the original on
    raw relevance, so the artist name breaks the tie."""
    results[0] = [
        song("295", "Some Cover Band", video_id="cover"),
        song("295", "Sidhu Moose Wala", video_id="real"),
    ]
    match = matching.find_best_match("295", ["Sidhu Moose Wala"])
    assert match["videoId"] == "real"


def test_keeps_the_top_hit_when_nothing_matches_the_artist(results):
    results[0] = [song("A", "X", video_id="first"), song("B", "Y", video_id="second")]
    match = matching.find_best_match("A", ["Totally Different Artist"])
    assert match["videoId"] == "first"


def test_artist_comparison_ignores_case_and_padding(results):
    results[0] = [
        song("Song", "Nobody", video_id="wrong"),
        song("Song", "  SIDHU moose wala ", video_id="right"),
    ]
    match = matching.find_best_match("Song", ["Sidhu Moose Wala"])
    assert match["videoId"] == "right"


def test_tolerates_results_with_no_artist_field(results):
    results[0] = [{"title": "Song", "videoId": "bare"}]
    assert matching.find_best_match("Song", ["Someone"])["videoId"] == "bare"
