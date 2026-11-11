
import sqlite3
# Track the Sunday reset in the configured local timezone.
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from pathlib import Path

# Store the database beside this Python file.
DB_PATH = Path(__file__).with_name("game.db")

# Weekly reset time; change this zone if your game uses a different timezone.
RESET_TIMEZONE = ZoneInfo("America/Chicago")


def initialize_database():
    # Create the players table if it doesn't exist.
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS players (
                client_id TEXT PRIMARY KEY,
                name TEXT,
                score INTEGER DEFAULT 0
            )
        """)
        # Consolidate old duplicate names and remove unnamed legacy records once.
        existing = connection.execute("SELECT client_id, name, score FROM players ORDER BY rowid").fetchall()
        merged = {}
        for client_id, name, score in existing:
            if not isinstance(name, str) or not name.strip():
                continue
            clean_name = name.strip()
            key = clean_name.casefold()
            if key in merged:
                merged[key][2] += score or 0
            else:
                merged[key] = [client_id, clean_name, score or 0]
        # Rebuild the rows in one transaction, retaining total points per name.
        connection.execute("DELETE FROM players")
        connection.executemany(
            "INSERT INTO players (client_id, name, score) VALUES (?, ?, ?)",
            merged.values()
        )
        # Enforce a single leaderboard row for each case-insensitive player name.
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_player_name ON players(name COLLATE NOCASE)")
        # Store the most recent completed weekly reset to avoid duplicate wipes.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        # On first setup, preserve existing scores until the NEXT Sunday reset.
        connection.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('last_weekly_reset', ?)
        """, (latest_reset_boundary(datetime.now(RESET_TIMEZONE)).isoformat(),))


def latest_reset_boundary(now):
    # Find the most recent Sunday at 8:00 AM in the configured timezone.
    sunday = now.date() - timedelta(days=(now.weekday() + 1) % 7)
    boundary = datetime.combine(sunday, time(8, 0), tzinfo=RESET_TIMEZONE)
    if now < boundary:
        boundary -= timedelta(days=7)
    return boundary


def reset_if_due(now=None):
    # Clear players once per Sunday boundary, including missed resets after downtime.
    now = now or datetime.now(RESET_TIMEZONE)
    boundary = latest_reset_boundary(now).isoformat()
    with sqlite3.connect(DB_PATH) as connection:
        # Keep the deletion and recorded reset in the same transaction.
        connection.execute("BEGIN IMMEDIATE")
        last_reset = connection.execute("""
            SELECT value FROM settings WHERE key = 'last_weekly_reset'
        """).fetchone()[0]
        if last_reset >= boundary:
            return False
        # Use the existing wipe function's SQL operation inside this transaction.
        clear_database(connection)
        connection.execute("""
            UPDATE settings SET value = ? WHERE key = 'last_weekly_reset'
        """, (boundary,))
        return True


def save_player(client_id, name):
    # Unnamed connections are not inserted into the leaderboard.
    if not isinstance(name, str) or not name.strip():
        return
    name = name.strip()
    with sqlite3.connect(DB_PATH) as connection:
        # A name already on the leaderboard retains its score and original row.
        existing = connection.execute(
            "SELECT client_id FROM players WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
        if existing:
            return
        # A changed name gets its own leaderboard row; old scores remain with the old name.
        # Use a new unique row ID if this session already has an entry under another name.
        row_id = client_id
        if connection.execute("SELECT 1 FROM players WHERE client_id = ?", (row_id,)).fetchone():
            import uuid
            row_id = str(uuid.uuid4())
        connection.execute(
            "INSERT INTO players (client_id, name, score) VALUES (?, ?, 0)",
            (row_id, name)
        )


def add_point(name):
    # Credit the existing name rather than creating another UUID-based entry.
    if not isinstance(name, str) or not name.strip():
        return
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "UPDATE players SET score = score + 1 WHERE name = ? COLLATE NOCASE",
            (name.strip(),)
        )


def get_leaderboard():
    # Retrieve players ordered by highest score.
    with sqlite3.connect(DB_PATH) as connection:
        return connection.execute("""
            SELECT client_id, name, score
            FROM players
            ORDER BY score DESC
        """).fetchall()


def clear_database(connection=None):
    # Delete all player records while keeping the database structure.
    if connection is not None:
        # Reuse the scheduler transaction so the wipe and timestamp commit together.
        connection.execute("DELETE FROM players")
    else:
        # Manual use remains possible; the scheduled task is the only automatic caller.
        with sqlite3.connect(DB_PATH) as database_connection:
            database_connection.execute("DELETE FROM players")
