import os

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from .auth import verify_api_key
from .matching import find_best_match
from .ytmusic_client import add_to_playlist

app = FastAPI(title="shazam-to-ytmusic")

PLAYLIST_ID = os.environ["PLAYLIST_ID"]


class SearchRequest(BaseModel):
    title: str
    artists: list[str] = []


class SearchResponse(BaseModel):
    found: bool
    video_id: str | None = None
    matched_title: str | None = None
    matched_artists: list[str] = []


class AddToPlaylistRequest(BaseModel):
    video_id: str


class AddToPlaylistResponse(BaseModel):
    added: bool  # False also means "already in the playlist"


@app.post(
    "/search",
    response_model=SearchResponse,
    dependencies=[Depends(verify_api_key)],
)
def search(req: SearchRequest) -> SearchResponse:
    """Resolve a title/artist to a YouTube Music video ID.

    Shared by the Android live-share pipeline and the local backfill script.
    """
    match = find_best_match(req.title, req.artists)
    if match is None:
        return SearchResponse(found=False)

    return SearchResponse(
        found=True,
        video_id=match["videoId"],
        matched_title=match.get("title"),
        matched_artists=[a.get("name") for a in (match.get("artists") or []) if a.get("name")],
    )


@app.post(
    "/add-to-playlist",
    response_model=AddToPlaylistResponse,
    dependencies=[Depends(verify_api_key)],
)
def add_to_playlist_endpoint(req: AddToPlaylistRequest) -> AddToPlaylistResponse:
    """Add a video ID to the configured playlist, skipping if already present.

    Shared by the Android live-share pipeline and the local backfill script.
    """
    added = add_to_playlist(PLAYLIST_ID, req.video_id)
    return AddToPlaylistResponse(added=added)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
