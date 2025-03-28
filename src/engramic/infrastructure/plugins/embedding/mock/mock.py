import pluggy

from engramic.core.interface.embedding import Embedding
from engramic.infrastructure.system.plugin_specifications import embedding_impl


class Mock(Embedding):
    @embedding_impl
    def gen_embed(self, strings: list[str]) -> dict[str, list[str]]:
        del strings
        return {
            'embedding_response': [
                'fdasfdsfasfdsafdfdsafdvfadsfdafvd',
                'fvdsfdafsabfvdfdsljfdjfjfkldjsklv',
                'jfkldsjafjdlksjflkdsjflkdjsflkjda',
            ]
        }


pm = pluggy.PluginManager('embedding')
pm.register(Mock())
