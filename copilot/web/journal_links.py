"""One card per link in "Links and services": no call links, no repeated or OCR-variant URLs."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

URL_RE = re.compile(
    r"(?i)(?:https?://|www\.)[^\s<>'\"\])}]+|"
    r"(?<![@\w])(?:[a-z0-9-]+\.)+(?:com|io|ai|app|dev|net|org|ru|me|co|us)"
    r"(?:/[^\s<>'\"\])}]*)?"
)
# The call itself (join, meeting and web-client pages) is never a meeting resource.
CALL_LINK_HOSTS = (
    "zoom.us", "zoom.com", "zoomgov.com",
    "meet.google.com",
    "teams.microsoft.com", "teams.live.com",
    "telemost.yandex.ru", "telemost.yandex.com", "telemost.360.yandex.ru",
    "webex.com", "whereby.com", "meet.jit.si", "join.skype.com",
    "gotomeeting.com", "meet.goto.com", "bluejeans.com", "chime.aws",
    "ktalk.ru", "jazz.sber.ru", "salutejazz.ru",
)
LINK_CATEGORIES = {"URL", "SERVICE", "PRODUCT"}
# Characters screen OCR swaps for one another (forms -> torms, FAIp -> FAlp).
OCR_CONFUSABLE = ("ft", "il1|", "o0", "s5", "b8", "gq9p", "z2", "uv")


def call_host(host: str) -> bool:
    host = host.lower().removeprefix("www.")
    return any(host == domain or host.endswith("." + domain) for domain in CALL_LINK_HOSTS)


def _parts(raw: str) -> tuple[str, str] | None:
    value = raw.strip().rstrip(".,;:!?)]}>")
    if not re.match(r"(?i)^https?://", value):
        value = "https://" + value
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().removeprefix("www.")
    except ValueError:
        return None
    return (host, parsed.path.rstrip("/")) if host else None


def _ocr_variant(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    diffs = [(x.lower(), y.lower()) for x, y in zip(a, b) if x != y]
    return len(diffs) <= 1 and all(
        x == y or any(x in group and y in group for group in OCR_CONFUSABLE) for x, y in diffs
    )


def collapse_links(items: list[dict]) -> list[dict]:
    """Chronological items in, same order out, without call links and repeated links.

    A repeated link (same host, path equal or one OCR misread apart) keeps its
    earliest card, unless a later card adds a label (SERVICE over a bare URL).
    Other items pass through untouched.
    """
    kept: list[dict] = []
    groups: list[tuple[str, list[str], int]] = []  # host, paths seen, index in kept
    for item in items:
        if item.get("category") not in LINK_CATEGORIES:
            kept.append(item)
            continue
        links = [parts for raw in URL_RE.findall(str(item.get("text", ""))) if (parts := _parts(raw))]
        own = [parts for parts in links if not call_host(parts[0])]
        if links and not own:
            continue
        if not own:
            kept.append(item)  # A named mention without a URL.
            continue
        host, path = own[0]
        # ponytail: linear scan over the meeting's links; index by host if journals grow large.
        group = next((g for g in groups if g[0] == host and any(_ocr_variant(path, seen) for seen in g[1])), None)
        if group is None:
            groups.append((host, [path], len(kept)))
            kept.append(item)
            continue
        group[1].append(path)
        if kept[group[2]].get("category") == "URL" and item.get("category") != "URL":
            kept[group[2]] = item
    return kept
