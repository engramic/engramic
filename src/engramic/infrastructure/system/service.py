# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import asyncio
import json
from concurrent.futures import Future
from enum import Enum

import zmq
import zmq.asyncio


class Service:
    class Topic(Enum):
        RETRIEVE_COMPLETE = 'retrieve_complete'

    def __init__(self, host):
        self.host = host
        self.subscriber_callbacks = {}
        self.context = None
        self.sub_socket = None
        self.push_socket = None

    def init_async(self):
        try:
            asyncio.get_running_loop()
        except RuntimeError as err:
            error = 'This method can only be called from an async context.'
            raise RuntimeError(error) from err

        self.context = zmq.asyncio.Context()
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect('tcp://127.0.0.1:5557')
        self.push_socket = self.context.socket(zmq.PUSH)
        self.push_socket.connect('tcp://127.0.0.1:5556')
        self._run_background(self._listen_for_messages())

    def validate(self):
        validation = {}
        validation['network'] = (
            self.context is not None and self.sub_socket is not None and self.push_socket is not None
        )
        return validation['network']

    def stop(self):
        self.sub_socket.close()
        self.push_socket.close()
        self.context.term()

    def run_task(self, coro) -> Future:
        return self.host.run_task(coro)

    def run_tasks(self, coros) -> Future:
        return self.host.run_tasks(coros)

    def _run_background(self, coro):
        self.host.run_background(coro)

    def send_message_async(self, topic, message):
        try:
            asyncio.get_running_loop()
        except RuntimeError as err:
            error = 'This method can only be called from an async context.'
            raise RuntimeError(error) from err

        self.push_socket.send_multipart([
            bytes(topic.value, encoding='utf-8'),
            bytes(json.dumps(message), encoding='utf-8'),
        ])

    def subscribe(self, topic: Topic, callback):
        async def subscribe_coro(topic):
            await self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, topic.value)

        if topic.value not in self.subscriber_callbacks:
            self.subscriber_callbacks[topic.value] = []

        self.subscriber_callbacks[topic.value].append(callback)

        self.run_task(subscribe_coro(topic))

    async def _listen_for_messages(self):
        """Continuously checks for incoming messages"""
        while True:
            topic, message = await self.sub_socket.recv_multipart()
            decoded_topic = topic.decode()
            decoded_message = json.loads(message.decode())

            for callbacks in self.subscriber_callbacks[decoded_topic]:
                await callbacks(decoded_message)
