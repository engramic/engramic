# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenQuestions(Prompt):
    def render_prompt(self) -> str:
        rendered_template = Template("""

    Document Summary:
    ${meta['summary_full']['text']}

    Use the document summary to generate questions.
    -Your questions should be thorough, capturing all of the items rather than some.
    -Your questions should be detail orientied, capturing the nuance of the main topic.
    -Use proper nouns in place of pronouns.

    Make at least one question each for all of the of the major topics.

    Write the questions in this format:
    Please answer this research question in an outline format:
    location: ${meta['locations']} "Insert a who, what, where, why, how question depending on what is apropriate given the keywords or major topic."

    """).render(**self.input_data)
        return str(rendered_template)
