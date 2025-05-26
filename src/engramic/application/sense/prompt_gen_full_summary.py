# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenFullSummary(Prompt):
    def render_prompt(self) -> str:
        rendered_template = Template("""
    Perform the actions listed below. You are going to generate a keyword phrase and an outline.

    This is meta data we already have:

    file_path - ${file_path}
    file_name - ${file_name}
    document_title - ${document_title}
    document_format - ${document_format}
    document_type - ${document_type}
    table of contents - ${toc}
    summary of first few pages - ${summary_initial}

    This is the full text:
    ${full_text}

    Perform these actions:
    1. In keywords, generate a keyword phrase of 8 to 10 keywords that describe this document.
    2. In summary_full, write an outline of this document.
        a. Must be an outline.
        b. Provide a title.
        c. Maintain the top to bottom order of the document.
        d. List all H1 topics. Group them if there are more than ten. IF there are more than 20, show only the groups.




    """).render(**self.input_data)
        return str(rendered_template)
