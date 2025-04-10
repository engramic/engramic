# Engramic Library Overview

The **Engramic Library** consists of several services, each designed to facilitate distinct aspects of knowledge processing.

## Host

The **Host** contains all of the executing services on the instance/machine. You may add all services or just one. The host manages initialization and the set of resources and capabilities used by all other systems. The Host is like a very lightweight abstraction layer for all services.

## Services

- **Retrieve**: Analyzes the prompt, manages short-term memory, and performs retrieval of all engrams.
- **Respond**: Constructs the response to the user.
- **Codify**: While in training mode, assesses the validity of responses, integrating them as long-term memories.
- **Consolidate**: Transforms data into observations, contained knowledge units rich in context.
- **Store**: Stores long-term, context-aware memory for rapid retrieval.
- **Message**: Centeralized message passing between all services.

## Services In Development

- **Sense**: Converts raw data into observations.
- **Teach**: Encourages the emergence of new engrams by stimulating connections between existing ones.

