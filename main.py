
"""
Connecting disparate work into one unit.

Needs to be run from a virtual environment.
-- make directory for virtual env
python3 -m venv .venv
source .venv/bin/activate
-- activate virtual env
source .venv/bin/activate
-- install required packages to venv
python -m pip install fastapi "uvicorn[standard]"
-- Run venv locally with:
    python -m uvicorn main:app --reload

Each browser tab receives a session UUID and name that survive page refreshes.
Active connections are broadcast to all connected browsers.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pathlib import Path
from boardflash import Board
import uuid

app = FastAPI()

# Keep one shared board for all connected browsers.
board = Board()
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
        old_connection = self.get_connection_by_id(
            connection.client_id
        )

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
        connection = self.get_connection(websocket)

        if connection is not None:
            return connection.name

        return None

    def set_name(self, websocket: WebSocket, name: str):
        connection = self.get_connection(websocket)

        if connection is not None:
            connection.set_name(name)

    def get_active_clients(self):
        # Return serializable client information, not WebSocket objects.
        return [
            {
                "client_id": connection.client_id,
                "name": connection.name
            }
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


socket_manager = WebsocketManager()


@app.get("/")
def root():
    # Serve the game page rather than the old placeholder.
    return FileResponse(INDEX_PATH)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    connection = None

    try:
        # Establish a connection and recover the browser's session details.
        connection = await socket_manager.connect(websocket)

        if connection is None:
            return

        print(f"Connected: {connection.client_id}")

        # Tell this browser which UUID represents its session.
        await websocket.send_json({
            "type": "welcome",
            "client_id": connection.client_id
        })

        # Send the current shared board and connection list.
        await websocket.send_json({"type": "board_updated", **board.state()})
        await socket_manager.broadcast_connections()

        # Listen for messages from the connected browser.
        while True:
            message = await websocket.receive_json()

            # Update the user's name when a name submission is received.
            if message.get("type") == "set_name":
                name = message.get("name")

                # Accept only nonempty strings as display names.
                if isinstance(name, str) and name.strip():
                    socket_manager.set_name(websocket, name.strip())

                    # Broadcast the updated names to all connected clients.
                    await socket_manager.broadcast_connections()

            # Process valid clicks on the single shared board.
            elif message.get("type") == "click":
                square = message.get("square")
                if type(square) is int and board.click(square):
                    await socket_manager.broadcast_board(board.state())

            # Start a fresh round only after the last pixel is gone.
            elif message.get("type") == "reset":
                if board.remaining == 0:
                    board.reset()
                    await socket_manager.broadcast_board(board.state())

    except WebSocketDisconnect:
        if connection is not None:
            print(f"Disconnected: {connection.client_id}")

    finally:
        # Remove this WebSocket and notify the remaining clients.
        if connection is not None:
            socket_manager.disconnect(websocket)
            await socket_manager.broadcast_connections()
