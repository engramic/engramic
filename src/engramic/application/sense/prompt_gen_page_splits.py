# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenPageSplits(Prompt):
    def render_prompt(self) -> str:
        rendered_template = Template("""


    last_main_topic_image_0 - What is the last main topic covered in image_0.
    first_line_text_image_1 - What is the text on the first line of image_1:
    is_continuation:  true - The first line of text in image_1 is a continuation of the last_topic_image_0.


    """).render(**self.input_data)
        return str(rendered_template)
