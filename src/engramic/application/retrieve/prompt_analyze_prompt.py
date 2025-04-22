# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptAnalyzePrompt(Prompt):
    def render_prompt(self) -> str:
        return_str = Template("""
Analyze the users prompt. Your name is Engramic and you act like an individual in a conversation.
<user_prompt>
    ${prompt_str}
</user_prompt>
<working_memory>
    ${working_memory}
</working_memory>
Classify it into the following categories:
response_type: short | medium | long
user_prompt_type: typical | reference (A reference type is an article, paragraph, data, that the user is asking me to understand as a reference)
thinking_steps: Review the prompt and define the next steps.

The working memory which represents the conversation imediatly after updating the working_memory with the information from the user's prompt. Assume the state has already been validated. Write a succint list of the detailed steps Engramic must take now that it is your turn in the converation. Do not include data from the working_memory, just the steps. Don't use pronous. Your last step should be about finishing your turn in the conversation.


""").render(**self.input_data)
        return str(return_str)
