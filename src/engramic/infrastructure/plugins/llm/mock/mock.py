
from engramic.core.llm import llm

class mock(llm):

    def submit(self, prompt: str, **kwargs: Any) -> str:
        return """This is an LLM mock return. I might not be able to counts how many r's are in straberry, but I can at least spell potato."""
