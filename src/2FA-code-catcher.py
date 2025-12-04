#!/usr/bin/env python3
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pyperclip
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

DB_PATH = Path.home() / "Library/Messages/chat.db"
NICKNAME_CACHE_DIR = Path.home() / "Library/Messages/NickNameCache"
MAC_EPOCH = datetime(2001, 1, 1)


def apple_time_to_dt(ts: float) -> datetime:
    """
    Convert Apple epoch time to Python datetime.
    Handles both nanoseconds and seconds.
    """
    if ts > 1e12:
        ts /= 1e9  # Convert nanoseconds to seconds
    return MAC_EPOCH + timedelta(seconds=ts)


def get_latest_message_from_them():
    """
    Returns the latest message sent by someone else (not me) from the Messages DB.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ROWID, text, handle_id, is_from_me, date
                FROM message
                WHERE is_from_me = 0
                ORDER BY ROWID DESC
                LIMIT 1;
                """
            )
            row = cursor.fetchone()
    except sqlite3.Error as e:
        print(f"Error reading database: {e}")
        return None

    if row:
        rowid, text, handle_id, is_from_me, date_raw = row
        timestamp = apple_time_to_dt(date_raw)
        return {
            "rowid": rowid,
            "text": text or "",
            "sender_type": "Them",
            "handle_id": handle_id,
            "timestamp": timestamp,
        }

    return None


class MessageWatcher(FileSystemEventHandler):
    def __init__(self):
        self.last_rowid = None

    def on_modified(self, event):
        # Trigger on NickNameCache database files which seem to be the most reliable indicator of a new message
        # Note: The chat.db and chat.db-wal do not seem to written to directly upon arrival of a new message
        if event.src_path.endswith((".db", ".db-wal", ".db-shm")):
            self.check_new_message()

    def check_new_message(self):
        msg = get_latest_message_from_them()
        if msg and msg["rowid"] != self.last_rowid:
            self.last_rowid = msg["rowid"]
            # Check for PIN/code and copy to clipboard
            if re.search(r"PIN|code", msg["text"], re.IGNORECASE):
                print(f"[{msg['timestamp']}] {msg['sender_type']}: {msg['text']}")
                match = re.search(r"\b\d{4,8}\b", msg["text"])
                if match:
                    code = match.group()
                    pyperclip.copy(code)
                    print(f"Copied code to clipboard: {code}")


def main():
    event_handler = MessageWatcher()
    observer = Observer()

    observer.schedule(event_handler, str(NICKNAME_CACHE_DIR), recursive=False)
    observer.start()
    print("Watching for new messages... (Ctrl+C to stop)")

    try:
        observer.join()
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped watching.")
    observer.join()


if __name__ == "__main__":
    main()
