# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptScanPage(Prompt):
    def render_prompt(self) -> str:
        rendered_template = Template("""
    Read and label items on the page using the following tags. Use no other tags.

    If an item with a given tag doesn't exist skip that tag.
    Never put tags around whitespace (e.g. <h1>\n</h1>)
    Never,ever, make tags with empty inner text (e.g. <h1></h1>)


    <page></page> - The page number if avaialble in image.
    <header></header> - This would be a standard document header. Typically includes a company name, logo, date, or current section.
    <title></title>  - Reserved only for document titles. They are typically in early pages, often the first page in smaller documents but larger documents sometimes have them on page two or three. They are large bold and may be accompanied by a author or a date.
    <chapter></chapter> - A chapter title, typically only in large documents.
    <section></section> - A major section of a document. Typically a very large title on it's very own page with very little else on the page. It's job to signal that the subsequent pages are related to this section. Sections are not that common and most pages do not have them.

    <h1> tags. Use these header tags as you see appropriate given the visual and contextual cues on the page. h1 tags match the main topic.
    <h3> tags. Use these header tags as you see appropriate given the visual and contextual cues on the page. h1 tags match the sub topic.

    <p></p> - A block of text, might be a paragraphs or a couple of paragraphs but possibly only a line of text. Isn't typically bold and looks like most of the font on the page.
    <img></img> - An alt text description of the image. An img tag should never be empty.

    Do not use <ul> tags. Use only the tags you are given.

    Contextual information about the document:
    You are viewing page ${page_number} from a document.
    file_name - ${file_name}
    document_title - ${document_title}
    document_format - ${document_format}
    document_type - ${document_type}
    toc - ${toc}
    summary_initial - ${summary_initial}

    Do not begin and end your response with a fence (i.e. three backticks)

    Begin with the page number.

    """).render(**self.input_data)
        return str(rendered_template)
