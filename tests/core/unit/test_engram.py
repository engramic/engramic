# test_engram.py


import uuid

from engramic.core import Engram


class MockContext:
    def render_context(self) -> str:
        return 'mocked_context'


class MockIndex:
    def __init__(self, text: str):
        self.text = text


def test_engram_initialization():
    """Test that an Engram object is initialized correctly."""
    engram = Engram(location='test_location', source_id='test_source', text='test_text', is_native_source=True)

    assert engram.location == 'test_location'
    assert engram.source_id == 'test_source'
    assert engram.text == 'test_text'
    assert engram.is_native_source is True
    assert engram.context is None
    assert engram.indices is None
    assert isinstance(engram.id, str)
    assert uuid.UUID(engram.id)  # Ensure valid UUID


def test_render_engram():
    """Test the render_engram method."""
    engram = Engram(
        location='test_location',
        source_id='test_source',
        text='test_text',
        is_native_source=True,
        context=MockContext(),
        indices=[MockIndex('index1'), MockIndex('index2')],
    )

    expected_output = (
        '<begin>\n'
        'location: test_location\n'
        'mocked_context\n'
        '<indices>\n'
        'index1\n'
        'index2</indices>\n'
        'The text is directly from the source.\n'
        '<text>test_text</text>\n'
        '</end>\n'
    )

    assert engram.render_engram() == expected_output
