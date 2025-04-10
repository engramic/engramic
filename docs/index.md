# Engramic API Reference

<p align="center">
  <img src="assets/logo_200.png" alt="Engramic Logo">
</p>

================================================================================================

Note: Engramic is pre-alpha. The architecture is designed to support all of the features described in this documentation but the implementation may be partial, not fully tested, or not publicly available at this time. It is a good time to get familiar with the architecture and get involved with the development process.

There is currently no support for the following:

- There is no support for userids.
- There is no HTTP(s) Interface at this time. 
- This is no support for documents such as PDFs.
- Windows and MacOS is not being tested as part of our release process.

These features, along with others, will be available in the near future.

================================================================================================

For an evergreen overview of Engramic, visit our online [Knowledge Base](https://www.engramic.org/knowledge-base).

## Introduction to Engramic

### Why Engramic?

Engramic is designed to seamlessly integrate unstructured, proprietary data with any large language model (LLM).

---

### Engramic Architecture

- **Modular**  
  The plugin system allows easy switching between LLMs, databases, vector databases, and embedding tools.

- **Scalable**  
  Built as a set of independent services, Engramic can run on a single machine or be distributed across multiple systems.

- **Fast**  
  Optimized for usage patterns involving many blocking API calls, ensuring responsive performance.

- **Extensible**  
  Easily create custom services or plugins to extend functionality.

---

### Engramic Core Concepts

- **Memory**  
  Supports both short-term and long-term memory mechanisms.

- **Engram**  
  The fundamental unit of information, which includes content and base and customizable contextual metadata

- **Citable Engrams**  
  External documents or media that are directly referenced. Citable Engrams are high-fidelity textual representations of the media.

- **Long-Term Memory Engrams**  
  Constructed from one or more Citable Engram or other Long-Term Memory Engrams.

- **Learning**  
  Built through the combination of memory, citable external sources, and user interaction or input.

- **Unified Memory**  
  All engrams are stored within a unified system, enabling both full and selective access to memory content.
