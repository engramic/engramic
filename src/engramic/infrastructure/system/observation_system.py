# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import time
import uuid
from dataclasses import asdict, dataclass
from typing import cast

from engramic.core import Index, Meta
from engramic.core.observation import Observation
from engramic.infrastructure.repository.engram_repository import EngramRepository


@dataclass
class ObservationSystem(Observation):
    def merge_observation(
        self, observation: Observation, accuracy_filter: int, relevancy_filter: int, engram_repository: EngramRepository
    ) -> Observation:
        observation_cast = cast(ObservationSystem, observation)
        observation_dict = asdict(observation_cast)

        filtered_engrams_dict = [
            dict(m)
            for m in observation_dict['engram_list']
            if m['accuracy'] > accuracy_filter and m['relevancy'] > relevancy_filter
        ]

        combined_source_ids: list[str] = list({
            source_id: str for m in filtered_engrams_dict for source_id in m['source_ids']
        })
        combined_locations: list[str] = list({
            location: str for m in filtered_engrams_dict for location in m['locations']
        })

        index = Index(**observation_dict['meta']['summary_full'])
        new_meta = Meta(
            str(uuid.uuid4()),
            combined_locations,
            combined_source_ids,
            observation_dict['meta']['keywords'],
            observation_dict['meta']['summary_initial'],
            index,
        )

        engram_list = engram_repository.load_batch_dict(filtered_engrams_dict)

        merged_observation: Observation = ObservationSystem(str(uuid.uuid4()), new_meta, engram_list, time.time())

        return merged_observation
