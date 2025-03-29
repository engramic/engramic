# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenIndices(Prompt):
    def render_prompt(self) -> str:
        return_str = Template("""
Review the content and generate short yet context rich phrase indexes that would act as an index to look up the most valuable information provided. An index should be at least 5 relevant words long.
<infomation>
    ${engram_render}
</information>
""").render(**self.input_data)
        return str(return_str)
