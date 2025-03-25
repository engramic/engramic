# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

import time
from enum import Enum
from threading import Lock
from typing import Generic, TypedDict, TypeVar

# Define a TypeVar bound to Enum
T = TypeVar('T', bound=Enum)


# Packet format
class MetricPacket(TypedDict):
    timestamp: float
    metrics: dict[str, int]  # String keys for serialization


# Generic tracker class
class MetricsTracker(Generic[T]):
    def __init__(self) -> None:
        self._lock: Lock = Lock()
        self._counters: dict[T, int] = {}
        self._last_sent: float | None = 0.0

    def increment(self, metric: T, amount: int = 1) -> None:
        with self._lock:
            self._counters[metric] = self._counters.get(metric, 0) + amount

    def get_and_reset_packet(self) -> MetricPacket:
        with self._lock:
            packet: MetricPacket = {
                'timestamp': time.time(),
                'metrics': {metric.name: count for metric, count in self._counters.items()},
            }
            self._counters.clear()
            self._last_sent = time.time()
            return packet

    def has_data(self) -> bool:
        with self._lock:
            return bool(self._counters)

    def time_since_last_send(self) -> float | None:
        if self._last_sent is None:
            return None
        return time.time() - self._last_sent
