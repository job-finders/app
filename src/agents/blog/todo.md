# Blog-Agent Standardisation TODO – Agent Layer Only

## Phase 1 – Folder & File Layout
- [ ] 1.1 Create `/src/agents/blog/`  
      ├── `__init__.py` (exports the new agents)  
      ├── `agent.py` (single class per agent, mirrors employer-agent pattern)  
      ├── `prompts/`  
      │   ├── system.jinja2  
      │   ├── user.jinja2  
      │   └── tools.jinja2  
      ├── `schemas.py` (Pydantic models only for agent I/O)  
      └── `memory.py` (re-use employer-agent memory wrapper)

## Phase 2 – Prompt & System Standardisation
- [ ] 2.1 Convert any ad-hoc strings into **Jinja2 templates** matching employer-agent style.  
- [ ] 2.2 Ensure **system prompt** specifies:  
      - Role = “Blog-Agent-{Type}”  
      - Output must comply with `schemas.py`  
      - Read/write memory keys explicitly listed  
- [ ] 2.3 Add unit tests for prompt rendering (snapshot tests).

## Phase 3 – Agent Classes
- [ ] 3.1 `TopicDiscoveryAgent`  
      - Inputs: site map (already scraped)  
      - Outputs: list of topic objects (schema)  
      - Memory key prefix: `topics:raw`

- [ ] 3.2 `ArticlePlannerAgent`  
      - Inputs: topic object  
      - Outputs: article outline object (schema)  
      - Memory key prefix: `outline:{topic_id}`

- [ ] 3.3 `PerformanceMonitorAgent`  
      - Inputs: article slug  
      - Outputs: performance metrics object (schema)  
      - Memory key prefix: `perf:{slug}`

- [ ] 3.4 `RefinerAgent`  
      - Inputs: performance metrics object  
      - Outputs: updated topic/article outline instructions  
      - Memory key prefix: `refinement:{slug}`

## Phase 4 – Memory & Tool Re-Use
- [ ] 4.1 Import and re-use **exact same** Memory class from employer agents.  
- [ ] 4.2 Import and re-use **exact same** tool-calling DSL.  
- [ ] 4.3 Ensure TTL & key-naming conventions match employer agents.

## Phase 5 – CI / Observability
- [ ] 5.1 Add minimal unit tests (prompt snapshot, memory round-trip).  
- [ ] 5.2 GitHub Action runs on push to `/src/agents/blog/**` (lint + tests).  
- [ ] 5.3 Update `/src/agents/__init__.py` to register new agents.


## Phase 6 – Hashnode Integration
- [ ] 6.1 Import & wrap `HashnodeService` (from `src.services.hashnode`) into `src/agents/blog/hashnode_client.py`
- [ ] 6.2 Update `ArticlePlannerAgent` → returns outline **and** Hashnode draft ID
- [ ] 6.3 Create `HashnodePublisherAgent` (new) – create/update posts via Hashnode API
- [ ] 6.4 Update `PerformanceMonitorAgent` – pull real metrics via Hashnode analytics
- [ ] 6.5 Update `RefinerAgent` – push edits as new Hashnode revisions
- [ ] 6.6 Add CLI flag `--publish` to actually hit Hashnode (dry-run by default)
