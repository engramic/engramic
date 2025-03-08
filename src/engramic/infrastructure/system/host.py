# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
import threading
from engramic.infrastructure.engram_profiles import EngramProfiles
from engramic.infrastructure.system.service import Service
from engramic.infrastructure.system.plugin_manager import PluginManager

class Host:
    def __init__(self, service_list:list[Service],selected_profile:str) -> None:
        """Initialize the host with an empty service list."""
        self.services = service_list
        self.plugin_manager = PluginManager()
        self.profile = EngramProfiles()

        profile = self.profile.get_profile(selected_profile)
        self.plugin_manager.install_dependencies(profile)

        for service in self.services:
            service.start()
        self.stop_event = threading.Event()

    def stop_all(self) -> None:
        """Stop all running services."""
        for service in self.services:
            service.stop()

    def wait_for_shutdown(self) -> None:
        try:
            self.stop_event.wait()  # This blocks until the event is set
        except KeyboardInterrupt:
            logging.info('\nShutdown requested. Exiting gracefully...')
        finally:
            logging.info('Cleaning up.')
