"""Ground Teams account labels in the meeting video, never in slide/email text."""

import re
from collections import Counter
from difflib import SequenceMatcher


def teams_participant_labels(observations: list[dict]) -> list[str]:
    # Require the *visible address bar* or Teams call toolbar, not a window
    # title left over while the browser is displaying an unrelated tab.
    address = any(
        float(item.get("y", 0)) > 0.85
        and re.search(r"\bteams\.(?:live|microsoft)\.com(?:/|\b)", str(item.get("text", "")), re.I)
        for item in observations
    )
    if not address:
        return []
    labels = []
    for item in observations:
        text = str(item.get("text", "")).strip().strip("🔇🎙• ")
        # Vision sometimes reads the microphone icon as an isolated S.
        text = re.sub(r"\s+[S§]$", "", text)
        words = text.split()
        if not 2 <= len(words) <= 4 or not 5 <= len(text) <= 60:
            continue
        if not all(re.fullmatch(r"[^\W\d_][^\W\d_.'’\-]*", word) and word[0].isupper() for word in words):
            continue
        x, y, width = (float(item.get(key, 0)) for key in ("x", "y", "width"))
        # Bottom-left name chip on the main remote tile in Teams 1:1 calls.
        # Do not interpret local thumbnail initials or content in a share.
        if 0.015 <= x <= 0.12 and 0.035 <= y <= 0.12 and 0 < width <= 0.25:
            labels.append(text)
    return list(dict.fromkeys(labels))


def teams_one_to_one_name(frames: list[dict]) -> str:
    """A repeated single main-tile account, with no contradictory remote labels."""
    relevant = [frame for frame in frames if frame.get("participant_platform") == "teams"]
    counts = Counter(name for frame in relevant for name in frame.get("participant_labels", []))
    if not counts:
        return ""
    name = counts.most_common(1)[0][0]
    if any(SequenceMatcher(None, name.casefold(), other.casefold()).ratio() < .90 for other in counts):
        return ""
    return name if sum(name in frame.get("participant_labels", []) for frame in relevant) >= 2 else ""
