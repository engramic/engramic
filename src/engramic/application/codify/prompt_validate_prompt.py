# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptValidatePrompt(Prompt):
    def render_prompt(self) -> str:
        return_string = Template("""
Your task is to study the article, repeating key facts and memorable information that directly relate to the original prompt, writing your response as a valid TOML file. Memorable does not include conversational banter, indentification of information not available, or knowledge that a typical 3rd grader would know.

Your goal is to be thorough but efficient.

If the article contains no memorable data, then you should respond with the following table:
[not_memorable]
reason = "insert briefly why you don't think it's memorable."

If the article contains memorable data, you may choose to provide one, two, or three engrams, but if you do provide an engram, you must also provide a meta table. Never provide more than one meta table.

An engram should be a unique, complete thought, with enough information to fill an index card. Grab as much memorable information as you can, which may be as little as a single sentence or as big as a large table. You should avoid breaking up information that is semantically related. For exmaple, if there is a list, it would be better to have a single engram with the entire list than three engrams that split the contextually related information.

% if engram_list:
In each engram, validate the content of the engram as it relates to the sources.
-The field relevancy is a ranking of how relevant the content is relative to the citations in the sources.
-The field accuracy is a ranking of how accurate the content is relative to the citations in the sources.

In each engram, combine the values below from the sources that contribute to the content for that engram. You may
combine duplicates into single entries.

meta_ids - unique guids
locations - unique uris
source_ids - unique guids
% endif

In the meta section, insert keywords and a summary_full.text value based on the content of the previous engrams.

Valid TOML file:
A multi-line text requires tripple double quotes.

<TOML_file_description>
[[engram]]
content = "extract memorable facts from the article."
% if engram_list:
is_native_source = false
relevancy = value from 0 to 4
accuracy = value from 0 to 4
meta_ids = [meta_guid_1,meta_guid_2,...]
locations = [location1,location2,...]
source_ids = [source_guid_1,source_guid_2,...]
% else:
is_native_source = true
% endif

the Meta table is a summary of the engram tables.
[meta]
keywords = ["insert keyword1","insert keyword2",...]
summary_full.text = "insert short sentence summary of all the above engram contents."
summary_full.embedding = ""
</TOML_file_description>

<original_prompt>
    ${prompt_str}
</orginal_prompt>
<article>
    ${response}
</article>
% if engram_list:
<sources>
%   for engram in engram_list:
    <citation>
        content: ${engram.content}
        meta_ids: ${engram.meta_ids}
        locations: ${engram.locations}
        source_ids: ${engram.source_ids}
    </citation>
%   endfor
</sources>
% endif
""").render(**self.input_data)

        return str(return_string)
