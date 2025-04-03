# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenConversation(Prompt):
    def render_prompt(self) -> str:
        return_str = Template("""
<instructions>
    Review the original prompt and briefly summarize user intent and determine if you need to do any research to answer the question. For example, if the user is making idle conversation such as "hi" or "how are you doing?" that doesn't require research.

    Provide two items in your response: user_intent:str and perform_research:bool.

    user_intent: Answer in 10 or less in a sentence like keyword phrase that predicts the direction of the conversation.
</instructions>
<original_prompt>
    ${prompt_str}
<original_prompt>
""").render(**self.input_data)
        return str(return_str)
