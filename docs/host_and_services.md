# Host & Services

The **Engramic Inference Engine** consists of several services, each designed to facilitate distinct aspects of knowledge processing.

## Host

The **Host** contains all of the executing services on the instance/machine. You may add all services or just one. The host manages initialization and the set of resources and capabilities used by all other systems. The Host is like a very lightweight abstraction layer for all services.

```mermaid
flowchart TD
    %% Define node styles
    classDef process fill:#f9f9f9,stroke:#333,stroke-width:1px,rounded:true
    classDef io fill:#e8f4ff,stroke:#4a86e8,stroke-width:1px,rounded:true
    classDef external fill:#f0fff0,stroke:#2d862d,stroke-width:1px,rounded:true
    
    %% Input and external processes
    prompt([User Prompt]):::io
    stream([User Stream]):::io
    sense[Sense]:::external
    
    respond --> stream

    %% Core processes in learning loop
    subgraph "Engramic Learning Loop"
      direction RL
      consolidate[Consolidate]:::process
      retrieve[Retrieve]:::process
      respond[Respond]:::process
      codify[Codify]:::process
      
      consolidate --> retrieve
      retrieve --> respond
      respond --> codify
      codify --> consolidate
    end
    
    %% External connections
    prompt --> retrieve
    sense --> consolidate
```

## Services

- **Retrieve**: Analyzes the prompt, manages short-term memory, and performs retrieval of all engrams.
- **Respond**: Constructs the response to the user.
- **Codify**: While in training mode, assesses the validity of responses, integrating them as long-term memories.
- **Consolidate**: Transforms data into observations, contained knowledge units rich in context.
- **Sense**: Converts raw data into observations.
- **Teach**: (Not in diagram.)Encourages the emergence of new engrams by stimulating connections between existing ones.
- **Repo**: Loads document repositories and defines repo ids. One or more repo ids can bet set when prompting.

## Centralized Services

- **Store**: Centralized storage for long-term, context-aware memory.
- **Message**: Centeralized message passing between all services.
- **Process**: Centralized progress tracking from input (e.g. prompt or document) to inserting into Retrieve.

