# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from engramic.infrastructure.system.service import Service
from engramic.infrastructure.system.plugin_manager import PluginManager
from engramic.infrastructure.system.websocket_manager import WebsocketManager
from engramic.infrastructure.repository.EngramRepository import EngramRepository

from engramic.core import Prompt, Engram
import logging
import queue

class ResponseService(Service):

    def __init__(self,host):
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager
        self.web_socket_manager: WebsocketManager = host.web_socket_manager
        self.engram_repository:EngramRepository = EngramRepository(self.plugin_manager)
        self.llm_main = self.plugin_manager.get_plugin('llm', 'response_main')
        self.prompt = Prompt("Placeholder for prompt engineering for main prompt.")
        self.retrieve_complete_queue = queue.Queue()
        ##
        ## Many methods are not ready to be until their async component is running.
        ## Do not call async context methods in the constructor.
        

    def start(self):
        self.subscribe(Service.Topic.RETRIEVE_COMPLETE,self.on_retrieve_complete)

    def on_retrieve_complete(self,engram_ids):
        logging.info("on_retrieve_complete: %s",engram_ids)
        self.retrieve_complete_queue.put(engram_ids)

    def tokencallback(self,token):
        var = 0

    async def submit_llm(self):
        mock_response = self.llm_main["func"].submit_streaming(prompt=self.prompt,  args=self.llm_main['args'], websocket_manager = self.web_socket_manager )
        self.send_message_async(Service.Topic.MAIN_PROMPT_COMPLETE,mock_response)

    async def fetch_engrams(self,engram_ids):
        engram_array: list[Engram] = self.engram_repository.load_batch(engram_ids)
        #assembled main_prompt, render engrams.
        self.run_task(self.submit_llm())
        
    def update(self) -> None:

        while not self.retrieve_complete_queue.empty():
            engram_ids = self.retrieve_complete_queue.get()
            self.run_task(self.fetch_engrams(engram_ids))


        