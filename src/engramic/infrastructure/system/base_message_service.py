# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import asyncio
import json
import logging
from concurrent.futures import Future
from enum import Enum
from typing import Any

import zmq
import zmq.asyncio

from engramic.core.host import Host
from engramic.core.metrics_tracker import MetricsTracker
from engramic.infrastructure.system import Service


class MessageMetric(Enum):
    MESSAGE_RECIEVED = 'message_recieved'
    MESSAGE_SENT = 'message_sent'


class BaseMessageService(Service):
    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.metrics_tracker: MetricsTracker[MessageMetric] = MetricsTracker[MessageMetric]()

    def init_async(self) -> None:
        super().init_async()
        self.pub_pull_context = zmq.asyncio.Context()
        self.pull_socket = self.pub_pull_context.socket(zmq.PULL)
        try:
            self.pull_socket.bind('tcp://*:5556')
        except zmq.error.ZMQError as err:
            logging.exception('Address 5556 in use. Is another instance running?')
            error = 'Failed to bind socket'
            raise OSError(error) from err

        self.pub_socket = self.pub_pull_context.socket(zmq.PUB)

        try:
            self.pub_socket.bind('tcp://127.0.0.1:5557')
        except zmq.error.ZMQError as err:
            logging.exception('Address 5557 in use. Is another instance running?')
            error = 'Failed to bind socket'
            raise OSError(error) from err

        self.listen_future = self.run_background(self.listen_for_push_messages())
        self.listen_future.add_done_callback(self._on_complete_listener)

    def shutdown(self) -> None:
        async def send_message() -> None:
            if self.push_socket is not None:
                await self.push_socket.send_multipart([
                    bytes(Service.Topic.ENGRAMIC_SHUTDOWN.value, encoding='utf-8'),
                    bytes(json.dumps({'shutdown': True}), encoding='utf-8'),
                ])

        self.run_task(send_message())

    def _on_complete_listener(self, future: Future[Any]) -> None:
        wait = future.result()
        del wait
        self.pub_socket.close(linger=0)
        self.pull_socket.close(linger=0)
        self.pub_pull_context.term()

        # base class sockets
        if self.sub_socket is not None:
            self.sub_socket.close()

        if self.push_socket is not None:
            self.push_socket.close()

        if self.context is not None:
            self.context.term()

        logging.debug('Message service sockets closed.')
        self.cleanup_complete.set()
        self.host.trigger_stop_event()

    async def listen_for_push_messages(self) -> None:
        try:
            """Continuously checks for incoming messages"""
            while not self.recieved_stop_message:
                topic, message = await self.pull_socket.recv_multipart()
                self.metrics_tracker.increment(MessageMetric.MESSAGE_RECIEVED)
                await self.pub_socket.send_multipart([topic, message])
                if topic == b'engramic_shutdown':
                    logging.debug('shutdown recieved message service')
                    self.recieved_stop_message = True
                self.metrics_tracker.increment(MessageMetric.MESSAGE_SENT)
        except asyncio.CancelledError:
            logging.info('Base messages shutting down.')
        except zmq.ZMQError as e:
            logging.info('ZMQ socket closed or failed: %s (ok during shutdown)', e)

        logging.debug('Shut down message=============================')
