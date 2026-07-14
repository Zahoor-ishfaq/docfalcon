"""Agent tool: fuzzy name match for Arabic + English dedup."""

from difflib import SequenceMatcher


def _normalize(s: str) -> str:
    # Arabic yeh/kaf variants → canonical; lowercase + strip for English
    return (
        s.replace("ي", "ى").replace("ك", "ک")
        .replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        .strip().lower()
    )


def compare_names(name_a: str, name_b: str) -> dict:
    """Returns {match: bool, score: float, name_a, name_b}.
    match=True when score ≥ 0.82 (catches common Arabic transliteration variants).
    """
    if not name_a or not name_b:
        return {"match": False, "score": 0.0, "name_a": name_a, "name_b": name_b}
    score = SequenceMatcher(None, _normalize(name_a), _normalize(name_b)).ratio()
    return {
        "match": score >= 0.82,
        "score": round(score, 3),
        "name_a": name_a,
        "name_b": name_b,
    }