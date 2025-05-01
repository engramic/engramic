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
    <h1></h1> - A main topic in this document.
    <h3></h3> - A sub topic in this document, supporting main topics with further detail.
    <engram></engram> - Group paragraphs and items that are semantically related. A good engram is a group of sub topics the size of one or two paragraphs.
    <p></p> - A block of text, might be a paragraphs or a couple of paragraphs but possibly only a line of text.
    <img></img> - An alt text description of the image. An img tag should never be empty.

    A good engram looks like this:

    <h1>Main topic</h1>
    <engram>
    <h3>Sub Topic</h3>
        <p>Some text related to sub topic.</p>
    <h3>Sub Topic</h3>
    </engram>

    % if page_split["is_continuation"]==True:
    The beginning of this page contains text that continues from the previous page's main topic.
    Your response should not begin with a h1 tag.
    % endif


    Do not begin and end your response with a fence (i.e. three backticks)

    """).render(**self.input_data)
        return str(rendered_template)
