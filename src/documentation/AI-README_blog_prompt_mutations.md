# PromptMutationController Documentation

## Overview
The `PromptMutationController` is responsible for automatically evolving and improving the prompts used by various AI agents within the blog content generation pipeline. It collects performance data, feeds it to a `PromptMutatorAgent`, and saves the new prompts along with mutation logs.

## Purpose
- To automatically improve the performance of AI agents by refining their prompts based on real-world data.
- To track changes to prompts and provide a history of mutations.
- To optimize the blog content generation process over time.

## Dependencies

-   `BlogPromptORM`: SQLAlchemy model for storing blog prompts.
-   `PromptMutationLogORM`: SQLAlchemy model for logging prompt mutations.
-   `ArticleORM`: SQLAlchemy model for storing articles.
-   `PerformanceORM`: SQLAlchemy model for storing performance data.
-   `PromptMutatorAgent`: AI agent for mutating prompts.
-   `get_service`: Helper function for retrieving services.

## Methods

### `__init__(self, factory)`

-   **Description:** Initializes the controller with a session factory and sets up the `PromptMutatorAgent`.
    -   Calls the superclass constructor (`Controllers.__init__(factory)`).
    -   Initializes the `PromptMutatorAgent` with a default user ID ("system").
    -   Sets up a logger for the controller.
-   **Parameters:**
    -   `factory`: The session factory used to create database sessions.
-   **Returns:** None

### `init_app(self, app)`

-   **Description:** Initializes the controller with a Flask application.
-   **Parameters:**
    -   `app`: The Flask application instance.
-   **Returns:** None
-   **Details:**
    -   Calls the superclass's `init_app` method.
    -   Logs that the `PromptMutationController` has been initialized.

### `daily_mutate_prompts(self) -> dict`

-   **Description:** Mutates prompts for TopicDiscoveryAgent, ArticlePlannerAgent, and ContentGeneratorAgent
-   **Parameters:** None
-   **Returns:** A dictionary summarizing the number of mutated prompts: `{"mutated": int}`
-   **Details:**
    1.  Iterates through agent names: "TopicDiscoveryAgent", "ArticlePlannerAgent", "ContentGeneratorAgent".
    2.  Retrieves the latest prompt version from the `BlogPromptORM`.
    3.  Aggregates performance data using `_aggregate_performance`.
    4.  Runs the `PromptMutatorAgent` to generate a new prompt.
    5.  Saves the new prompt to the `BlogPromptORM`.
    6.  Creates a `PromptMutationLogORM` record to track the mutation.

### `_aggregate_performance(self, session, agent_name: str) -> dict`

-   **Description:** Aggregates performance data for a given agent.
-   **Parameters:**
    -   `session`: Database session
    -   `agent_name` (str): The name of the agent to aggregate performance data for.
-   **Returns:** A dictionary containing a summary of the performance data and a list of examples.
    -   `summary`: A dictionary containing average views, read time, and reactions.
    -   `examples`: A list of dictionaries, each containing the article ID, title, views, read time, and reactions for a specific article.
-   **Details:**
    1.  Retrieves the 20 most recent `ArticleORM` and `PerformanceORM` records.
    2.  Calculates the average views, read time, and reactions.
    3.  Creates a list of examples containing the article ID, title, views, read time, and reactions for each article.

## Input Validation

-   The controller relies on the underlying services and agents to handle input validation.
-   It checks for the presence of required data (e.g., latest prompt) before proceeding with prompt mutation.

## Error Handling

-   The `@error_handler` decorator is used to wrap the `daily_mutate_prompts` method, providing a consistent way to catch exceptions, log errors, and return structured error responses.

## Notes

-   The controller relies heavily on other services and agents to perform its tasks, so ensure those dependencies are properly configured.
-   The `PromptMutatorAgent` performs the core logic for prompt mutation and must be implemented separately.
-   The `_aggregate_performance` method provides a basic mechanism for aggregating performance data. More sophisticated aggregation techniques could be used to improve the quality of the mutated prompts.