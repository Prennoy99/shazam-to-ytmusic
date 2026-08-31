import os
import tempfile
from functools import lru_cache

from ytmusicapi import YTMusic


def _write_auth_file() -> str:
    auth_json = os.environ["YTMUSIC_AUTH_JSON"]
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        f.write(auth_json)
    return path


@lru_cache(maxsize=1)
def get_client() -> YTMusic:
    return YTMusic(_write_auth_file())


def is_in_playlist(playlist_id: str, video_id: str) -> bool:
    yt = get_client()
    playlist = yt.get_playlist(playlist_id, limit=None)
    existing_ids = {track["videoId"] for track in playlist.get("tracks", [])}
    return video_id in existing_ids


def add_to_playlist(playlist_id: str, video_id: str) -> bool:
    """Returns True if the track was added, False if it was already present."""
    if is_in_playlist(playlist_id, video_id):
        return False
    get_client().add_playlist_items(playlist_id, [video_id])
    return True
