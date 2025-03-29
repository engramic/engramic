import json
from typing import Any, cast

import pluggy

from engramic.core.interface.db import DB
from engramic.infrastructure.system.plugin_specifications import db_impl


class Mock(DB):
    def __init__(self) -> None:
        self.observations: dict[str, Any] = {}
        self.history: dict[str, Any] = {}

    @db_impl
    def connect(self) -> None:
        return None

    @db_impl
    def close(self) -> None:
        return None

    @db_impl
    def fetch(self, table: DB.DBTables, ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        del ids
        if table.value == 'engram':
            return_string = """{
  "engram": [
    {
      "locations": ["file:///Users/allin_podcast/episodes/167.csv"],
      "accuracy":0,
      "relevancy":0,
      "source_ids": ["550e8400-e29b-41d4-a716-446655440000"],
      "content": "Chamath explains his take on the latest inflation report and what it means for investors.",
      "is_native_source": true,
      "meta_ids": ["a1b2c3d4-e5f6-4711-8097-92a8c3f6d5e7"],
      "library_ids": ["f1e2d3c4-b5a6-4f78-9a0b-1c2d3e4f5a6b"],
      "id": "c1d2e3f4-a5b6-4c78-9d0e-1f2a3b4c5d6e",
      "indices":[{"text":"What is this about","embedding":"43243"}],
      "context": {
        "episode": 167,
        "segment": "Economic Trends",
        "topic": "Inflation and Interest Rates",
        "speakers": ["Chamath Palihapitiya", "David Sacks"],
        "show": "All-In Podcast"
      }
    },
    {
      "locations": ["file:///Users/allin_podcast/episodes/168.csv"],
      "accuracy":0,
      "relevancy":0,
      "source_ids": ["660f9511-e39b-52d5-c817-667766552222"],
      "content": "David Friedberg discusses AI-driven biotech startups and their impact on medicine.",
      "is_native_source": false,
      "meta_ids": ["b2c3d4e5-f6a7-4811-8097-92a8c3f6d5e7"],
      "library_ids": ["f1e2d3c4-b5a6-4f78-9a0b-1c2d3e4f5a6b"],
      "id": "d2e3f4g5-h6i7-5c78-9d0e-1f2a3b4c5d6e",
      "indices":[{"text":"What is this about","embedding":"43243"}],
      "context": {
        "episode": 168,
        "segment": "Tech & Innovation",
        "topic": "AI in Biotech",
        "speakers": ["David Friedberg"],
        "show": "All-In Podcast"
      }
    },
    {
      "locations": ["file:///Users/allin_podcast/episodes/169.csv"],
      "accuracy":0,
      "relevancy":0,
      "source_ids": ["770g0612-f4ab-63e5-d927-778877663333"],
      "content": "Jason and Sacks debate the role of government in venture capital funding.",
      "is_native_source": true,
      "meta_ids": ["c3d4e5f6-a7b8-5911-8097-92a8c3f6d5e7"],
      "library_ids": ["f1e2d3c4-b5a6-4f78-9a0b-1c2d3e4f5a6b"],
      "id": "e3f4g5h6-i7j8-6c78-9d0e-1f2a3b4c5d6e",
      "indices":[{"text":"What is this about","embedding":"43243"}],
      "context": {
        "episode": 169,
        "segment": "Startup & VC",
        "topic": "Government Role in VC",
        "speakers": ["Jason Calacanis", "David Sacks"],
        "show": "All-In Podcast"
      }
    }
  ]
}
"""
            return cast(dict[str, Any], json.loads(return_string))

        if table.value == 'meta':
            return_string = """{"meta":[
            {
                "id":"a1b2c3d4-e5f6-4711-8097-92a8c3f6d5e7",
                "location": "file:///Users/allin_podcast/episodes/167.csv",
                "source_id": ["550e8400-e29b-41d4-a716-446655440000"],
                "keywords": ["inflation", "investors"],
                "summary_initial": "The AllIn podcast talk about the current state of the market",
                "summary_full": {"embedding":None,"text":"The AllIn podcast talk about the current state of the market"}
            },
            {
                "id": "b2c3d4e5-f6a7-4811-8097-92a8c3f6d5e7",
                "location": "file:///Users/allin_podcast/episodes/168.csv",
                "source_id": ["660f9511-e39b-52d5-c817-667766552222"],
                "keywords": ["biotech", "medicine"],
                "summary_initial": "The AllIn podcast talk about biotech.",
                "summary_full": {"embedding":None,"text":"The AllIn podcast talk about biotech."}
            },
            {
                "id": "c3d4e5f6-a7b8-5911-8097-92a8c3f6d5e7",
                "location": "file:///Users/allin_podcast/episodes/169.csv",
                "source_id": ["770g0612-f4ab-63e5-d927-778877663333"],
                "keywords": ["inflation", "investors"],
                "summary_initial": "The AllIn podcast talk about the role of government in venture capital funding.",
                "summary_full": {"embedding":None,"text":"The AllIn podcast talk about the role of government in venture capital funding."}
            }
        ]}"""

            return cast(dict[str, Any], json.loads(return_string))

        error = 'Table type not known.'
        raise ValueError(error)

    @db_impl
    def insert_documents(self, table: DB.DBTables, docs: list[dict[str, Any]]) -> None:
        if table.value == 'history':
            for doc in docs:
                self.history[doc['id']] = doc
            return None
        if table.value == 'observation':
            for doc in docs:
                self.history[doc['id']] = doc
            return None


pm = pluggy.PluginManager('llm')
pm.register(Mock())
