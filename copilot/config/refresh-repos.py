#!/usr/bin/env python3
"""Build the meeting-copilot repository manifest without changing repositories."""

from __future__ import annotations

import json
import os
import re
import select
import subprocess
import tempfile
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


HOME = Path.home()
OUTPUT = HOME / ".config" / "meeting-copilot" / "repos.json"
SKIP_DIRS = {
    ".cache",
    ".Trash",
    "Trash",
    "Library",
    "node_modules",
    ".venv",
    "venv",
    "vendor",
    "dist",
    "build",
}
DOC_DIR_NAMES = {
    "doc",
    "docs",
    "documentation",
    "wiki",
    "spec",
    "specs",
    "plans",
    "notes",
    "memory",
}
GIT_TIMEOUT_SECONDS = 5


TIMEOUT_SENTINEL = "__MEETING_COPILOT_TIMEOUT__"


def command(repo: Path, *args: str) -> str:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "--no-optional-locks", *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return TIMEOUT_SENTINEL
    return result.stdout.strip()


def working_tree_status(repo: Path) -> tuple[str, list[str]]:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    base = ["git", "-C", str(repo), "--no-optional-locks"]
    try:
        unstaged = subprocess.run(
            [*base, "diff", "--quiet", "--"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
        staged = subprocess.run(
            [*base, "diff", "--cached", "--quiet", "--"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "unknown_timeout", [f"tracked working-tree inspection exceeded {GIT_TIMEOUT_SECONDS} seconds"]
    if unstaged.returncode == 1 or staged.returncode == 1:
        return "dirty", []
    if unstaged.returncode not in {0, 1} or staged.returncode not in {0, 1}:
        return "unknown_error", ["git diff could not classify the working tree"]

    process = subprocess.Popen(
        [*base, "ls-files", "--others", "--exclude-standard", "--directory"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    assert process.stdout is not None
    readable, _, _ = select.select([process.stdout], [], [], GIT_TIMEOUT_SECONDS)
    if not readable:
        process.kill()
        process.wait()
        return "unknown_timeout", [f"untracked-file inspection exceeded {GIT_TIMEOUT_SECONDS} seconds"]
    first_line = process.stdout.readline()
    if first_line:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return "dirty", []
    process.wait()
    return "clean", []


def existing_search_roots() -> list[Path]:
    cwd = Path.cwd()
    candidates = [
        cwd,
        cwd.parent,
        HOME / "Projects",
        HOME / "projects",
        HOME / "Developer",
        HOME / "Development",
        HOME / "dev",
        HOME / "code",
        HOME / "Code",
        HOME / "work",
        HOME / "workspace",
        HOME / "src",
        HOME / "Documents",
    ]
    unique_by_inode: dict[tuple[int, int], Path] = {}
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        stat = candidate.stat()
        unique_by_inode.setdefault((stat.st_dev, stat.st_ino), candidate)

    roots: list[Path] = []
    for candidate in sorted(unique_by_inode.values(), key=lambda p: (len(p.parts), str(p))):
        if any(candidate == root or candidate.is_relative_to(root) for root in roots):
            continue
        roots.append(candidate)
    return roots


def discover_repositories(roots: list[Path]) -> list[Path]:
    found: dict[tuple[int, int], Path] = {}
    for root in roots:
        for current, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and d != ".git"]
            current_path = Path(current)
            git_marker = current_path / ".git"
            if git_marker.is_dir() or git_marker.is_file():
                stat = current_path.stat()
                found.setdefault((stat.st_dev, stat.st_ino), current_path)
                dirs[:] = []
    return sorted(found.values(), key=lambda p: str(p).lower())


def readme_metadata(repo: Path) -> tuple[str | None, str | None]:
    candidates = sorted(
        (p for p in repo.iterdir() if p.is_file() and p.name.lower().startswith("readme")),
        key=lambda p: (p.suffix.lower() not in {".md", ".markdown"}, p.name.lower()),
    )
    if not candidates:
        return None, None
    readme = candidates[0]
    try:
        lines = readme.read_text(encoding="utf-8", errors="replace").splitlines()[:160]
    except OSError:
        return readme.name, None

    title = None
    summary_lines: list[str] = []
    in_fence = False
    for raw in lines:
        line = raw.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line:
            if summary_lines:
                break
            continue
        if title is None and line.startswith("#"):
            title = line.lstrip("#").strip()
            continue
        if line.startswith(("[![", "![", "<", "#", "---", "***")):
            continue
        if re.match(r"^\[.+\]:\s*https?://", line):
            continue
        summary_lines.append(line)
        if len(" ".join(summary_lines)) >= 500:
            break

    summary = " ".join(summary_lines)[:500] or None
    return title or readme.stem, summary


def documentation(repo: Path) -> tuple[list[str], list[str]]:
    doc_dirs: list[str] = []
    markdown: list[str] = []
    try:
        for child in repo.iterdir():
            if child.is_dir() and child.name.lower() in DOC_DIR_NAMES:
                doc_dirs.append(child.name)
            elif child.is_file() and child.suffix.lower() in {".md", ".markdown"}:
                markdown.append(child.name)
        for doc_dir in doc_dirs:
            base = repo / doc_dir
            for current, dirs, files in os.walk(base):
                relative_depth = len(Path(current).relative_to(base).parts)
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                if relative_depth >= 2:
                    dirs[:] = []
                for filename in files:
                    if Path(filename).suffix.lower() in {".md", ".markdown"}:
                        markdown.append(str((Path(current) / filename).relative_to(repo)))
    except OSError:
        pass
    return sorted(set(doc_dirs), key=str.lower), sorted(set(markdown), key=str.lower)[:120]


def inspect_repository(repo: Path) -> dict[str, object]:
    warnings: list[str] = []
    head_output = command(repo, "rev-parse", "HEAD")
    head = None if head_output in {"", TIMEOUT_SENTINEL} else head_output
    if head_output == TIMEOUT_SENTINEL:
        warnings.append("HEAD inspection timed out")
    branch_output = command(repo, "symbolic-ref", "--short", "-q", "HEAD")
    branch = "UNKNOWN_TIMEOUT" if branch_output == TIMEOUT_SENTINEL else (branch_output or "DETACHED")
    if branch_output == TIMEOUT_SENTINEL:
        warnings.append("branch inspection timed out")
    status, status_warnings = working_tree_status(repo)
    warnings.extend(status_warnings)
    remotes = []
    remote_names = command(repo, "remote")
    if remote_names == TIMEOUT_SENTINEL:
        remote_names = ""
        warnings.append("remote inspection timed out")
    for name in remote_names.splitlines():
        url = command(repo, "remote", "get-url", name)
        remotes.append({"name": name, "url": None if url in {"", TIMEOUT_SENTINEL} else url})
    readme_title, readme_summary = readme_metadata(repo)
    doc_dirs, markdown_files = documentation(repo)
    return {
        "name": repo.name,
        "path": str(repo),
        "branch": branch,
        "head": head,
        "status": status,
        "remotes": remotes,
        "readme_title": readme_title,
        "readme_summary": readme_summary,
        "documentation_directories": doc_dirs,
        "major_markdown_files": markdown_files,
        "inspection_warnings": warnings,
    }


def refresh_status(record: dict[str, object]) -> dict[str, object]:
    repo = Path(str(record["path"]))
    updated = dict(record)
    if not repo.exists():
        updated["status"] = "missing"
        updated["inspection_warnings"] = ["repository path no longer exists"]
        return updated
    warnings: list[str] = []
    head_output = command(repo, "rev-parse", "HEAD")
    updated["head"] = None if head_output in {"", TIMEOUT_SENTINEL} else head_output
    if head_output == TIMEOUT_SENTINEL:
        warnings.append("HEAD inspection timed out")
    branch_output = command(repo, "symbolic-ref", "--short", "-q", "HEAD")
    updated["branch"] = (
        "UNKNOWN_TIMEOUT" if branch_output == TIMEOUT_SENTINEL else (branch_output or "DETACHED")
    )
    if branch_output == TIMEOUT_SENTINEL:
        warnings.append("branch inspection timed out")
    updated["status"], status_warnings = working_tree_status(repo)
    warnings.extend(status_warnings)
    updated["inspection_warnings"] = warnings
    return updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=OUTPUT,
        help="manifest to refresh (defaults to the full repository catalog)",
    )
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="refresh branch, HEAD, and working-tree status for the existing manifest",
    )
    args = parser.parse_args()
    output = args.manifest.expanduser().resolve()

    roots = existing_search_roots()
    preserved: dict[str, object] = {}
    if args.status_only:
        if not output.is_file():
            parser.error(f"manifest does not exist: {output}")
        current = json.loads(output.read_text(encoding="utf-8"))
        preserved = {
            key: value
            for key, value in current.items()
            if key not in {"generated_at", "search_roots", "repository_count", "repositories"}
        }
        old_records = current.get("repositories", [])
        with ThreadPoolExecutor(max_workers=min(12, max(1, len(old_records)))) as pool:
            records = list(pool.map(refresh_status, old_records))
        roots = [Path(p) for p in current.get("search_roots", [])]
    else:
        repositories = discover_repositories(roots)
        with ThreadPoolExecutor(max_workers=min(12, max(1, len(repositories)))) as pool:
            records = list(pool.map(inspect_repository, repositories))
    payload = preserved | {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "search_roots": [str(p) for p in roots],
        "repository_count": len(records),
        "repositories": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix="repos.", suffix=".json", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary_name, output)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    mode = "status" if args.status_only else "full"
    print(f"Repository manifest refreshed ({mode}): {len(records)} repositories -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
