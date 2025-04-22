# Engramic API Reference (v{{ version }})

<p align="center">
  <img src="assets/logo_200.png" alt="Engramic Logo">
</p>

---

Engramic is pre-alpha. It's a great time to start working with these core systems for some developers, but we have yet to complete many important features and even the core systems may not be fully tested. In other words, use of this code base will require some development experience and the ability to work in maturing environments. The flip side, is that a new community is forming and as a pioneer, you have an opportunity to get in early so that you can someday tell your friends, *I used Engramic before it was cool*.

There is currently no support for the following:

- There is no support for individual users.
- There is no HTTP(s) interface at this time. 
- This is no support for documents such as PDFs.
- Windows and MacOS is not being tested as part of our release process.

These features, along with others, will be available in the near future.

---

For an evergreen overview of Engramic, visit our online [Knowledge Base](https://www.engramic.org/knowledge-base).

## Introduction to Engramic

### Why Engramic?

Engramic is designed to learn from your unstructured, proprietary data using any large language model (LLM). When we study, we often begin by reading a document from start to finish. But true understanding comes from synthesizing the information, asking questions, identifying what’s meaningful, and connecting it to prior knowledge and related context. Learning is an iterative process—not a linear one. That’s why we believe a large context window alone doesn’t solve the challenge of truly understanding a dataset. This belief, shaped by two years of research, is what inspired Engramic’s design.

---

### Engramic Architecture Philosophy

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
