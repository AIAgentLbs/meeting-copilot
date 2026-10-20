"""Read dated call preparation from active local repositories, without copying it."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import threading
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit


DATE_RE = re.compile(r"(?m)^call_date:\s*(\d{4}-\d{2}-\d{2})\s*$")
HEADING_RE = re.compile(r"(?m)^#\s+(.+?)\s*$")
LINK_RE = re.compile(r"\[([^\]]{2,100})\]\((https://[^\s)]+)\)")
NUMBERED_RE = re.compile(r"^\s*\d+[.)]\s+(.+)$")
UNCHECKED_RE = re.compile(r"^\s*-\s*\[\s\]\s+(.+)$")
MAX_DOCUMENT_BYTES = 512_000


def _section(markdown: str, *names: str) -> str:
    wanted = tuple(name.casefold() for name in names)
    current = False
    lines: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("## "):
            title = line[3:].strip().casefold()
            if current:
                break
            current = any(name in title for name in wanted)
            continue
        if current:
            lines.append(line)
    return "\n".join(lines)


def _clean(value: str, limit: int = 240) -> str:
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"[*_`]+", "", value)
    return " ".join(value.split())[:limit]


def _safe_link(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username


def _item_id(kind: str, text: str) -> str:
    return f"repo-{kind}-{hashlib.sha256(text.casefold().encode()).hexdigest()[:12]}"


def parse_preparation(path: Path, *, repo_name: str = "") -> dict | None:
    """Extract a concise checklist from an existing dated Markdown preparation."""
    try:
        if path.stat().st_size > MAX_DOCUMENT_BYTES:
            return None
        markdown = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    dated = DATE_RE.search(markdown[:2000])
    heading = HEADING_RE.search(markdown)
    if not dated or not heading:
        return None
    try:
        date.fromisoformat(dated.group(1))
    except ValueError:
        return None
    title = _clean(re.sub(r"^(?:Sales kit|Call prep|Подготовка)\s*:\s*", "", heading.group(1), flags=re.I), 180)
    if not title:
        return None
    questions_section = _section(markdown, "опросник", "вопросы к встрече", "questions")
    if not questions_section:
        return None

    questions: list[str] = []
    for line in questions_section.splitlines():
        if line.startswith("### ") and questions:
            break
        matched = NUMBERED_RE.match(line)
        if matched:
            questions.append(_clean(matched.group(1)))
    if not questions:
        questions = [
            _clean(line[2:]) for line in questions_section.splitlines()
            if line.startswith("- ") and "?" in line
        ]
    questions = list(dict.fromkeys(item for item in questions if item))[:12]
    if not questions:
        return None

    objections_section = _section(markdown, "возражения", "objections")
    objections = []
    for line in objections_section.splitlines():
        matched = re.match(r"^\*\*(.+?)\*\*\s*$", line.strip())
        if matched and ("«" in matched.group(1) or "?" in matched.group(1)):
            objections.append(_clean(matched.group(1), 180))
    objections = list(dict.fromkeys(objections))[:15]

    readiness_section = _section(markdown, "проверка перед встречей", "готовность", "preflight")
    risks = list(dict.fromkeys(
        _clean(match.group(1), 180)
        for line in readiness_section.splitlines()
        if (match := UNCHECKED_RE.match(line))
    ))[:10]

    items = [
        {"id": _item_id("q", text), "kind": "question", "text": text}
        for text in questions
    ] + [
        {"id": _item_id("r", text), "kind": "risk", "text": text}
        for text in risks
    ] + [
        {"id": _item_id("o", text), "kind": "objection", "text": text}
        for text in objections
    ]

    memo = _section(markdown, "мемо перед встречей", "meeting memo", "краткое резюме")
    goal = re.search(r"(?m)^\*\*(?:Цель встречи|Meeting goal)\.\*\*\s*(.+)$", memo)
    intro = _clean(goal.group(1), 650) if goal else ""
    aliases = [part.strip() for part in re.split(r"[/·—|]", title) if len(part.strip()) >= 3]
    seen_urls: set[str] = set()
    links = []
    for label, url in LINK_RE.findall(markdown):
        if url in seen_urls or not _safe_link(url):
            continue
        lower = label.casefold()
        if not any(word in lower for word in ("sales kit", "мемо", "телемост", "meet", "проект", "дашборд", "dashboard", "brief", "demo")):
            continue
        seen_urls.add(url)
        links.append({"label": _clean(label, 80), "url": url})
        if len(links) >= 10:
            break

    digest = hashlib.sha256(f"{path.resolve()}:{dated.group(1)}".encode()).hexdigest()[:16]
    return {
        "id": f"repo-{digest}", "call_date": dated.group(1),
        "title": title, "intro": intro, "title_aliases": aliases,
        "attendee_aliases": aliases, "links": links, "items": items,
        "source_label": f"{repo_name}/{path.name}" if repo_name else path.name,
        "source_path": str(path.resolve()),
        "meeting_link": next((link["url"] for link in links if any(
            word in link["label"].casefold() for word in ("телемост", "meet")
        )), ""),
    }


class RepositoryPreparations:
    def __init__(self, active_repos_path: Path) -> None:
        self.active_repos_path = active_repos_path
        self._cache: dict[tuple[str, float], tuple[float, list[dict]]] = {}
        self._lock = threading.Lock()

    def active_roots(self) -> list[tuple[str, Path]]:
        try:
            payload = json.loads(self.active_repos_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        repositories = payload.get("repositories", []) if isinstance(payload, dict) else []
        if not isinstance(repositories, list):
            return []
        roots = []
        for item in repositories[:15]:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                root = Path(item["path"]).resolve()
                if root.is_dir():
                    roots.append((str(item.get("name") or root.name), root))
        return roots

    def from_active_file(self, source: str) -> dict | None:
        path = Path(source).resolve()
        for name, root in self.active_roots():
            if path.is_relative_to(root) and path.is_file():
                return parse_preparation(path, repo_name=name)
        return None

    def context_from_active_file(self, source: str, max_chars: int = 12000) -> str:
        path = Path(source).resolve()
        if not any(path.is_relative_to(root) for _, root in self.active_roots()):
            return ""
        try:
            if path.stat().st_size > MAX_DOCUMENT_BYTES:
                return ""
            markdown = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return ""
        sections = [
            _section(markdown, "мемо перед встречей", "meeting memo"),
            _section(markdown, "шпаргалка ведущего", "talk track"),
            _section(markdown, "опросник", "вопросы к встрече", "questions"),
            _section(markdown, "ответы на вопросы и возражения", "objections"),
            _section(markdown, "проверка перед встречей", "готовность", "preflight"),
        ]
        return "\n\n".join(section for section in sections if section)[:max_chars]

    def for_date(self, call_date: str) -> list[dict]:
        try:
            date.fromisoformat(call_date)
        except ValueError:
            return []
        try:
            manifest_mtime = self.active_repos_path.stat().st_mtime
        except OSError:
            manifest_mtime = 0.0
        key = (call_date, manifest_mtime)
        with self._lock:
            cached = self._cache.get(key)
            if cached and time.monotonic() - cached[0] < 120:
                return list(cached[1])
        results = []
        for name, root in self.active_roots():
            try:
                scan = subprocess.run(
                    ["rg", "-l", "-m", "1", "-g", "*.md", "-g", "!node_modules/**",
                     "-g", "!vendor/**", f"^call_date:\\s*{call_date}\\s*$", "."],
                    cwd=root, capture_output=True, text=True, timeout=4, check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            for relative in scan.stdout.splitlines()[:40]:
                path = (root / relative).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    continue
                plan = parse_preparation(path, repo_name=name)
                if plan and plan["call_date"] == call_date:
                    results.append(plan)
        results = results[:30]
        with self._lock:
            self._cache = {key: (time.monotonic(), results)}
        return list(results)
