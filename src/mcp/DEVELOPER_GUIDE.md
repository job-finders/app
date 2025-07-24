# MCP Internal Developer Guide

## Purpose

This document provides architecture and development guidelines for all MCP (Modular Control Point) servers in the
platform. It is intended for internal engineering teams building and maintaining MCP services.

## Architecture Overview

- **Language:** Python
- **Framework:** [Specify, e.g., FastAPI, Flask, or custom]
- **Entry Point:** Each MCP has a main file in `src/mcp/` (e.g., `resumes_mcp.py`, `jobs_mcp.py`)
- **Core Principle:** MCP servers directly import and use internal controller logic from `internal/controllers/`,
  bypassing any external/public API layers.

## Responsibilities

- Expose internal-only endpoints for LLMs and service APIs.
- Orchestrate business logic by calling internal controllers/services.
- Enforce authentication, authorization, and business rules.
- Integrate with other MCPs and platform services as needed.

## Development Pattern

1. **Import Internal Controllers:**
    - MCP servers must import business logic from `internal/controllers/` (e.g.,
      `from internal.controllers.resume_controller import ResumeController`).

2. **Endpoint Definition:**
    - Define only the endpoints required for internal workflows.
    - Avoid exposing public or user-facing APIs.

3. **No HTTP Calls to Core Logic:**
    - All business operations are performed via direct function/class calls, not via HTTP requests to other services.

4. **Security:**
    - Enforce authentication and permissions at the MCP layer.
    - Log all actions for auditing.

5. **Integration:**
    - Use direct imports for cross-MCP logic where possible.
    - For external dependencies (e.g., AI services), use well-defined interfaces.

## Example MCP Server Structure

```python
# src/mcp/example_mcp.py

from internal.controllers.example_controller import ExampleController

controller = ExampleController()

def create_resource(data):
    return controller.create(data)

def update_resource(resource_id, data):
    return controller.update(resource_id, data)

# Define additional internal endpoints as needed