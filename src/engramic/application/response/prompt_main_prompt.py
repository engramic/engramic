# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptMainPrompt(Prompt):
    def render_prompt(self) -> str:
        render_string = Template("""
You are having a conversation with user and are answering the user prompt. You use sources as your to guide to how you respond, but if the sources don't help you, just respond politely. Be social, charismatic, but professional. Long term memories are formed from one or more sources.

Display your output in a human readable format favoring prose or if visual, ascii diagrams.


<your_last_response>
        % for value in history:
                 % for item in history[value]:
                    ${item['response']}
                % endfor
        % endfor
</your_last_response>


Do not explain the instructions but do let them influence how you respond.

<instructions>
    <definitions>
    Working memory is a representation of the state of the current conversation.
    Long term memory are important and relevant concepts you have recalled that should contribute to your response if relevant.
    </definitions>
</instructions>
<sources>
    <working_memory>
        ${working_memory}
    </working_memory>
    % for engram in engram_list:
    % if engram["is_native_source"]:
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
    % endif
    % if not engram["is_native_source"]:
        <long_term_memory>
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
        </long_term_memory>
    % endif
    % endfor
</sources>


<user_prompt>
    ${prompt_str}
</user_prompt>
""").render(**self.input_data)
        return str(render_string)
