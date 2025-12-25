#!/usr/bin/env python3

import logging
import re
import signal
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pyperclip

DB_PATH = Path.home() / "Library/Messages/chat.db"
MAC_EPOCH = datetime(2001, 1, 1)

LOG_PREDICATE = (
    'process == "imagent" AND ' 'eventMessage CONTAINS "SMSReceivedRelayMessage"'
)

LOG_CMD = [
    "log",
    "stream",
    "--style",
    "syslog",
    "--predicate",
    LOG_PREDICATE,
    "--line-buffered",
]

CODE_REGEX = re.compile(r"\b\d{4,8}\b")
KEYWORD_REGEX = re.compile(r"PIN|code", re.IGNORECASE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("2FA-code-catcher")


def apple_time_to_dt(ts: float) -> datetime:
    """Convert Apple epoch timestamp to datetime."""
    if ts > 1e12:
        ts /= 1e9
    return MAC_EPOCH + timedelta(seconds=ts)


def get_latest_message_from_them(retry_limit: int | None = 5, delay: float = 1.0):
    attempt = 0
    while retry_limit is None or attempt < retry_limit:
        attempt += 1
        try:
            with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    """
                    SELECT ROWID, text, handle_id, is_from_me, date
                    FROM message
                    WHERE is_from_me = 0
                    ORDER BY ROWID DESC
                    LIMIT 1
                    """
                ).fetchone()

                if not row:
                    return None

                return {
                    "rowid": row["ROWID"],
                    "text": row["text"] or "",
                    "sender_type": "Them",
                    "handle_id": row["handle_id"],
                    "timestamp": apple_time_to_dt(row["date"]),
                }

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


def process_message(msg: dict):
    """Extract 2FA codes and copy to clipboard."""
    text = msg["text"]

    if not KEYWORD_REGEX.search(text):
        return

    match = CODE_REGEX.search(text)
    if not match:
        return

    code = match.group()
    pyperclip.copy(code)

    logger.info(
        "2FA code detected [%s]: %s",
        msg["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
        code,
    )


def main():
    logger.info("Listening for Messages events (event-based)")
    logger.info("Press Ctrl+C to exit")

    # Initialize with current latest message to avoid reprocessing old messages
    # Use infinite retries on startup because this is required to continue
    initial_msg = get_latest_message_from_them(retry_limit=None)
    # Shift initial last_rowid back by one to force the first read on startup to be seen as a fresh message
    last_rowid = initial_msg["rowid"] - 1 if initial_msg else 0
    logger.info("Successfully read from Messages database")

    proc = subprocess.Popen(
        LOG_CMD,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    def shutdown(_sig, _frame):
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    for line in proc.stdout:
        # Ignore log stream headers
        if "SMSReceivedRelayMessage" not in line:
            continue

        msg = get_latest_message_from_them()

        # Retry until receive fresh message
        while not msg or msg["rowid"] <= last_rowid:
            logger.info("Waiting for fresh message in database")
            time.sleep(0.1)
            msg = get_latest_message_from_them()

        last_rowid = msg["rowid"]
        process_message(msg)


if __name__ == "__main__":
    main()
