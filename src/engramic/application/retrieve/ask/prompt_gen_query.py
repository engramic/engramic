# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging

from mako.exceptions import text_error_template
from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenQuery(Prompt):
    def render_prompt(self) -> str:
        try:
            rendered_template = Template("""
        From the user prompt, determine the location as interpreted from the users_prompt.
                                         
        Your options include:
        location : the full file path of one or more files ad defined in the user_prompt.
                                         
        <user_prompt>
            ${prompt_str}
        </user_prompt>
        <file_list>
            % for file in file_list:
                ${file}
            % endfor
        </file_list>


        """).render(**self.input_data)
        except Exception:
            error_message = text_error_template().render()
            logging.exception(error_message)
            rendered_template = ''
        return str(rendered_template)
