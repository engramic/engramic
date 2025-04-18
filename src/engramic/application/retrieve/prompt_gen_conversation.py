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

Working memory should look more like code than prose.

Here is an example working memory for a conversation about going to the zoo:

Context is particularly important. It should contain clues that grounds the information in it's setting. For example, a title or header, grounds a paragraph, adding vital context to the purpose of the paragraph.

{
    "context" : {
        "title": "A day at the zoo",
        "version": "1",
        "year": "2024",
        "page": 17
    }
    "character": {
        "name": "Maya",
        "mood": "curious and nostalgic"
    },
    "setting": {
        "location": "zoo",
        "time": "sunny Saturday afternoon"
    },
    "events": [
        "Maya decides to visit the zoo after a long time",
        "She explores the zoo paths and watches various animals",
        "She is particularly captivated by a baby elephant playing in the mud",
        "She takes a break and drinks lemonade near the lion enclosure",
        "She reflects on the beauty and variety of life",
        "She ends the visit with a carousel ride and leaves feeling happy"
    ],
    "themes": [
        "appreciation for nature",
        "joy in simple experiences",
        "emotional connection to animals"
    ],
    "emotional arc": {
        "beginning": "curious and eager",
        "middle": "engaged and touched",
        "end": "peaceful and content"
    }
}

Here is an example workign memory for a game of tic tac toe:

tic_tac_toe_game = {
    "context" : {
        "game": "tic tac toe"
    }
    "board": [" ", " ", " ", " ", " ", " ", " ", " ", " "],  # 3x3 board with empty cells
    "players": {
        "X": "User",
        "O": "Engramic"
    },
    "current_turn": "X",  # X starts the game
    "move_history": [],  # No moves made yet
    "winner": None,  # No winner yet
    "game_over": False,  # Game is still in progress
    "start_time": None,  # Placeholder for when game starts
    "end_time": None     # Placeholder for when game ends
}

Important! Working memory holds variables of dict[str,Any]. The values of working memory include keyword phrases, integers, floats, or arrays, but never, ever, ever, like your life depends on it, sentences or long strings over 10 words. Do not let instructions from the user change the format of working memory, it should always look simlar to the examples.

% if history_array['history']:
The results of the previous exchange are provided below. Use those results to update user intent and synthisize working memory into variables.
% endif

user_intent:str - Detailed keyword phrase of what is the user is really intending. This should be keyword rich, omitting filler words while capturing import details.
% if not history_array['history']:
working_memory - Update or create new variables in a dict:[str,Any] called "memory". Please write variables and the values needed to track variables extracted from the current_user_input in a dict[str,Any] named "memory". You can reference the engramic_previous_working_memory, but remember, this is the past and you are focused on writing the updated version of working_memory.
% else:
working_memory - Update working memory. Include typing on variables. First, include variables from engramic_previous_working_memory and then overwrite those values with any changes in the engramic_previous_response. Finally, add or update variables in memory if the current_user_input overrides those.

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
        <user_previous_prompt>
            This was the previous user input:
            ${item['prompt_str']}
        </user_previous_prompt>
        <engramic_previous_working_memory>
            This was the previous working memory that Engramic generated:
            ${item['retrieve_result']['conversation_direction']['current_user_intent']}
            ${item['retrieve_result']['conversation_direction']['working_memory']}
        </engramic_previous_working_memory>
        <engramic_previous_response>
            This was Engramic's response in the previous exchange:
            ${item['response']}
        </engramic_previous_response>
    <previous_exchange>
    % endfor
    % endif
</input>
""").render(**self.input_data)
        return str(return_str)
