# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenConversation(Prompt):
    def render_prompt(self) -> str:
        return_str = Template("""
<instructions>
Your name is Engramic and you are in a conversation with the user. When the user submits input and Engramic returns a response, this is known as an exchange. Review the input and provide user intent and a description of your working memory.

% if history_array['history']:
The results of the previous exchange are provided below. Use those results to inform your response.
% endif

user_intent:str - Detailed keyword phrase of what is the user is really intending. This should be keyword rich, omitting any filler words.
% if not history_array['history']:
working_memory - Update or create new variables in a dict:[str,Any] called "memory". Please write variables and the values needed to track all elements of the conversation or any activities that will ensue based on the current_user_input in a dict[str,Any] named "memory". Assume if this were a program, you would need all of these memory variables in order for the code to work. Include any responsibilities you have for yourself.
% else:
working_memory - Update working memory. Include typing on variables. First, include variables from previous_working_memory and then overwrite those values with any changes in the previous_response. Finally, add or update variables in memory if the current_user_input overrides those.

If you are asked to start a new conversation, remove all data from working memory and set it to None.
% endif

</instructions>
<input>
    <current_user_input>
        ${prompt_str}
    </current_user_input>
    % if history_array['history']:
    <previous_exchange>
    % for item in history_array['history']:
        <previous_prompt>
            This was the previous user input:
            ${item['prompt_str']}
        </previous_prompt>
        <previous_working_memory>
            This was the previous working memory that Engramic generated:
            ${item['retrieve_result']['conversation_direction']['current_user_intent']}
            ${item['retrieve_result']['conversation_direction']['working_memory']}
        </previous_working_memory>
        <previous_response>
            This was Engramic's response in the previous exchange:
            ${item['response']}
        </previous_response>
    <previous_exchange>
    % endfor
    % endif
</input>
""").render(**self.input_data)
        return str(return_str)
