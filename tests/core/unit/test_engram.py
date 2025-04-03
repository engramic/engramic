# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.


import uuid

from engramic.core import Engram


class MockIndex:
    def __init__(self, text: str):
        self.text = text
        self.embedding = 'fdsfdasfds'


def test_engram_initialization() -> None:
    """Test that an Engram object is initialized correctly."""
    engram = Engram(
        id='3702e0f0-3aac-4df9-8c33-78cf162f9cfd',
        locations=['test_location'],
        source_ids=['test_source'],
        content='test_text',
        is_native_source=True,
    )

    assert engram.locations == ['test_location']
    assert engram.source_ids == ['test_source']
    assert engram.content == 'test_text'
    assert engram.is_native_source is True
    assert engram.context is None
    assert engram.indices is None
    assert isinstance(engram.id, str)
    assert uuid.UUID(engram.id)  # Ensure valid UUID
