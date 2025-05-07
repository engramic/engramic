# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenMeta(Prompt):
    def render_prompt(self) -> str:
        rendered_template = Template("""



    These are the initial pages of a pdf named ${file_name} from location ${file_path} and you are only seeing the first several pages. From the images, extract the following:


    file_path - The file path of the document
    file_name - The file name of the document
    subject - The main subject or subjects the document is about.
    audience - The intended audience for the document. Must be explicitly stated otherwise "null".
    document_title - The title of the document.
    document_format - word_processing | presentation  | null
    document_type - legal | null
    toc - Table of contents in dict[str,Any] format.
    summary_initial - Write an outline starting with the broadest description. In general terms of the document purpose, and not concrete terms, define what are main and subtopics listing the term "Main Topics:" and "Sub Topics". You may give examples of main and sub topics by useing (e.g. )


    For example:
    Description: The document is about dogs.
    Main Topics: Dogs (e.g. terrier, mastif)
    Sub Topics: Care (e.g. At home, veteranarian), Food (e.g. Feeding time, Ingredients)

    If a topic is not observable, simply provide null as a value.

    """).render(**self.input_data)
        return str(rendered_template)
