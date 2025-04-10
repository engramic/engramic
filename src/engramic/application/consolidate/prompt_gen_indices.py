# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenIndices(Prompt):
    def render_prompt(self) -> str:
        return_str = Template("""
Review the content and generate short yet context rich phrase indexes that can be used as an index to perform a relevance search seeking to find the content. An index should be at least 8 relevant words long but may be longer.

If the information is a sentence, you may only need one or two indexes.

If the information is a paragraph and very dense with information, you may need four or five.

If the information is more than a paragraph and very dense, you may need 8 to 10 indexes.
<infomation>
    ${engram.content}
</information>
""").render(**self.input_data)
        return str(return_str)
