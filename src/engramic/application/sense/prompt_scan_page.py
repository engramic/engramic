# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptScanPage(Prompt):
    def render_prompt(self) -> str:
        rendered_template = Template("""
    You are viewing page ${page_number} from a document. This is the page as determined by counting pages, not scanned page in the image.

    file_path - ${file_path}
    file_name - ${file_name}
    document_title - ${document_title}
    document_format - ${document_format}
    document_type - ${document_type}
    toc - ${toc}
    summary_initial - ${summary_initial}

    Read and label items on the page using the following tags. Use no other tags.
    If an item doesn't exist, simply leave it empty.
    Do not put tags around whitespace such as a group of returns.



    <page></page> - The page number if avaialble in image.
    <header></header> - This would be a standard header. Typically includes a company name, logo, date, or current section.
    <chapter></chapter> - A chapter title, typically only in large documents.
    <section></section> - A section of a document. Typically a large title on a page denoting that the subsequent pages are related to this title.
    <title></title>  - Reserved only for obvious document titles.
    <h1></h1> - A typical heading in this document. A h1 is typically the start of a new idea and is clearly linked to the Main Topics described in the summary_initial.
    <h3></h3> - A typical heading that is contained under a h1, supporting it with further detail. It adds detail to the Sub Topics described the summary_initial.
    <engram></engram> - Group paragraphs and semanticaly related items into blocks of items that are semantically related. Never nest h1 and h3 tags inside of it the engram is always at a level just below that.
    <p></p> - A block of text, might be a paragraphs or a couple of paragraphs but possibly only a line of text.
    <img></img> - An alt text description of the image. An img tag should never be empty.




    Do not begin and end your response with a fence (i.e. three backticks)

    """).render(**self.input_data)
        return str(rendered_template)
