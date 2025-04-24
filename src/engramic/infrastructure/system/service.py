# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import threading
import uuid
from abc import ABC, abstractmethod
from concurrent.futures import Future
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar

import zmq
import zmq.asyncio

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from engramic.core.host import Host

T = TypeVar('T', bound=Enum)


class Service(ABC):
    class Topic(Enum):
        ENGRAMIC_SHUTDOWN = 'engramic_shutdown'
        SUBMIT_PROMPT = 'submit_prompt'
        RETRIEVE_COMPLETE = 'retrieve_complete'
        MAIN_PROMPT_COMPLETE = 'main_prompt_complete'
        START_PROFILER = 'start_profiler'
        END_PROFILER = 'end_profiler'
        OBSERVATION_COMPLETE = 'end_codify'
        ENGRAM_COMPLETE = 'engram_complete'
        META_COMPLETE = 'meta_complete'
        INDEX_COMPLETE = 'index_complete'
        ACKNOWLEDGE = 'acknowledge'
        STATUS = 'status'
        SET_TRAINING_MODE = 'set_training_mode'
        DEBUG_OBSERVATION_TOML_COMPLETE = 'debug_engram_complete'
        DEBUG_CONVERSATION_DIRECTION = 'debug_conversation_direction'
        DEBUG_ASK_CREATED = 'debug_ask_created'
        DEBUG_ASK_INDICES = 'debug_ask_indices'
        DEBUG_ASK_META = 'debug_ask_meta'
        DEBUG_MAIN_PROMPT_INPUT = 'debug_main_prompt_input'

    def __init__(self, host: Host) -> None:
        self.id = str(uuid.uuid4())
        self.init_async_complete = False
        self.host = host
        self.subscriber_callbacks: dict[str, list[Callable[..., None]]] = {}
        self.context: zmq.asyncio.Context | None = None
        self.sub_socket: zmq.asyncio.Socket | None = None
        self.push_socket: zmq.asyncio.Socket | None = None
        self.recieved_stop_message = False
        self.cleanup_complete = threading.Event()

    def init_async(self) -> None:
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
        if self.__class__.__name__ != 'MessageService':
            self.background_future = self.run_background(self._listen_for_published_messages())
            self.background_future.add_done_callback(self.on_run_background_end)
        self.init_async_complete = True

    def validate_service(self) -> bool:
        validation = {}
        validation['network'] = (
            self.context is not None and self.sub_socket is not None and self.push_socket is not None
        )
        return validation['network']

    @abstractmethod
    def start(self) -> None:
        self.subscribe(Service.Topic.ENGRAMIC_SHUTDOWN, self.on_run_background_end)

    async def stop(self) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def run_task(self, async_coro: Awaitable[Any]) -> Future[None]:
        if inspect.iscoroutinefunction(async_coro):
            error = 'Coro must be an async function.'
            raise TypeError(error)

        result = self.host.run_task(async_coro)

        if not isinstance(result, Future):
            error = f'Expected Future[None], but got {type(result)}'
            raise TypeError(error)

        return result

    def run_tasks(self, async_coros: Sequence[Awaitable[Any]]) -> Future[Any]:
        if inspect.iscoroutinefunction(async_coros):
            error = 'Coro must be an async function.'
            raise TypeError(error)

        result = self.host.run_tasks(async_coros)

        if not isinstance(result, Future):
            error = f'Expected Future[None], but got {type(result)}'
            raise TypeError(error)

        return result

    def run_background(self, async_coro: Awaitable[None]) -> Future[Any]:
        if inspect.iscoroutinefunction(async_coro):
            error = 'Coro must be an async function.'
            raise TypeError(error)

        return self.host.run_background(async_coro)

    def on_run_background_end(self, fut: Future[Any]) -> None:
        result = fut.result()
        del result
        future = self.run_task(self.stop())

        def complete_on_run(future: Future[Any]) -> None:
            future.result()

            if self.sub_socket is not None:
                self.sub_socket.close()

            if self.push_socket is not None:
                self.push_socket.close()

            if self.context is not None:
                self.context.term()

            self.cleanup_complete.set()

            logging.debug('Cleanup complete event set.: %s', self.__class__.__name__)

        future.add_done_callback(complete_on_run)

    # when sending from a non-async context
    async def _send_message(self, topic: Enum, message: dict[Any, Any] | None = None) -> None:
        self.send_message_async(topic, message)

    # when sending from an async context
    def send_message_async(
        self, topic: Enum, message: dict[Any, Any] | None = None
    ) -> Awaitable[zmq.MessageTracker | None] | None:
        try:
            asyncio.get_running_loop()
        except RuntimeError as err:
            error = 'This method can only be called from an async context.'
            raise RuntimeError(error) from err

        try:
            if self.push_socket is not None:
                future = self.push_socket.send_multipart([
                    bytes(topic.value, encoding='utf-8'),
                    bytes(json.dumps(message), encoding='utf-8'),
                ])
                return future
            error = 'push_socket is not initialized before sending a message'
            raise RuntimeError(error)
        except zmq.ZMQError as e:
            logging.info('ZMQ socket closed or failed: %s', e)

        return None

    def subscribe(self, topic: Topic, no_async_callback: Callable[..., None]) -> None:
        def runtime_error(error: str) -> None:
            raise RuntimeError(error)

        if inspect.iscoroutinefunction(no_async_callback):
            error = 'Subscribe callback must not be async.'
            raise TypeError(error)

        if not self.init_async_complete:
            error = 'Cannot call subscribe until async is initialized.'
            raise RuntimeError(error)

        try:
            if topic.value not in self.subscriber_callbacks:
                self.subscriber_callbacks[topic.value] = []

            self.subscriber_callbacks[topic.value].append(no_async_callback)

            if self.sub_socket is not None:
                self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, topic.value)
            else:
                error = 'sub_socket is not initialized before subscribing to a topic'
                runtime_error(error)

        except Exception:
            logging.exception('Run task failed in service:subscribe')

    async def _listen_for_published_messages(self) -> None:
        """Continuously checks for incoming messages"""
        if self.sub_socket is None:
            error = 'sub_socket is not initialized before receiving messages'
            raise RuntimeError(error)
        try:
            while not self.recieved_stop_message:
                topic, message = await self.sub_socket.recv_multipart()
                decoded_topic = topic.decode()

                if decoded_topic == Service.Topic.ENGRAMIC_SHUTDOWN.value:
                    self.recieved_stop_message = True
                    logging.debug('shutdown recieved. %s', self.__class__.__name__)
                    continue

                decoded_message = json.loads(message.decode())

                for callbacks in self.subscriber_callbacks[decoded_topic]:
                    try:
                        callbacks(decoded_message)
                    except ValueError as e:
                        # logging.exception('Exception while listening to published message. TOPIC: %s', decoded_topic)
                        error = f'Runtime error: {e}'
                        raise RuntimeError(error) from e

        except asyncio.CancelledError:
            logging.info('Service listener shutdown. %s', self.__class__.__name__)

        except zmq.ZMQError as e:
            logging.info('ZMQ socket closed or failed: %s (ok during shutdown)', e)

        logging.debug('_listen_for_published_messages exited: %s', self.__class__.__name__)
