# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptMainPrompt(Prompt):
    def render_prompt(self) -> str:
        render_string = Template("""
Respond to the user's prompt as if you were having a business conversation with them.  Be informative, accurate, and complete. It is very, very important to begin your response by answering the user's prompt directly and before you cover other topics.

% if len(engram_list)>0:
Do not explain the instructions but do let them influence how you respond.

<instructions>
    <definitions>
    Sources are citable information found during a search.
    Memories are information you remember and are derrived from sources.
    </definitions>
    <priorities>
        Prioritize answering the user's prompt over providing information from Sources and Memories.
        When information conflicts, prioritize Sources over Memories.
        When information conflicts, prioritize newer timestamps over older ones.
    </priorities>
    <no_answer>
        If you can't satisfy the user's prompt within the sources, begin your response by telling them you couldn't find an answer in the source and ask them if they would like you to use your pre-trained knowledge to search for more information. You may offer alternative topics based on the sources you found.
    </no_answer>
</instructions>
<sources>
    % for engram in engram_list:
    if engram["is_native_source"]:
        <source>
            % if len(engram["locations"]) == 1:
            location: ${engram["locations"][0]}
            % else:
            % if engram.get("context"):
            <context>
            % for key, value in engram["context"].items():
                ${key}: ${value}
            % endfor
            </context>
            % endif
            locations: ${", ".join(engram["locations"])}
            % endif
            content: ${engram["content"]}
            timestamp: ${engram["created_date"]}
        </source>
    if not engram["is_native_source"]:
        <memory>
            % if len(engram["locations"]) == 1:
            location: ${engram["locations"][0]}
            % else:
            % if engram.get("context"):
            <context>
            % for key, value in engram["context"].items():
                ${key}: ${value}
            % endfor
            </context>
            % endif
            locations: ${", ".join(engram["locations"])}
            % endif
            content: ${engram["content"]}
            timestamp: ${engram["created_date"]}
        </memory>
    % endfor
</sources>
% endif

<user_prompt>
    ${prompt_str}
</user_prompt>
""").render(**self.input_data)
        return str(render_string)
