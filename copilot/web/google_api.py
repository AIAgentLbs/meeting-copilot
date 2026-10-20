"""Bounded adapter for the product's existing Google commands, not a general CLI."""
import base64
import json
import mimetypes
import uuid
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote


def part(value):
    return quote(str(value), safe="")


def read(oauth, command, params):
    params = dict(params or {})
    routes = {
        ("calendar", "events", "list"): ("https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events", ("calendarId",)),
        ("drive", "files", "list"): ("https://www.googleapis.com/drive/v3/files", ()),
        ("gmail", "users", "messages", "list"): ("https://gmail.googleapis.com/gmail/v1/users/{userId}/messages", ("userId",)),
        ("gmail", "users", "messages", "get"): ("https://gmail.googleapis.com/gmail/v1/users/{userId}/messages/{id}", ("userId", "id")),
        ("docs", "documents", "get"): ("https://docs.googleapis.com/v1/documents/{documentId}", ("documentId",)),
        ("sheets", "spreadsheets", "values", "get"): ("https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/{range}", ("spreadsheetId", "range")),
    }
    if tuple(command) not in routes:
        raise ValueError("google_operation_not_allowed")
    template, keys = routes[tuple(command)]
    url = template.format(**{key: part(params.pop(key)) for key in keys})
    params = {k: str(v).lower() if isinstance(v, bool) else v for k, v in params.items()}
    return oauth.request("context", "GET", url, params=params, timeout=4)


def delivery(oauth, args, timeout):
    args = list(args)
    flags = {}
    first = next((i for i, value in enumerate(args) if value.startswith("--")), len(args))
    command = args[:first]
    rest = args[first:]
    if len(rest) % 2:
        raise ValueError("google_operation_not_allowed")
    flags.update(zip(rest[::2], rest[1::2]))
    params = json.loads(flags.get("--params", "{}"))
    body = json.loads(flags.get("--json", "{}"))
    if command == ["gmail", "+send"]:
        message = EmailMessage()
        message["From"] = oauth.status()["account"]
        message["To"], message["Subject"] = flags["--to"], flags["--subject"]
        message.set_content(flags["--body"])
        attachment = Path(flags["--attach"])
        if attachment.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("attachment_too_large")
        message.add_attachment(attachment.read_bytes(), maintype="application", subtype="pdf", filename="meeting-report.pdf")
        return oauth.request("mail", "POST", "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                             body={"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}, timeout=timeout)
    if command not in [["drive", "files", method] for method in ("list", "create", "update")]:
        raise ValueError("google_operation_not_allowed")
    method = command[-1]
    url = "https://www.googleapis.com/drive/v3/files"
    if method == "update":
        url += "/" + part(params.pop("fileId"))
    if method == "list":
        return oauth.request("drive", "GET", url, params=params, timeout=timeout)
    if "--upload" not in flags:
        return oauth.request("drive", "POST", url, params=params, body=body, timeout=timeout)
    path = Path(flags["--upload"])
    if path.stat().st_size > 25 * 1024 * 1024:
        raise ValueError("attachment_too_large")
    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    payload = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode()
               + json.dumps(body).encode() + f"\r\n--{boundary}\r\nContent-Type: {mime}\r\n\r\n".encode()
               + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode())
    return oauth.request("drive", "PATCH" if method == "update" else "POST",
                         url.replace("/drive/v3/", "/upload/drive/v3/"),
                         params={**params, "uploadType": "multipart"}, data=payload,
                         content_type=f"multipart/related; boundary={boundary}", timeout=timeout)
