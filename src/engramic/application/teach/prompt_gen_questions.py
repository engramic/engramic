# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenQuestions(Prompt):
    def render_prompt(self) -> str:
        rendered_template = Template("""


    High Level Summary:
    ${meta['summary_initial']}

    Document Summary:
    ${meta['summary_full']['text']}

    We are going to peform an analysis on this document, to this this, I need to you generate 3 study actions to understand the document better.

    I need you to generate study actions that are the most apropriate for the entirety of the document, now is not the time to get overly specific, keep it high level. Consider the purpose of the document so that your study actions are the most relevant.

    Go for it, generate ten relevant study actions based on the entirety of the document.
    Popular study actions include:
    location: ${meta['locations']} List all
    location: ${meta['locations']} Summarize all topics
    location: ${meta['locations']} interpret all of
    location: ${meta['locations']} Make comparrisons of all
    location: ${meta['locations']} Find trends of all

    Include the location tag in each action.
    Include the prefix about being concise, brief, so that they answers aren't overly verbose.
    Include the suffix "all" to help the researcher be thorough.

    Bias your questions towards lists if they exist in the Document Summary as that is a very popular request for your audience.
    Your remaining questions should not be random, but rather, the most valuable for a business professional.

    If it makes sense for the purpose of this document, feel free to make several study actions so that you can cover the broad base of the document.

    """).render(**self.input_data)
        return str(rendered_template)
