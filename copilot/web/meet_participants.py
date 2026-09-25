"""Conservative Google Meet account-label and active-tile extraction from OCR frames."""

from __future__ import annotations

import re
from pathlib import Path


_UI_WORDS = (
    "meet", "chrome", "active", "portuguese", "english", "everyone",
    "captions", "settings", "sharing", "available", "recording",
    "japanese", "indonesian", "hindi", "estonian", "italian", "beta",
)


def _label_observations(observations: list[dict]) -> list[dict]:
    candidates = []
    for item in observations:
        text = str(item.get("text") or "").strip().lstrip("🔇🎙• ")
        if not (2 <= len(text) <= 40) or len(text.split()) > 4:
            continue
        if any(word in text.casefold() for word in _UI_WORDS):
            continue
        if not all(char.isalpha() or char in " .'-’" for char in text):
            continue
        if re.fullmatch(r"[A-Za-zА-Яа-яЁё]\.?", text):
            continue
        try:
            x = float(item.get("x", 0))
            y = float(item.get("y", 0))
            width = float(item.get("width", 0))
        except (TypeError, ValueError):
            continue
        if not (0.02 < x < 0.95 and 0.08 < y < 0.80 and 0 < width < 0.30):
            continue
        candidates.append({"text": text, "x": x, "y": y, "width": width})

    rows: list[list[dict]] = []
    for item in sorted(candidates, key=lambda value: value["y"]):
        row = next((row for row in rows if abs(row[0]["y"] - item["y"]) <= 0.018), None)
        if row is None:
            row = []
            rows.append(row)
        row.append(item)

    labels = []
    for row in rows:
        ordered = sorted(row, key=lambda item: item["x"])
        if len(ordered) < 2 or len(ordered) > 8:
            continue
        if any(right["x"] - left["x"] < 0.035 for left, right in zip(ordered, ordered[1:])):
            continue
        labels.extend(ordered)
    return labels


def meet_participant_labels(observations: list[dict]) -> list[str]:
    """Only OCR labels sharing a Meet tile row qualify as account names."""
    language_menu = sum(
        any(language in str(item.get("text") or "").casefold()
            for language in ("english (", "dutch", "filipino", "finnish", "french", "german", "greek", "hungarian"))
        for item in observations
    )
    if language_menu >= 4:
        return []
    labels = list(dict.fromkeys(item["text"] for item in _label_observations(observations)))
    # A language/settings overlay can create several aligned OCR rows. Meet's
    # grid never has more than eight readable tile labels in one captured view.
    return labels if len(labels) <= 8 else []


def meet_active_speaker(path: Path, observations: list[dict]) -> str:
    """Map Meet's light-blue active-tile outline to an OCR account label."""
    try:
        import numpy as np
        from PIL import Image

        image = np.asarray(Image.open(path).convert("RGB"))
        height, width, _ = image.shape
        red, green, blue = (image[:, :, index] for index in range(3))
        outline = (
            (red > 150) & (red < 185) &
            (green > 180) & (green < 210) &
            (blue > 220) & (blue < 250)
        )
        strength = outline[int(height * 0.12):int(height * 0.90)].sum(axis=0)
        columns = np.where(strength > height * 0.18)[0]
        groups: list[list[int]] = []
        for column in columns:
            index = int(column)
            if not groups or index > groups[-1][1] + 2:
                groups.append([index, index])
            else:
                groups[-1][1] = index
        allowed_labels = set(meet_participant_labels(observations))
        labels = [item for item in _label_observations(observations) if item["text"] in allowed_labels]
        matches: list[tuple[float, str]] = []
        for index, left_group in enumerate(groups):
            for right_group in groups[index + 1:]:
                left = (left_group[0] + left_group[1]) // 2
                right = (right_group[0] + right_group[1]) // 2
                if not width * 0.06 <= right - left <= width * 0.75:
                    continue
                left_rows = np.where(outline[:, left])[0]
                right_rows = np.where(outline[:, right])[0]
                if not len(left_rows) or not len(right_rows):
                    continue
                top = max(int(left_rows.min()), int(right_rows.min()))
                bottom = min(int(left_rows.max()), int(right_rows.max()))
                if bottom - top < height * 0.16:
                    continue
                for label in labels:
                    center_x = (label["x"] + label["width"] / 2) * width
                    center_y = (1 - label["y"]) * height
                    if left < center_x < right and bottom - height * 0.08 < center_y < bottom + height * 0.02:
                        matches.append((float(min(strength[left], strength[right])), label["text"]))
        return max(matches)[1] if matches else ""
    except (ImportError, OSError, ValueError, TypeError):
        return ""
