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
            rendered_template = Template("""Write a set of 5 to 10 lookup indices, each with phrases of 5 to 8 words, that will be used to query a vector database. An index is a query is important to know in order to satisfy the current_user_intent. If domain_knolwedge does not relate, then do not make an index for it.

        Do not create duplicate indexes.

        % if len(meta_list)>0:
        <domain_knowledge_instructions>
        The domain_knowledge gives you insight into the knowledge in the vector database. If you have domain knowledge that relates to the current_user_intent, use that information when formulating the indices. Form your set of indices with a few context items from the context keywords, followed by your phrases as defined by this template:

        context_item: value, context_item2: value, 5 to 8 word phrase.
        <domain_knowledge_instructions>
        % endif


        <domain_knowledge>
        % for meta in meta_list:
            <knowledge>
                type: ${meta.type}
                % if meta.locations:
                    information location: ${" ".join(meta.locations)}
                % endif
                context keywords: ${" ".join(meta.keywords)}
                knowledge: ${meta.summary_full.text}
            </knowledge>
        % endfor
        </domain_knowledge>

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
