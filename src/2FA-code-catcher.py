#!/usr/bin/env python3
import re
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import pyperclip

DB_PATH = Path.home() / "Library/Messages/chat.db"
MAC_EPOCH = datetime(2001, 1, 1)
POLL_INTERVAL_SEC = 1


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


def main():
    last_rowid = None
    print("Polling messages for new incoming texts... (Ctrl+C to stop)")

    try:
        while True:
            msg = get_latest_message_from_them()
            if msg and msg["rowid"] != last_rowid:
                last_rowid = msg["rowid"]

                # Check for PIN/code and copy to clipboard
                if re.search(r"PIN|code", msg["text"], re.IGNORECASE):
                    print(f"[{msg['timestamp']}] {msg['sender_type']}: {msg['text']}")

                    match = re.search(r"\b\d{4,8}\b", msg["text"])
                    if match:
                        code = match.group()
                        pyperclip.copy(code)
                        print("Detected code and copied to clipboard:", code)

            time.sleep(POLL_INTERVAL_SEC)

    except KeyboardInterrupt:
        print("\nStopped polling.")


if __name__ == "__main__":
    main()
