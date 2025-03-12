# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
import threading
from typing import ClassVar

from engramic.infrastructure.system.plugin_manager import PluginManager
from engramic.infrastructure.system.service import Service


class Host:
    _services: ClassVar[dict[str, type[Service]]] = {}

    @staticmethod
    def register_service(cls_in: type[Service]):
        Host._services[cls_in.__name__] = cls_in

    def __init__(self, selected_profile: str) -> None:
        self.plugin_manager: PluginManager = PluginManager(selected_profile)
        self.services: dict[str, type[Service]] = {}

        for name in Host._services:
            class_ctr = Host._services[name]
            self.services[name] = class_ctr(self.plugin_manager)  # Instantiate the class
            self.services[name].start(self)

        self.stop_event: threading.Event = threading.Event()

    def get_service(self, cls_in: type[Service]) -> Service:
        name = cls_in.__name__
        if name in self.services:
            return self.services[name]
        return None

    def shutdown(self) -> None:
        """Stop all running services."""
        for service in self.services:
            self.services[service].stop()
        
        #host ready for shutdown
        self.stop_event.set()


    def wait_for_shutdown(self) -> None:
        try:
            self.stop_event.wait()  # This blocks until the event is set
        except KeyboardInterrupt:
            logging.info('\nShutdown requested. Exiting gracefully...')
        finally:
            logging.info('Cleaning up.')
