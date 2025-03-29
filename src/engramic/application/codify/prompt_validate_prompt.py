# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptValidatePrompt(Prompt):
    def render_prompt(self) -> str:
        return_string = Template("""
You job is to extract important information and facts relevant to the original prompt and save them in a TOML file. The file includes one table named "meta", and up to three array of tables named "engram". An engram should be a complete thought with enough information to fill an index card.

The fields for the engram table are as follows.

[[engram]]
content = "extract a memorable fact from the article."
is_native_source = true

the Meta table is a summary of the engram tables.
[meta]
keywords = ["insert keyword1","insert keyword2","insert keyword3","insert keyword4"]
summary_full.text = "insert short sentence summary of all the above engram contents."
summary_full.embedding = ""
<original_prompt>
    ${prompt_str}
</orginal_prompt>
<article>
    ${response}
</article>
% if engram_render_list:
<sources>
%   for engram_render in engram_render_list:
    <knowledge>${engram.summary_full}</knowledge>
%   endfor
</sources>
% endif
""").render(**self.input_data)

        return str(return_string)
