
"""
Continuation of the WebSocket connection management proof of concept.

Run locally with:
    uvicorn main:app --reload

Each browser tab receives a session UUID that survives page refreshes.
Active connections are broadcast to all connected browsers.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uuid

app = FastAPI()


# Placeholder webpage for displaying session IDs and active connections.
placeholder_html = """
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Connections</title>
</head>

<body>
    <h1>WebSocket Connection Test</h1>

    <h2>Your Client ID:</h2>
    <p id="client_id">Connecting...</p>

    <h2>Active Connections:</h2>
    <ul id="connections"></ul>

    <script>
        // Retrieve this tab's previous UUID, if one exists.
        let client_id = sessionStorage.getItem("client_id");

        // Connect to the FastAPI WebSocket endpoint.
        const protocol =
            location.protocol === "https:" ? "wss:" : "ws:";

        const socket = new WebSocket(
            protocol + "//" + location.host + "/ws"
        );

        // Identify this browser session when the connection opens.
        socket.onopen = function() {
            socket.send(JSON.stringify({
                type: "identify",
                client_id: client_id
            }));
        };

        // Process messages sent by the FastAPI server.
        socket.onmessage = function(event) {
            const message = JSON.parse(event.data);

            // Remember the UUID so refreshing preserves the session.
            if (message.type === "welcome") {
                client_id = message.client_id;
                sessionStorage.setItem("client_id", client_id);

                document.getElementById("client_id")
                    .textContent = client_id;
            }

            // Replace the displayed list with the latest connections.
            if (message.type === "connections_updated") {
                const list = document.getElementById("connections");
                list.replaceChildren();

                message.clients.forEach(client => {
                    const item = document.createElement("li");

                    item.textContent =
                        client.client_id +
                        " | Name: " + (client.name ?? "None");

                    list.appendChild(item);
                });
            }
        };

        // Indicate when this browser loses its WebSocket connection.
        socket.onclose = function() {
            document.getElementById("client_id")
                .textContent = "Disconnected";
        };
    </script>
</body>
</html>
"""


class Connection:
    """Stores the WebSocket, name, and UUID of one client."""

    def __init__(self, ws: WebSocket, client_id=None):
        self.websocket = ws
        self.name = None

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
        # Accept the WebSocket and wait for the browser's session ID.
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

        connection = Connection(websocket, client_id)

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


socket_manager = WebsocketManager()


@app.get("/")
def root():
    # Serve the placeholder webpage directly from FastAPI.
    return HTMLResponse(placeholder_html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    connection = None

    try:
        # Establish a connection and recover the browser's session UUID.
        connection = await socket_manager.connect(websocket)

        if connection is None:
            return

        print(f"Connected: {connection.client_id}")

        # Tell this browser which UUID represents its session.
        await websocket.send_json({
            "type": "welcome",
            "client_id": connection.client_id
        })

        # Notify all connected browsers about the updated list.
        await socket_manager.broadcast_connections()

        # Keep receiving messages until the WebSocket disconnects.
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        if connection is not None:
            print(f"Disconnected: {connection.client_id}")

    finally:
        # Remove this WebSocket and notify the remaining clients.
        if connection is not None:
            socket_manager.disconnect(websocket)
            await socket_manager.broadcast_connections()
