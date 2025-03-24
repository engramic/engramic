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


def test_render_engram() -> None:
    """Test the render_engram method."""
    engram = Engram(
        locations=['test_location'],
        source_ids=['test_source'],
        content='test_text',
        is_native_source=True,
        id='3702e0f0-3aac-4df9-8c33-78cf162f9cfd',
        accuracy=0,
        relevancy=0,
        context={'title': 'Title of Paragraph'},
        indices=[MockIndex('index1'), MockIndex('index2')],
    )

    expected_output = 'id = "3702e0f0-3aac-4df9-8c33-78cf162f9cfd"\ncontent = "test_text"\nis_native_source = true\nlocations = ["test_location"]\nsource_ids = ["test_source"]\ncontext = { title = "Title of Paragraph" }\n[[indices]]\ntext = "index1"\nembedding = "fdsfdasfds"\n[[indices]]\ntext = "index2"\nembedding = "fdsfdasfds"'

    render = engram.render()

    assert render == expected_output
