# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import zmq
import zmq.asyncio
from engramic.infrastructure.system.service import Service


class BaseMessageService(Service):
    def __init__(self):
        self.pub_pull_context = zmq.asyncio.Context()
        self.pub_socket = self.pub_pull_context.socket(zmq.PUB)
        self.pub_socket.bind('tcp://127.0.0.1:5557')
        self.pull_socket = self.pub_pull_context.socket(zmq.PULL)
        self.pull_socket.bind('tcp://*:5556')

        super().__init__(self.listen_for_push_messages())

    def stop(self) -> None:
        self.pub_socket.close()
        self.pull_socket.close()
        self.pub_pull_context.term()
        super().stop()

    def publish_message(self, topic, message):
        async def send_message_coroutine():
            await self.pub_socket.send_multipart([topic, message])

        future = self.submit_async_tasks(send_message_coroutine())
        return future

    async def listen_for_push_messages(self):
        """Continuously checks for incoming messages"""
        while True:
            topic, message = await self.pull_socket.recv_multipart()
            self.publish_message(topic, message)
