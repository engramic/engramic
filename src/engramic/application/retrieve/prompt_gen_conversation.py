# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenConversation(Prompt):
    def render_prompt(self) -> str:
        return_str = Template("""
<instructions>
Your name is Engramic and you are in a conversation with the user. When the user submits input and Engramic returns a response, this is known as an exchange. Review the input and provide user intent and a description of your working memory which is like system memory on a computer.


Context is particularly important. It should contain clues that grounds the information in it's setting. For example, a title or header, grounds a paragraph, adding vital context to the purpose of the paragraph.

The types of working memory include keyword phrases, integers, floats, or arrays, but never sentences or long strings over 10 words.

% if history_array['history']:
The results of the previous exchange are provided below. Use those results to update user intent and synthisize working memory into variables.
% endif

user_intent:str - Detailed keyword phrase of what is the user is really intending. This should be keyword rich, omitting filler words while capturing import details.

working_memory - Update working memory which is register of variables you will use to track all elements of the conversation. If there are no changes to make on any step, or if the data referenced doesn't exist, respond with changes = None. Write each step as densely as you can, but make sure you maintain context and scope by wrapping related topics:

memory{topic = {variable1:value1,varaiable2:value2}}

To update working memory, you need to perform the following:

Steps
1. Write variables from engramic_previous_working memory and update the values based on the extrapolated values in current_user_input.
2. Add as many new state variables and values that you can by predicting what you may track and then extraploate them from the current_user_input and engramic_previous_response.
3. Drawing from the previous_working_memory, write and update the state of all variables not changed in steps 1 and 2. Stop and think at this step as there may be logic required to determine if state 3 has cascading changes due to changes in state 1 & 2.
4. In order, and starting with a json object called, "memory" combine the states above from 1, 2, and 3. If there are conflicting data, 3 overwrites values from 2, and 2 overwrites values from 1.


</instructions>
<input>
    <current_user_input>
        ${prompt_str}
    </current_user_input>
    <previous_exchange>
    % for ctr, item in enumerate(history_array['history']):
        <timestamp time="${item['response_time']}">
            <user_previous_prompt>
                ${item['prompt_str']}
            </user_previous_prompt>
            <engramic_previous_working_memory>
                ${item['retrieve_result']['conversation_direction']['current_user_intent']}
                ${item['retrieve_result']['conversation_direction']['working_memory']}
            </engramic_previous_working_memory>
            % if ctr <= 3:
                <engramic_previous_response>
                    ${item['response']}
                </engramic_previous_response>
            % endif
        </timestamp>
    <previous_exchange>
    % endfor
</input>


Display your repsonse including user_intent and working memory steps 1 through 4.
Step 1, 2, and 3 should be dense and condensed
Step 4 should be written in json and you should expand steps 1-3 into variables.

""").render(**self.input_data)
        return str(return_str)
