#!/usr/bin/env python3
import logging
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pyperclip
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

DB_PATH = Path.home() / "Library/Messages/chat.db"
NICKNAME_CACHE_DIR = Path.home() / "Library/Messages/NickNameCache"
MAC_EPOCH = datetime(2001, 1, 1)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("2FA-code-catcher")

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def apple_time_to_dt(ts: float) -> datetime:
    """
    Convert Apple epoch time to Python datetime.
    Handles both nanoseconds and seconds.
    """
    if ts > 1e12:
        ts /= 1e9  # Convert nanoseconds to seconds
    return MAC_EPOCH + timedelta(seconds=ts)


def get_latest_message_from_them(retries=5, delay=2.0):
    for attempt in range(retries):
        try:
            with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
                conn.row_factory = sqlite3.Row
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
                if row:
                    timestamp = apple_time_to_dt(row["date"])
                    return {
                        "rowid": row["ROWID"],
                        "text": row["text"] or "",
                        "sender_type": "Them",
                        "handle_id": row["handle_id"],
                        "timestamp": timestamp,
                    }
                return None
        except sqlite3.OperationalError as e:
            msg = str(e).lower()
            if "locked" in msg or "busy" in msg:
                logger.info("Database temporarily locked; retrying...")
                time.sleep(delay)
                continue
            elif "unable to open" in msg:
                logger.info(
                    "Database temporarily unavailable; waiting for Messages to release it..."
                )
                time.sleep(delay * 2)
                continue
            else:
                logger.error(f"OperationalError: {e}")
                return None
        except sqlite3.Error as e:
            logger.error(f"General SQLite error: {e}")
            return None

    logger.error("Failed to read database after retries.")
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
                logger.info(f"[{msg['timestamp']}] {msg['sender_type']}: {msg['text']}")
                match = re.search(r"\b\d{4,8}\b", msg["text"])
                if match:
                    code = match.group()
                    pyperclip.copy(code)
                    logger.info(f"Copied code to clipboard: {code}")


def main():
    event_handler = MessageWatcher()
    observer = Observer()

    observer.schedule(event_handler, str(NICKNAME_CACHE_DIR), recursive=False)
    observer.start()
    logger.info("Watching for new messages... (Ctrl+C to stop)")

    try:
        observer.join()
    except KeyboardInterrupt:
        observer.stop()
        logger.info("\nStopped watching.")
    observer.join()


if __name__ == "__main__":
    main()
