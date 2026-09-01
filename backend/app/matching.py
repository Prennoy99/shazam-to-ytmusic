from .ytmusic_client import get_client


def _normalize(name: str) -> str:
    return name.strip().lower()


def find_best_match(title: str, artists: list[str]) -> dict | None:
    query = f"{title} {' '.join(artists)}".strip()
    results = get_client().search(query, filter="songs")
    if not results:
        return None

    target_artists = {_normalize(a) for a in artists if a}
    if not target_artists:
        return results[0]

    def artist_overlap(result: dict) -> int:
        result_artists = {_normalize(a.get("name", "")) for a in (result.get("artists") or [])}
        return len(target_artists & result_artists)

    # max() keeps the first (highest-relevance) result among ties, so this
    # only overrides the top hit when a later result actually matches better.
    return max(results, key=artist_overlap)
