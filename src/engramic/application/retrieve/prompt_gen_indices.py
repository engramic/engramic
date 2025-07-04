# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging

from mako.exceptions import text_error_template
from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenIndices(Prompt):
    def render_prompt(self) -> str:
        try:
            rendered_template = Template("""

        % if selected_repos is not None and repo_ids_filters is not None and all_repos is not None:
        Repos hold files that the user is interested in. The user has selected the following repos:
        % for repo_id in repo_ids_filters:
            ${all_repos[repo_id]}
        % endfor
        % endif

        Write a set of indices, phrases of 5 to 8 words, that will be used by a vector database to search for data that will satisfy the user_prompt.

        If the user is asking you to achieve something, look for instructions. If you find them, build one or more indices about the "instructions" related to the user prompt.


        % if len(meta_list)>0:
        The domain_knowledge gives you insight into knowledge stored in your long term memory. It's here because it's the most closely related information you have stored about the user_prompt. If you have domain knowledge that satisfies the user prompt, consider the information when formulating the indices. Form your set of indices with context items followed by your phrases as defined by this template: context_item: value, context_item2: value, 5 to 8 word phrase.
        % endif

        % for meta in meta_list:
        <domain_knowledge>
            <knowledge>
                information location: ${" ".join(meta.locations)}
                context keywords: ${" ".join(meta.keywords)}
                knowledge: ${meta.summary_full.text}
            </knowledge>
        </domain_knowledge>
        % endfor

        <user_prompt>
            <prompt_string>
                ${prompt_str}
            </prompt_string>
            <current_user_intent>
                ${current_user_intent}
            </current_user_intent>
        </user_prompt>

        """).render(**self.input_data)
        except Exception:
            error_message = text_error_template().render()
            logging.exception(error_message)
            rendered_template = ''
        return str(rendered_template)
