# Engramic Plugin and Profile System

Engramic is designed with a **plugin layer** that allows seamless integration with various components such as LLMs, databases, vector databases, and embedding services. The glue that binds these systems together are called **profiles**.

## Example: Default Profile Configuration

```toml
version = 0.1

[mock]
type = "profile"
vector_db.db = {name="Mock"}
llm.retrieve_gen_conversation_direction = {name="Mock"}
llm.retrieve_gen_index = {name="Mock"}
llm.retrieve_prompt_analysis = {name="Mock"}
db.document = {name="Mock"}
llm.response_main = {name="Mock"}
llm.validate = {name="Mock"}
llm.summary = {name="Mock"}
llm.gen_indices = {name="Mock"}
embedding.gen_embed = {name="Mock"}

[standard]
type = "pointer"
ptr = "standard-2025-04-01"

[standard-2025-04-01]
type = "profile"
vector_db.db = {name="ChromaDB"}
llm.retrieve_gen_conversation_direction = {name="Gemini", model="gemini-2.0-flash"}
llm.retrieve_gen_index = {name="Gemini", model="gemini-2.0-flash"}
llm.retrieve_prompt_analysis = {name="Gemini", model="gemini-2.0-flash"}
db.document = {name="Sqlite"}
llm.response_main = {name="Gemini", model="gemini-2.0-flash"}
llm.validate = {name="Gemini", model="gemini-2.0-flash"}
llm.summary = {name="Gemini", model="gemini-2.0-flash"}
llm.gen_indices = {name="Gemini", model="gemini-2.0-flash"}
embedding.gen_embed = {name="Gemini", model="text-embedding-004"}
```

## Loading a Profile with the Host

When creating a `Host`, you should load the initial profile like so:

```python
host = Host(
    'standard',
    [
        MessageService,
        RetrieveService,
        ResponseService,
        StorageService,
        CodifyService,
        ConsolidateService
    ]
)
```

In this example, the developer is using the `standard` profile. This is a **pointer profile** that redirects to a dated version (e.g., `standard-2025-04-01`). As Engramic evolves, the `standard` pointer will be updated to reference the currently recommended profile. By using `standard`, you're always aligned with the recommended configuration.

The `mock` profile is another key option. When using `mock`, all plugins are mock implementations — meaning **no API calls are made**. This mode is intended exclusively for **testing and development**.

