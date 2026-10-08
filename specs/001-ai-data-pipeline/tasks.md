# Tasks: AI Data Processing Pipeline

## Phase 1: Setup (Shared Infrastructure)
**Purpose**: Project initialization and basic structure

- [x] T001 Create project structure per implementation plan
- [x] T002 Initialize Python 3.11 project with LangGraph and Pydantic dependencies

## Phase 2: Foundational (Blocking Prerequisites)
**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [x] T003 Setup configuration and fallback logic in src/ai/config.py
- [x] T004 Setup data models and strict validation in src/ai/schemas.py
- [x] T005 Implement PDF parsing in src/ai/ingestion/extractor.py

## Phase 3: User Story 1 - Process Data through AI Pipeline (Priority: P1)
**Goal**: As a system orchestrator, I want to process incoming data through the AI pipeline so that the data is correctly ingested, analyzed, and assembled into a final output using the established multi-agent pattern.

### Implementation for User Story 1
- [x] T006 [P] [US1] Create pedagogical drafting agent in src/ai/agents/creador.py
- [x] T007 [P] [US1] Create format query builder and routing in src/ai/pipeline.py
- [x] T008 [US1] Implement LangGraph StateGraph orchestration in src/ai/graph.py
- [x] T009 [US1] Implement Quality Critic Agent (Grounding) in src/ai/agents/critico.py

## Phase 4: User Story 2 - Audit Pipeline Operations with Hermes (Priority: P2)
**Goal**: As a security and logic reviewer, I want the pipeline's execution to be audited using local Nous Hermes 3 so that any vulnerabilities, logic flaws, or inefficiencies are flagged securely.

### Implementation for User Story 2
- [x] T010 [US2] Implement AuditorAgent using Hermes 3 in src/ai/agents/auditor.py
- [x] T011 [US2] Integrate Hermes asynchronous audit into pipeline.py

## Phase 5: Performance & Quality Validation (Pending)
**Purpose**: Execute the performance benchmark and HTTP 422 Grounding tests defined in the latest specification update.

- [ ] T012 [P] Benchmark Performance & Token Usage (Latency < 5s) via scripts/benchmark_modelos.py
- [x] T013 [P] Test Contexto Insuficiente (Grounding Error 422) by mocking unrelated PDF input.
- [x] T014 Test Failover Gemini -> Groq by providing invalid API key.
