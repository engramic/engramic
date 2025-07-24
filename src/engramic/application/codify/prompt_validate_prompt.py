# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from mako.template import Template

from engramic.core.prompt import Prompt


class PromptValidatePrompt(Prompt):
    def render_prompt(self) -> str:
        return_string = Template("""
Your task is to study the original_prompt and article forming long term memories called Engrams that are extracted from the original_prompt and article saving your memories as valid TOML file.

You should never form Engrams from data in the <sources></sources>. That data is only provided to help you calculate relevancy and accuracy.

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

Instructions are memorable.
% endif

If the original_prompt and article contains no memorable data, then you should respond with the following table:
[not_memorable]
reason = "insert briefly why you don't think it's memorable."

If the original_prompt and article contains memorable data, you may choose to provide one, two, or three engrams, but if you do provide an engram, you must also provide a meta table. Never provide more than one meta table.

An engram should be a unique, complete thought, with enough information to fill an index card. Grab as much memorable information as you can, which may be as little as a single sentence or as big as a large table. You should avoid breaking up information that is semantically related. For exmaple, if there is a list, it would be better to have a single engram with the entire list than three engrams that split the contextually related information.

% if is_lesson:
This particular original_prompt and article is special and needs special treatment. You should try and generate one, maybe two engrams for this original_prompt and article.
The information is designed to be cohesive and it's better to consolidate simlar topics agressively into as few engrams as possible.


% endif

% if is_on_demand:
This particular original_prompt and article is special and needs special treatment. You should try and generate one engram for this original_prompt and article that extracts the main topic and captures as much of the meaningful information as possible.

If the data is tabular, save it as a csv.
% endif

In the meta section, insert keywords and an outline summary based on the content and context of all engrams.

Valid TOML file:
A multi-line text requires tripple quotes.
never includes ```toml fences or any fences at all such as```

<TOML_file_description>
[[engram]]
engram_type = "episodic" unless specficially described as an "artifact"
content = "extract memorable facts from the original_prompt and article."
context = a tripple single quote (e.g. ''') wrapped valid json string of key pair data (e.g. "key":"value" ) that provides a contextual understandng of the content. Think of context as all of the relevant details you would need to give someone to fully understand the content such as a title, section, document name, subject, etc.

formatting example: context = '''{"key":"value"}'''

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
summary_full.text = "Condense the outline to roughly 50 words by abstracting low level details into higher level overviews. Very important: Include context keys and values."
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
        context: ${engram.context}
        meta_ids: ${engram.meta_ids}
        locations: ${engram.locations}
        source_ids: ${engram.source_ids}
    </citation>
%   endfor
</sources>
% endif
""").render(**self.input_data)

        return str(return_string)
