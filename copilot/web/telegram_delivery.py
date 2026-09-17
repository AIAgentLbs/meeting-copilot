#!/usr/bin/env python3
"""Deliver a Meeting Copilot memo to the owner's Telegram Saved Messages."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

from telethon import TelegramClient


def load_account(config_path: Path, label: str) -> dict:
    values: dict[str, str] = {}
    for raw in config_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    indexes = sorted(
        int(match.group(1))
        for key in values
        if (match := re.fullmatch(r"TG(\d+)_API_ID", key))
    )
    for index in indexes:
        prefix = f"TG{index}_"
        if values.get(prefix + "LABEL") != label:
            continue
        session = Path(values[prefix + "SESSION"]).expanduser()
        if not Path(str(session) + ".session").is_file():
            fallback = config_path.parent / session.name
            if Path(str(fallback) + ".session").is_file():
                session = fallback
        return {
            "api_id": int(values[prefix + "API_ID"]),
            "api_hash": values[prefix + "API_HASH"],
            "session": str(session),
        }
    raise RuntimeError(f"Telegram account label is not configured: {label}")


async def deliver(args: argparse.Namespace) -> dict:
    account = load_account(args.config, args.account)
    client = TelegramClient(
        account["session"], account["api_id"], account["api_hash"]
    )
    await client.connect()
    try:
        if not await client.is_user_authorized():
            return {"ok": False, "status": "auth_required"}
        text = (
            f"Meeting Copilot by aiagentlbs.com\n{args.title}\n{args.date}\n\n"
            "HTML и PDF сохранены в Google Drive. PDF приложен к сообщению."
        )
        links = [
            ("Папка", args.drive_folder_url),
            ("HTML", args.drive_html_url),
            ("PDF", args.drive_pdf_url),
        ]
        available = [f"{label}: {url}" for label, url in links if url]
        if available:
            text += "\n\nСсылки Google Drive:\n" + "\n".join(available)
        message = await client.send_file(
            args.target,
            str(args.pdf),
            caption=text,
            force_document=True,
        )
        return {"ok": True, "status": "sent", "message_id": message.id}
    finally:
        await client.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--account", required=True)
    parser.add_argument("--target", default="me")
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--drive-folder-url", default="")
    parser.add_argument("--drive-html-url", default="")
    parser.add_argument("--drive-pdf-url", default="")
    args = parser.parse_args()
    if not args.pdf.is_file():
        print(json.dumps({"ok": False, "status": "missing_pdf"}))
        return 2
    try:
        result = asyncio.run(deliver(args))
    except Exception as exc:
        print(json.dumps({"ok": False, "status": "failed", "error": type(exc).__name__}))
        return 1
    print(json.dumps(result))
    return 0 if result.get("ok") else 4


if __name__ == "__main__":
    raise SystemExit(main())
