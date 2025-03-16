# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.


import websockets
from engramic.core.host import Host


class WebsocketManager():
    def __init__(self,host:Host):
        self.websocket = None
        self.host = host

    def init_async(self):
        self.host.run_background(self.run_server())

    async def run_server(self):
        self.websocket = await websockets.serve(self.handler, "localhost", 8765)
        await self.websocket.wait_closed()

    async def handler(self, websocket):
        self.active_connections = websocket
        
        try:
            # Listen for incoming messages
            async for message in websocket:
                print("Received:", message)

        except websockets.exceptions.ConnectionClosed:
            print("Client disconnected")
        finally:
            self.active_connections = None

    async def message_task(self,message):
            await self.active_connections.send(str(message.packet))

    def send_message(self, message):
            self.host.run_task(self.message_task(message))
