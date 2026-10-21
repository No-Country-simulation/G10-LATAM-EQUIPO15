# Research & Decisions: AI Data Processing Pipeline

## Decision 1: Security and Validation Strategy (from Hermes Audit)
**Decision**: Implement size limits (`max_length`) and strict character filtering in Pydantic V2 schemas instead of migrating to `re2`. Minimize exposure of sensitive infrastructure details in Enums.
**Rationale**: The Hermes audit identified potential vulnerabilities with bypass of input validations and information leakage via Enums. Adding `max_length` and `pattern` constraints to Pydantic is a native, token-efficient, and lightweight solution that aligns with the "ligero y potente" project goal without introducing C-level dependencies like `re2` which could complicate the local setup.
**Alternatives considered**: 
- Migrating to `re2` (Rejected due to extra dependency weight for a prototype/hackathon phase).
- Removing Enums completely (Rejected as they provide essential structure to the LLM outputs).

## Decision 2: Orchestration Framework
**Decision**: Retain LangGraph (`StateGraph`) for pipeline orchestration.
**Rationale**: It provides deterministic control over the multi-agent flow and supports the "Single-Call Multi-Agent" pattern efficiently.
**Alternatives considered**: LangChain standard chains (Too rigid for multi-agent loops), AutoGen (Overkill and too token-heavy).

## Decision 3: Audit Integration
**Decision**: Trigger local `Nous Hermes 3` via Ollama API as an asynchronous post-processing step or dedicated node in the graph.
**Rationale**: Keeps sensitive security analysis local and cost-free, satisfying the requirement to save tokens while providing robust logic checks.
**Alternatives considered**: Using Gemini/Groq for audit (Rejected to save tokens and keep security checks local).
