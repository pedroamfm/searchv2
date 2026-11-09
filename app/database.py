"""SQLite connection and transaction helpers for application code."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def connect_database(path: Path, *, read_only: bool = False) -> sqlite3.Connection:
    """Open one configured SQLite unit-of-work connection."""
    if read_only:
        target = f"file:{path.resolve()}?mode=ro"
        connection = sqlite3.connect(target, uri=True, timeout=5)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    # SQLite's built-in lower() is ASCII-only. Search terms are user-facing
    # Spanish text, so use Python's Unicode-aware case folding consistently.
    connection.create_function("CASEFOLD", 1, lambda value: str(value).casefold() if value is not None else "")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    if not read_only:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
    return connection


@contextmanager
def database_connection(path: Path, *, read_only: bool = True) -> Iterator[sqlite3.Connection]:
    connection = connect_database(path, read_only=read_only)
    try:
        yield connection
        if not read_only:
            connection.commit()
    except Exception:
        if not read_only:
            connection.rollback()
        raise
    finally:
        connection.close()
