<div align="center">
  <img alt="Engramic Logo" src="https://images.squarespace-cdn.com/content/67b3db6de0a35d0b59158854/69eac5b0-f048-4ec7-84d5-9ba7b7a1272a/logo_gray_200.png">
</div>

# Engramic: Build Apps that Answer, Learn, and Remember

## What is Engramic?
Engramic is an advanced system designed to enhance AI applications with sophisticated context management and memory capabilities. Unlike conventional RAG implementations, Engramic goes beyond simple retrieval and response by integrating memory and learning mechanisms, enabling applications to synthesize their data, improving it's undersanding over time.

## Core Features
- **Context Management**: Maintain and utilize contextual awareness across multiple interactions.
- **Long-Term Memory**: Store and recall relevant information dynamically for more natural and intelligent responses.
- **Learning Capability**: Adapt over time based on interactions and inputs.

## Development Status
We are in early stages of development and platform testing is limited. Core concepts are in place, but the system is still evolving. We encourage developers and researchers to follow our progress and contribute to shaping the future of Engramic.

[Engramic Docs](https://engramic.github.io/engramic/)

[Engramic Knowledge Base](https://www.engramic.org/knowledge-base)

## Getting Started

The fastest way to begin working with Engramic is to download it from pip.

```
pip install engramic
```

During these early phases of development, we recommend working from source code. Setting up your environment is designed to be straightforward. See the "Getting Started" section in our documentation. The complete code is available in examples/mock_profile/mock_profile.py.

### Starter Example 
Run a mock version (no API key required) of Engramic.

**Step 1**. Include the imports & set logging:
```
import logging
from typing import Any

from engramic.application.message.message_service import MessageService
from engramic.application.response.response_service import ResponseService
from engramic.application.retrieve.retrieve_service import RetrieveService
from engramic.core.host import Host
from engramic.core.prompt import Prompt
from engramic.core.response import Response
from engramic.infrastructure.system import Service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
```

**Step 2**. Create a test service and subscribe to the MAIN_PROMPT_COMPLETE message:

```
class TestService(Service):
    def start(self):
        self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_main_prompt_complete)
        return super().start()

    def on_main_prompt_complete(self, message_in: dict[str, Any]) -> None:
        response = Response(**message_in)
        logging.info('\n\n================[Response]==============\n%s\n\n', response.response)
        self.host.shutdown()
```

**Step 3**. Create the host, add the services, and submit a prompt.
```
if __name__ == '__main__':

    host = Host(
        'mock',
        [
            # Order matters due to pub/sub dependencies.
            MessageService,
            RetrieveService,
            ResponseService,
            TestService,  #TestService must be last
        ],
    )

    retrieve_service = host.get_service(RetrieveService)
    retrieve_service.submit(Prompt('Tell me about the All In podcast.'))

    # The host continues to run and waits for a shutdown message to exit.
    host.wait_for_shutdown()
```

This example uses plugins that emulate API calls (i.e. mocks) to LLMs, databases, etc. by returning deterministic data. Visit the documentation for the next "Getting Started" example to use non-mock plugins.

## Dependencies
**Pure Python**
- Pluggy
- Mako
- Tomli
- Cachetools
- Websockets

**Pure Python & C++**
- Pyzmq

## Plugins
Plugins are managed in the engram_profiles.toml file which is generated during the first run. Engramic currently includes the plugins listed below.

*Note: Plugin dependencies are downloaded on first run of the plugin and can be viewed in the plugin.toml file located in the root directory of the plugin.*

Vector DB
- ChomraDB

Database
- SQLite

LLM
- Gemini (2.0)

Embedding
- Google ext-embedding-004



## Getting Involved
If you're interested in contributing or have questions about Engramic, feel free to reach out to us:

**Email**: [info@engramic.org](mailto:info@engramic.org)



