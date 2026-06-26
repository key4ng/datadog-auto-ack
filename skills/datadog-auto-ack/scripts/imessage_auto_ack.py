#!/usr/bin/env python3
"""Auto-ack Datadog-style SMS alerts in macOS Messages.

The monitor reads Messages read-only and sends through the Messages app only
when an incoming message from the configured sender contains reply options with
"<number> ack" or "<number> ack all".
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


HOME = Path.home()
RUNTIME_DIR = Path(os.environ.get("AUTO_ACK_RUNTIME_DIR", HOME / ".codex/datadog-auto-ack"))
DB_PATH = os.environ.get("AUTO_ACK_DB_PATH", str(HOME / "Library/Messages/chat.db"))
TARGET = os.environ.get("AUTO_ACK_TARGET", "43152")
STATE_PATH = Path(os.environ.get("AUTO_ACK_STATE", RUNTIME_DIR / "state.json"))
LOG_PATH = Path(os.environ.get("AUTO_ACK_LOG", RUNTIME_DIR / "auto_ack.log"))
HEARTBEAT_PATH = Path(os.environ.get("AUTO_ACK_HEARTBEAT", RUNTIME_DIR / "heartbeat.txt"))
POLL_SECONDS = int(os.environ.get("AUTO_ACK_POLL_SECONDS", "60"))
DRY_RUN = os.environ.get("AUTO_ACK_DRY_RUN", "").lower() in {"1", "true", "yes", "on"}

ACK_REPLY_RE = re.compile(
    r"\bReply\b.*?\b(\d+)\s+ack(?:\s+all)?\b",
    re.IGNORECASE | re.DOTALL,
)


def log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).astimezone().isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")


def load_state() -> dict[str, object]:
    if not STATE_PATH.exists():
        return {"processed_ids": []}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"processed_ids": []}


def save_state(state: dict[str, object]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def send_sms(reply: str) -> None:
    if DRY_RUN:
        log(f"dry_run_reply={reply}")
        return

    script = f'''
tell application "Messages"
  set targetService to 1st service whose service type = SMS
  set targetBuddy to buddy "{TARGET}" of targetService
  send "{reply}" to targetBuddy
end tell
'''
    subprocess.run(["osascript", "-e", script], check=True)


def fetch_candidate_messages() -> list[sqlite3.Row]:
    query = """
        SELECT
          message.ROWID AS message_id,
          message.text,
          message.attributedBody AS attributed_body,
          message.date
        FROM message
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        LEFT JOIN chat_message_join ON message.ROWID = chat_message_join.message_id
        LEFT JOIN chat ON chat_message_join.chat_id = chat.ROWID
        WHERE message.is_from_me = 0
          AND (handle.id = ? OR chat.chat_identifier = ?)
          AND (message.text IS NOT NULL OR message.attributedBody IS NOT NULL)
        ORDER BY message.date DESC
        LIMIT 25
    """
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(query, (TARGET, TARGET)).fetchall()
    finally:
        conn.close()


def choose_reply(text: str) -> str | None:
    match = ACK_REPLY_RE.search(text)
    return match.group(1) if match else None


def message_text(row: sqlite3.Row) -> str:
    if row["text"]:
        return row["text"]

    body = row["attributed_body"]
    if body is None:
        return ""
    if isinstance(body, memoryview):
        body = body.tobytes()

    # macOS SMS rows sometimes store the visible string in an archived
    # attributedBody while message.text is NULL. A forgiving UTF-8 decode keeps
    # the embedded NSString content visible enough for the reply-option regex.
    return body.decode("utf-8", errors="ignore")


def poll_once() -> None:
    state = load_state()
    processed_ids = set(int(item) for item in state.get("processed_ids", []))
    changed = False

    for row in reversed(fetch_candidate_messages()):
        message_id = int(row["message_id"])
        if message_id in processed_ids:
            continue

        reply = choose_reply(message_text(row))
        if reply is None:
            continue

        send_sms(reply)
        processed_ids.add(message_id)
        changed = True
        log(f"replied={reply} message_id={message_id}")

    if changed:
        state["processed_ids"] = sorted(processed_ids)[-500:]
        state["last_checked_at"] = datetime.now(timezone.utc).astimezone().isoformat()
        save_state(state)

    HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_PATH.write_text(
        datetime.now(timezone.utc).astimezone().isoformat() + "\n",
        encoding="utf-8",
    )


def main() -> None:
    if "--test-parser" in sys.argv:
        examples = [
            "Reply 1 ack, 2 escalate, 3 resolve",
            "Reply 11 ack all, 12 escalate all, 13 resolve all",
            "hello",
        ]
        for item in examples:
            print(f"{item!r} => {choose_reply(item)!r}")
        return

    if "--once" in sys.argv:
        try:
            poll_once()
        except Exception as exc:
            log(f"error={exc!r}")
            raise
        return

    log(f"started target={TARGET} poll_seconds={POLL_SECONDS} dry_run={DRY_RUN}")
    while True:
        try:
            poll_once()
        except Exception as exc:
            log(f"error={exc!r}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
