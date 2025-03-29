# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptMainPrompt(Prompt):
    def render_prompt(self) -> str:
        render_string = Template("""
Respond to the user's prompt.
<user_prompt>
    ${prompt_str}
</user_prompt>
% if len(engram_list)>0:
    <sources>
        % for engram in engram_list:
        <source>
            ${"The content is from an original source." if engram["is_native_source"] else "The content is a combination of original sources."}
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
        </source>
        % endfor
    </sources>
% endif
""").render(**self.input_data)
        return str(render_string)
