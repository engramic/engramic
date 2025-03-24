# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from concurrent.futures import Future
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from engramic.core import Engram, Index, Meta, Prompt
from engramic.core.observation import Observation
from engramic.infrastructure.repository.observation_repository import ObservationRepository
from engramic.infrastructure.system.host import Host
from engramic.infrastructure.system.service import Service

if TYPE_CHECKING:
    from engramic.infrastructure.system.plugin_manager import PluginManager


class ConsolidateService(Service):
    def __init__(self, host: Host) -> None:
        super().__init__(host)
        self.plugin_manager: PluginManager = host.plugin_manager
        self.llm_summary: dict[str, Any] = self.plugin_manager.get_plugin('llm', 'summary')
        self.llm_gen_indices: dict[str, Any] = self.plugin_manager.get_plugin('llm', 'gen_indices')
        self.embedding_gen_embed: dict[str, Any] = self.plugin_manager.get_plugin('embedding', 'gen_embedding')
        self.observation_repository = ObservationRepository(self.plugin_manager)
        self.engram_builder: dict[str, Engram] = {}
        self.index_builder: dict[str, Index] = {}

    def start(self) -> None:
        self.subscribe(Service.Topic.OBSERVATION_COMPLETE, self.on_observer_complete)

    def on_observer_complete(self, observation_dict: dict[str, Any]) -> None:
        """
        Callback invoked once an observation is complete.
        We run summary + engram pipeline tasks asynchronously.
        """
        observation = self.observation_repository.load_dict(observation_dict)

        summary_observation = self.run_task(self.generate_summary(observation))
        summary_observation.add_done_callback(self.on_summary)

        generate_engrams = self.run_task(self.generate_engrams(observation))
        generate_engrams.add_done_callback(self.on_engrams)

    async def generate_summary(self, observation: Observation) -> Meta:
        """
        Asynchronously call your LLM to create a summary of the observation.
        """
        prompt = Prompt('Make me a summary')
        args = self.llm_summary['args']
        args.update({'observation': observation.render()})
        summary = self.llm_summary['func'].submit(prompt=prompt, args=args)
        observation.meta.summary_full = summary
        return observation.meta

    def on_summary(self, summary_fut: Future[Any]) -> None:
        """Callback after `generate_summary` completes."""
        result = summary_fut.result()
        self.send_message_async(Service.Topic.META_COMPLETE, asdict(result))

    async def generate_engrams(self, observation: Observation) -> list[Engram]:
        """
        Will procedurally generate engrams from other elements in an observation.
        """
        return observation.engram_list

    def on_engrams(self, engram_list_fut: Future[Any]) -> None:
        """
        Called after generate_engrams(...) is done.
        We next need to:
           (1) Generate indices for each engram
           (2) Then generate embeddings for all indices
           (3) Only then publish engram_complete
        """
        engram_list = engram_list_fut.result()

        # Keep references so we can fill them in later
        for engram in engram_list:
            if self.engram_builder.get(engram.id) is None:
                self.engram_builder[engram.id] = engram
            else:
                error = 'Engram ID Collision. During conslidation, two Engrams with the same IDs were detected.'
                raise RuntimeError(error)

        # 1) Generate indices for each engram
        index_tasks = [self.gen_indices(engram.id, engram.render()) for engram in engram_list]
        indices_future = self.run_tasks(index_tasks)

        # Once all indices are generated, generate embeddings
        def on_indices_done(indices_list_fut: Future[Any]) -> None:
            # This is the accumulated result of each gen_indices(...) call
            indices_list: dict[str, Any] = indices_list_fut.result()
            # indices_list should have a key like 'gen_indices' -> list[dict[str, Any]]
            index_sets: list[dict[str, Any]] = indices_list['gen_indices']

            # 2) Generate embeddings for each index set
            embed_tasks = [self.gen_embeddings(index_set) for index_set in index_sets]
            embed_future = self.run_tasks(embed_tasks)

            # Once embeddings are generated, then we're truly done
            def on_embeddings_done(embed_fut: Future[Any]) -> None:
                ret = embed_fut.result()  # ret should have 'gen_embeddings' -> list of engram IDs
                ids = ret['gen_embeddings']  # which IDs got their embeddings updated

                # 3) Now that embeddings exist, we can send "ENGRAM_COMPLETE" for each
                for eid in ids:
                    engram = self.engram_builder[eid]
                    self.send_message_async(Service.Topic.ENGRAM_COMPLETE, asdict(engram))
                    del self.engram_builder[eid]

            embed_future.add_done_callback(on_embeddings_done)

        indices_future.add_done_callback(on_indices_done)

    async def gen_indices(self, id_in: str, engram_render: str) -> dict[str, Any]:
        """Generate the 'indices' for one engram via an LLM plugin."""
        del engram_render  # not used in your snippet, but presumably in the future
        prompt = Prompt('Generate indicies.')
        args = self.llm_gen_indices['args']
        indices = self.llm_gen_indices['func'].submit(prompt=prompt, args=args)
        return {'id': id_in, 'indices': indices[0]['llm_response']}

    async def gen_embeddings(self, id_and_index_dict: dict[str, Any]) -> str:
        """
        Called after `gen_indices`; now we have the engram ID plus the new indices to embed.
        """
        indices = id_and_index_dict['indices']
        id_val: str = id_and_index_dict['id']

        prompt = Prompt('Generate embeddings.')
        args = self.embedding_gen_embed['args']
        embedding = self.embedding_gen_embed['func'].gen_embed(prompt=prompt, indices=indices, args=args)

        # Convert raw embeddings to Index objects and attach them
        index_array: list[Index] = []
        for i, vec in enumerate(embedding[0]['embedding_response']):
            index = Index(vec, indices[i])
            index_array.append(index)

        self.engram_builder[id_val].indices = index_array
        serialized_index_array = [asdict(index) for index in index_array]

        # We can optionally notify about newly attached indices
        self.send_message_async(Service.Topic.INDEX_COMPLETE, {'index': serialized_index_array})

        # Return the ID so we know which engram was updated
        return id_val
