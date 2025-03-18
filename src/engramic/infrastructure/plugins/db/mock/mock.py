import json
from typing import Any

import pluggy

from engramic.core.db import DB
from engramic.infrastructure.system.plugin_specifications import db_impl


class Mock(DB):
    @db_impl
    def connect(self, **kwargs: Any) -> bool:
        del kwargs
        return True

    @db_impl
    def close(self) -> bool:
        return True

    @db_impl
    def execute(self, query: str) -> str:
        if query == 'load_batch':
            return_string = """[
                {
                    "location": "file:///Users/allin_podcast/episodes/167.csv",
                    "source_id": "550e8400-e29b-41d4-a716-446655440000",
                    "content": "Chamath explains his take on the latest inflation report and what it means for investors.",
                    "is_native_source": true,
                    "context": {
                    "episode": 167,
                    "segment": "Economic Trends",
                    "topic": "Inflation and Interest Rates",
                    "speakers": ["Chamath Palihapitiya", "David Sacks"],
                    "show": "All-In Podcast"
                    },
                    "meta_id": "a1b2c3d4-e5f6-4711-8097-92a8c3f6d5e7",
                    "library_id": "f1e2d3c4-b5a6-4f78-9a0b-1c2d3e4f5a6b",
                    "id": "c1d2e3f4-a5b6-4c78-9d0e-1f2a3b4c5d6e"
                },
                {
                    "location": "file:///Users/allin_podcast/episodes/168.csv",
                    "source_id": "660f9511-e39b-52d5-c817-667766552222",
                    "content": "David Friedberg discusses AI-driven biotech startups and their impact on medicine.",
                    "is_native_source": false,
                    "context": {
                    "episode": 168,
                    "segment": "Tech & Innovation",
                    "topic": "AI in Biotech",
                    "speakers": ["David Friedberg"],
                    "show": "All-In Podcast"
                    },
                    "meta_id": "b2c3d4e5-f6a7-4811-8097-92a8c3f6d5e7",
                    "library_id": "g3h4i5j6-k7l8-5f78-9a0b-1c2d3e4f5a6b",
                    "id": "d2e3f4g5-h6i7-5c78-9d0e-1f2a3b4c5d6e"
                },
                {
                    "location": "file:///Users/allin_podcast/episodes/169.csv",
                    "source_id": "770g0612-f4ab-63e5-d927-778877663333",
                    "content": "Jason and Sacks debate the role of government in venture capital funding.",
                    "is_native_source": true,
                    "context": {
                    "episode": 169,
                    "segment": "Startup & VC",
                    "topic": "Government Role in VC",
                    "speakers": ["Jason Calacanis", "David Sacks"],
                    "show": "All-In Podcast"
                    },
                    "meta_id": "c3d4e5f6-a7b8-5911-8097-92a8c3f6d5e7",
                    "library_id": "h4i5j6k7-l8m9-6f78-9a0b-1c2d3e4f5a6b",
                    "id": "e3f4g5h6-i7j8-6c78-9d0e-1f2a3b4c5d6e"
                }
            ]"""

            return json.loads(return_string)
        return ''

    @db_impl
    def execute_data(self, query: str, data: dict) -> bool:
        if query == 'save_history':
            del data
            return True
        return False


pm = pluggy.PluginManager('llm')
pm.register(Mock())
