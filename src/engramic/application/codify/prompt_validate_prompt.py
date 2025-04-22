# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptValidatePrompt(Prompt):
    def render_prompt(self) -> str:
        return_string = Template("""
Your task is to study the article searching for suitable long term memories called engrams that are extracted from the article, and ONLY from the article, saving your notes as a valid TOML file.

Engrams are important or unique topics. Something unimportant that just happened isn't a long term memory, that will be saved in working memory. Something that I should remember to inform and contribute to my existence or make me smarter is a long term memory. Write responses in absolute terms such as a four digit year rather than saying "last year".

Always use proper nouns and avoid pronouns.

% if engram_list:
Source engrams are listed below. You will be responding with meta and destination engrams.

Destination engrams should always be combinations of multiple source engrams. Do not make duplicates of existing engrams.

The destination engram can cite it's sources by including the source_id in the source_ids array. It should also do the same for meta_ids and locations.

Add supporting context such as headers, titles, page numbers, versions, in the context section.

In each engram, validate the content of the engram as it relates to the sources.
-The field relevancy is a ranking of how relevant the content is relative to the sources.
-The field accuracy is a ranking of how accurate the content is relative to the sources.

Engrams are unique, so if there is already a engram in the source, there is no need to generate another one that is sematnically the same. That is not memorable.
% endif

If the article contains no memorable data, then you should respond with the following table:
[not_memorable]
reason = "insert briefly why you don't think it's memorable."

If the article contains memorable data, you may choose to provide one, two, or three engrams, but if you do provide an engram, you must also provide a meta table. Never provide more than one meta table.

An engram should be a unique, complete thought, with enough information to fill an index card. Grab as much memorable information as you can, which may be as little as a single sentence or as big as a large table. You should avoid breaking up information that is semantically related. For exmaple, if there is a list, it would be better to have a single engram with the entire list than three engrams that split the contextually related information.

In the meta section, insert keywords and an outline summary based on the content and context of all engrams.

Valid TOML file:
A multi-line text requires tripple double quotes.

<TOML_file_description>
[[engram]]
content = "extract memorable facts from the article."
context = a dict:[str,str] that notes context that supports a broader undersanding of the content. Look for <context> xml tags.
% if engram_list:
relevancy = value from 0 to 4
accuracy = value from 0 to 4
meta_ids = [meta_guid_1,meta_guid_2,...] <-values are combined from source metas.
locations = [location1,location2,...] <-values are combined from source engrams.
source_ids = [source_guid_1,source_guid_2,...] <-values are combined from source engrams.
% endif

the Meta table is a summary of the engram tables.
[meta]
keywords = ["insert keyword1","insert keyword2",...]
summary_full.text = "insert a dense summary outline of all the above engrams. Very important: Include context keys and values."
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
