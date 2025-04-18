# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptAnalyzePrompt(Prompt):
    def render_prompt(self) -> str:
        return_str = Template("""
Analyze the users prompt.
<user_prompt>
    ${prompt_str}
</user_prompt>
Classify it into the following categories:
response_type: short | medium | long
user_prompt_type: typical | reference
A reference type is an article, paragraph, data, that the user is asking me to understand as a reference.
""").render(**self.input_data)
        return str(return_str)
