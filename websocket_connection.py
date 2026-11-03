'''
Sean M Roberts Jr

can testrun with "uvicorn main:app --reload"
-- reload means the server automatically refreshes when file edits are made

to run on local machine, make sure to install Uvicorn, FastAPI, etc. according to local machine specifications

Description:
A working skeleton and proof-of-concept for a websocket creation and management class, along with a FastAPI app, 
to keep track of individual user sessions when they connect to the python program.

Clients that connect see a placeholder HTML page, their own client ID, and other clients that are connected
(later, these IDs will be hidden, and only used by the backend)
'''

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uuid

app = FastAPI()


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
            const protocol =
                location.protocol === "https:" ? "wss:" : "ws:";

            const socket = new WebSocket(
                protocol + "//" + location.host + "/ws"
            );

            socket.onmessage = function(event) {
                const message = JSON.parse(event.data);

                if (message.type === "welcome") {
                    document.getElementById("client_id")
                        .textContent = message.client_id;
                }

                if (message.type === "connections_updated") {
                    const list =
                        document.getElementById("connections");

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

            socket.onclose = function() {
                document.getElementById("client_id")
                    .textContent = "Disconnected";
            };
        </script>
    </body>
    </html>
    """



class Connection:
    ''' Class to keep track of one individual websocket connection

    Has three elements:
    - self.websocket = websocket object 
    - self.name = string representing the name of the connected client
    - self.client_id = a unique uuid string generated on init to represent the client connection

    Has the following functions:
    - set_name(self, name) = set the name of the connection
    - get_client_id(self) = return the client uuid
    '''
    def __init__(self, ws: WebSocket):
        self.websocket = ws
        self.name = None
        self.client_id = str(uuid.uuid4())

    def set_name(self, new_name):
        self.name = new_name

    def get_client_id(self):
        return self.client_id




class WebsocketManager:
    ''' Class to keep track of multiple websockets at once, in a list of active connections, and broadcast to all of them
    
    Has only one element:
    - self.active_connections = a list of Connection objects that are active (i.e. have connected and have not yet disconnected)

    Has the following functions:
    '''

    def __init__(self):
        self.active_connections: list[Connection] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

        connection = Connection(websocket)
        self.active_connections.append(connection)

        return connection

    def get_connection(self, websocket: WebSocket):
        for connection in self.active_connections:
            if connection.websocket is websocket:
                return connection

        return None

    def disconnect(self, websocket: WebSocket):
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
        return [
            {
                "client_id": connection.client_id,
                "name": connection.name
            }
            for connection in self.active_connections
        ]

    async def broadcast_connections(self):
        message = {
            "type": "connections_updated",
            "clients": self.get_active_clients()
        }

        for connection in self.active_connections[:]:
            try:
                await connection.websocket.send_json(message)
            except Exception:
                pass




socket_manager = WebsocketManager()

message = {"Placeholder for main.py"}

# app decorator defines the path for the HTTP get method, gets the root
@app.get("/")
def root():
    return HTMLResponse(placeholder_html) # return placeholder HTML


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    connection = await socket_manager.connect(websocket)

    print(f"Connected: {connection.client_id}")

    try:
        # Tell the client its own ID
        await websocket.send_json({
            "type": "welcome",
            "client_id": connection.client_id
        })

        # Tell everyone about the new connection
        await socket_manager.broadcast_connections()

        # Keep listening until the client disconnects (allows updates to be seen)
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        print(f"Disconnected: {connection.client_id}")

    finally:
        socket_manager.disconnect(websocket)
        await socket_manager.broadcast_connections()

