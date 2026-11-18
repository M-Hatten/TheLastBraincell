"""
Connecting disparate work into one unit.

Needs to be run from a virtual environment.
-- make directory for virtual env
python3 -m venv .venv
source .venv/bin/activate
-- install required packages to venv (if you don't have them already)
python -m pip install fastapi "uvicorn[standard]"
-- Run venv locally with:
    python -m uvicorn main:app --reload

Each browser tab receives a session UUID and name that survive page refreshes.
Active connections are broadcast to all connected browsers.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uuid
# Use a monotonic clock for server-enforced per-player cooldowns.
import time
# Run the weekly reset task while the FastAPI application is running.
import asyncio
from contextlib import asynccontextmanager, suppress

# Pull the database operations and board logic from their own files.
from database import initialize_database, save_player, add_point, get_leaderboard, reset_if_due
from boardflash import Board

# Development switch: False enforces the normal five-second click cooldown.
DEBUG = False


# Create the single-process application and initialize persistent storage.
# The background task starts with FastAPI and stops cleanly on shutdown.
@asynccontextmanager
async def lifespan(app):
    initialize_database()
    # If the server missed a Sunday reset, apply it before accepting players.
    reset_if_due()
    task = asyncio.create_task(weekly_reset_loop())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(lifespan=lifespan)

# Serve the CSS file from the static directory.
STATIC_PATH = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")

# Keep one shared board for all connected browsers.
board = Board()
# Remember the winner until the server starts the next round.
round_winner_id = None
# Keep the server-owned reset task from being garbage collected.
round_reset_task = None
INDEX_PATH = Path(__file__).with_name("index.html")


class Connection:
    """Stores the WebSocket, name, and UUID of one client."""

    def __init__(self, ws: WebSocket, client_id=None, name=None):
        self.websocket = ws

        # Restore the previous name or use None for a new client.
        self.name = name

        # Reuse a session UUID or generate one for a new session.
        self.client_id = (
            client_id if client_id is not None
            else str(uuid.uuid4())
        )

    def set_name(self, new_name):
        self.name = new_name

    def get_client_id(self):
        return self.client_id


class WebsocketManager:
    """Tracks active connections and broadcasts updates to clients."""

    def __init__(self):
        self.active_connections: list[Connection] = []

    async def connect(self, websocket: WebSocket):
        # Accept the WebSocket and wait for the browser's session details.
        await websocket.accept()
        message = await websocket.receive_json()

        if message.get("type") != "identify":
            await websocket.close(code=1008)
            return None

        client_id = message.get("client_id")

        # Accept a previously issued UUID or generate a new one.
        if not isinstance(client_id, str):
            client_id = None
        else:
            try:
                client_id = str(uuid.UUID(client_id))
            except ValueError:
                client_id = None

        # Retrieve the previously submitted name from the browser.
        name = message.get("name")

        # Accept only valid, nonempty names.
        if not isinstance(name, str) or not name.strip():
            name = None
        else:
            name = name.strip()

        # Create a connection using the previous UUID and name.
        connection = Connection(websocket, client_id, name)

        # Remove any older active connection using this UUID.
        old_connection = self.get_connection_by_id(connection.client_id)

        if old_connection is not None:
            self.active_connections.remove(old_connection)

            try:
                await old_connection.websocket.close()
            except Exception:
                pass

        # Add the newly established connection to the active list.
        self.active_connections.append(connection)

        return connection

    def get_connection(self, websocket: WebSocket):
        # Find a Connection using its exact WebSocket object.
        for connection in self.active_connections:
            if connection.websocket is websocket:
                return connection
        return None

    def get_connection_by_id(self, client_id: str):
        # Find a Connection using its session UUID.
        for connection in self.active_connections:
            if connection.client_id == client_id:
                return connection
        return None

    def disconnect(self, websocket: WebSocket):
        # Remove only the Connection associated with this WebSocket.
        connection = self.get_connection(websocket)
        if connection is not None:
            self.active_connections.remove(connection)

    def get_name(self, websocket: WebSocket):
        # Get the name of an individual connection.
        connection = self.get_connection(websocket)
        if connection is not None:
            return connection.name
        return None

    def set_name(self, websocket: WebSocket, name: str):
        # Set the name of an individual connection.
        connection = self.get_connection(websocket)
        if connection is not None:
            connection.set_name(name)

    def get_active_clients(self):
        # Return serializable client information, not WebSocket objects.
        return [
            {"client_id": connection.client_id, "name": connection.name}
            for connection in self.active_connections
        ]

    async def broadcast_connections(self):
        # Send the latest active connection list to every client.
        message = {
            "type": "connections_updated",
            "clients": self.get_active_clients()
        }
        for connection in self.active_connections[:]:
            try:
                await connection.websocket.send_json(message)
            except Exception:
                # A disconnected client's endpoint handles cleanup.
                pass

    async def broadcast_board(self, state):
        # Show every player the same board after a click or reset.
        message = {"type": "board_updated", **state}
        for connection in self.active_connections[:]:
            try:
                await connection.websocket.send_json(message)
            except Exception:
                pass

    async def broadcast_leaderboard(self):
        # Read persistent scores and send the leaderboard to all players.
        players = [
            {"client_id": client_id, "name": name, "score": score}
            for client_id, name, score in get_leaderboard()
        ]
        message = {"type": "leaderboard_updated", "players": players}
        for connection in self.active_connections[:]:
            try:
                await connection.websocket.send_json(message)
            except Exception:
                pass


socket_manager = WebsocketManager()


async def broadcast_game_results(winner_id):
    # Send each connected browser its own result using its session UUID.
    for player in socket_manager.active_connections[:]:
        try:
            await player.websocket.send_json({
                "type": "game_result",
                "result": "win" if player.client_id == winner_id else "lose"
            })
        except Exception:
            # Disconnected clients are cleaned up by their WebSocket endpoints.
            pass


async def reset_round_after_delay():
    global round_winner_id, round_reset_task
    # Give players two seconds to see their result before a new round begins.
    await asyncio.sleep(2)
    board.reset()
    round_winner_id = None
    round_reset_task = None
    # The next board update clears the result on every browser.
    await socket_manager.broadcast_board(board.state())

# Track each session's last accepted pixel click across WebSocket reconnects.
CLICK_COOLDOWN_SECONDS = 5
last_click_times = {}



async def weekly_reset_loop():
    # Check the Sunday 8:00 AM boundary every second while the server is running.
    while True:
        await asyncio.sleep(1)
        if reset_if_due():
            # Restore currently connected identities with zero scores after the wipe.
            for player in socket_manager.active_connections[:]:
                if player.name:
                    save_player(player.client_id, player.name)
            # Show the reset leaderboard immediately to every connected browser.
            await socket_manager.broadcast_leaderboard()


@app.get("/")
def root():
    # Serve the game page (replaced placeholder from previous iterations).
    return FileResponse(INDEX_PATH)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global round_winner_id, round_reset_task
    connection = None

    try:
        # Establish a connection and recover the browser's session details.
        connection = await socket_manager.connect(websocket)

        if connection is None:
            return

        print(f"Connected: {connection.client_id}")

        # Save the player's UUID and name without overwriting their score.
        if connection.name:
            save_player(connection.client_id, connection.name)

        # Tell this browser which UUID represents its session.
        await websocket.send_json({
            "type": "welcome",
            "client_id": connection.client_id
        })

        # Send the current shared board, connections, and saved scores.
        await websocket.send_json({"type": "board_updated", **board.state()})
        # A player reconnecting during the result screen sees the correct outcome.
        if board.remaining == 0 and round_winner_id is not None:
            await websocket.send_json({
                "type": "game_result",
                "result": "win" if connection.client_id == round_winner_id else "lose"
            })
        await socket_manager.broadcast_connections()
        await socket_manager.broadcast_leaderboard()

        # Listen for messages from the connected browser.
        while True:
            message = await websocket.receive_json()

            # Update the user's name when a name submission is received.
            if message.get("type") == "set_name":
                name = message.get("name")

                # Accept only nonempty strings as display names.
                if isinstance(name, str) and name.strip():
                    socket_manager.set_name(websocket, name.strip())

                    # Persist the new name without resetting the score.
                    save_player(connection.client_id, name.strip())

                    # Broadcast the updated names and leaderboard.
                    await socket_manager.broadcast_connections()
                    await socket_manager.broadcast_leaderboard()

            # Process valid clicks on the single shared board.
            elif message.get("type") == "click":
                square = message.get("square")
                # Require a saved name and enforce the cooldown on the server.
                now = time.monotonic()
                previous_click = last_click_times.get(connection.client_id, float("-inf"))
                if not connection.name:
                    await websocket.send_json({"type": "click_rejected", "reason": "Enter and save a name first."})
                elif not DEBUG and now - previous_click < CLICK_COOLDOWN_SECONDS:
                    await websocket.send_json({
                        "type": "click_rejected",
                        "reason": "Wait before clicking another pixel.",
                        "remaining": round(CLICK_COOLDOWN_SECONDS - (now - previous_click), 1)
                    })
                elif type(square) is int and board.click(square):
                    # Only successful clicks start the five-second cooldown.
                    if not DEBUG:
                        last_click_times[connection.client_id] = now
                    # Tell the browser to skip its local cooldown in debug mode.
                    await websocket.send_json({"type": "click_accepted", "cooldown": 0 if DEBUG else CLICK_COOLDOWN_SECONDS})
                    # Award a persistent point to the final square's clicker.
                    if board.remaining == 0:
                        # Record the UUID of the player who removed the final pixel.
                        round_winner_id = connection.client_id
                        add_point(connection.name)
                        await socket_manager.broadcast_leaderboard()

                    await socket_manager.broadcast_board(board.state())

                    if board.remaining == 0:
                        # Send the winner and all other players personalized messages.
                        await broadcast_game_results(round_winner_id)
                        # Reset on the server, even if the winning browser disconnects.
                        round_reset_task = asyncio.create_task(reset_round_after_delay())


    except WebSocketDisconnect:
        if connection is not None:
            print(f"Disconnected: {connection.client_id}")

    finally:
        # Remove this WebSocket and notify the remaining clients.
        if connection is not None:
            socket_manager.disconnect(websocket)
            await socket_manager.broadcast_connections()
