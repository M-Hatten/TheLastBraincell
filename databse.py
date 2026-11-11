
import sqlite3
from pathlib import Path

# Store the database beside this Python file.
DB_PATH = Path(__file__).with_name("game.db")


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


def save_player(client_id, name):
    # Add a new player or update an existing player's name.
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            INSERT INTO players (client_id, name)
            VALUES (?, ?)
            ON CONFLICT(client_id)
            DO UPDATE SET name = excluded.name
        """, (client_id, name))


def add_point(client_id):
    # Increase a player's score by one.
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            UPDATE players
            SET score = score + 1
            WHERE client_id = ?
        """, (client_id,))


def get_leaderboard():
    # Retrieve players ordered by highest score.
    with sqlite3.connect(DB_PATH) as connection:
        return connection.execute("""
            SELECT client_id, name, score
            FROM players
            ORDER BY score DESC
        """).fetchall()


def clear_database():
    # Delete all player records while keeping the database structure.
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("DELETE FROM players")
