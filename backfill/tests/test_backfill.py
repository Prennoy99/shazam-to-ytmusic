import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backfill  # noqa: E402


def test_splits_on_commas_and_ampersands():
    assert backfill.split_artists("S.S. Thaman, D Dheeraj & Vivek") == [
        "S.S. Thaman",
        "D Dheeraj",
        "Vivek",
    ]


def test_single_artist_is_left_alone():
    assert backfill.split_artists("Sidhu Moose Wala") == ["Sidhu Moose Wala"]


def test_blank_input_yields_no_artists():
    assert backfill.split_artists("") == []
    assert backfill.split_artists("   ") == []


def test_empty_fragments_are_dropped():
    assert backfill.split_artists("A,, & B,") == ["A", "B"]
