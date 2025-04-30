# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptGenFullSummary(Prompt):
    def render_prompt(self) -> str:
        rendered_template = Template("""


    This is meta data we already have:

    file_path - ${file_path}
    file_name - ${file_name}
    document_title - ${document_title}
    document_format - ${document_format}
    document_type - ${document_type}
    toc - ${toc}
    summary_initial - ${summary_initial}

    This is the full text:
    ${full_text}

    Perform these two actions:
    1. Generate a keyword phrase of 8 to 10 keywords that describe this document.
    2. Concisely summarize this document as an outline that is two levels deep, saving the results in summary_full.

    """).render(**self.input_data)
        return str(rendered_template)
