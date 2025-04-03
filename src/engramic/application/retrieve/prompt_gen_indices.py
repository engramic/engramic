# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenIndices(Prompt):
    def render_prompt(self) -> str:
        rendered_template = Template("""
    Based on the user prompt, generate lookup strings that will be used to query and fetch additional data that would help you generate a response to the user prompt.

    Domain_knowledge includes knowledge that you have available in your memory. Use it to help formulate your indices.
    % if meta_list:
    <domain_knowledge>
    % for meta in meta_list:
        <knowledge>
            information location: ${" ".join(meta.locations)}
            context keywords: ${" ".join(meta.keywords)}
            knowledge: ${meta.summary_full.text}
        </knowlege>
    </domain_knowledge>
    % endfor
    % endif
    <user_prompt>
        ${prompt_str}
    </user_prompt>

    """).render(**self.input_data)
        return str(rendered_template)
