# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenIndices(Prompt):
    def render_prompt(self) -> str:
        rendered_template = Template("""

    % if selected_repos is not None and repo_ids_filters is not None:
    Repos hold files that the user is interested in. The user has selected the following repos:
    % for repo_id in repo_ids_filters:
        ${all_repos[repo_id]}
    % endfor
    % endif

    Write a set of indices, phrases of 5 to 8 words, that will be used by a vector database to search for data that will satisfy the user_prompt.

    When building indices for a list, pay careful attention to the names of the items in the list to ensure that you don't combine similar names.


    % if len(meta_list)>0:
    The domain_knowledge gives you insight into knowledge stored in your long term memory. It's here because it's the most closely related information you have stored about the user_prompt.
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
        ${prompt_str}
    </user_prompt>

    """).render(**self.input_data)
        return str(rendered_template)
