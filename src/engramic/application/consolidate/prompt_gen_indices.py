# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenIndices(Prompt):
    def render_prompt(self) -> str:
        return_str = Template("""
Review the content and generate short yet context rich phrase indexes that can be used as an index to perform a relevance search seeking to find the content. An index should be at least 8 relevant words long but may be longer.

Do not make redundant indexes.

You should make up to ${(len(engram.content) // 200)+1} indexes.

A third of your indexes should be a high level overview of your content.
The remaining two thirds of your indexes should be focused on important details.

<context>
    ${engram.context}
</context>
<content>
    ${engram.content}
</content>
""").render(**self.input_data)
        # logging.info("=================================")
        # logging.info(return_str)
        return str(return_str)
