# BlogFeedbackController Documentation

## Overview

The `BlogFeedbackController` is responsible for ingesting blog post performance data from external sources (e.g., Hashnode analytics) and storing it in the local database. It also calculates a simple feedback score based on the ingested data.

## Purpose

-   To collect and store performance metrics for blog posts.
-   To calculate a feedback score that reflects user engagement with the posts.
-   To provide a basis for further analysis and optimization of blog content.

## Dependencies

-   `PerformanceORM`: SQLAlchemy model for storing blog post performance data.
-   `init_logger`: Function for initializing a logger instance.
-   `Flask`: Used for application context.

## Methods

### `__init__(self, factory)`

-   **Description:** Initializes the controller with a session factory and a logger.
    -   Calls the superclass constructor (`Controllers.__init__(factory)`).
    -   Initializes a logger for the controller.
-   **Parameters:**
    -   `factory`: The session factory used to create database sessions.
-   **Returns:** None

### `init_app(self, app: Flask)`

-   **Description:** Registers the controller with a Flask application.
-   **Parameters:**
    -   `app`: The Flask application instance.
-   **Returns:** None
-   **Details:**
    -   Calls the superclass's `init_app` method.
    -   Logs that the feedback controller has been initialized.

### `calculate_feedback_score(self, perf: PerformanceORM) -> float`

-   **Description:** Calculates a feedback score based on reactions, comments, and views.
-   **Parameters:**
    -   `perf` (PerformanceORM): The PerformanceORM instance containing the data.
-   **Returns:** A float representing the feedback score.
-   **Details:**
    -   Calculates the score using the formula: `(reactions * 2 + comments * 3) / max(views, 1)`.
    -   Rounds the result to 4 decimal places.

### `ingest_performance(self, performance_data: dict) -> str`

-   **Description:** Stores analytics pulled from Hashnode into PerformanceORM.
-   **Parameters:**
    -   `performance_data` (dict): A dictionary containing performance metrics for a blog post, including:
        -   `article_id` (str): The ID of the article.
        -   `views` (int): The number of views.
        -   `read_time` (float): The read time.
        -   `reactions` (int): The number of reactions.
        -   `comments` (int): The number of comments.
        -   `shares` (int): The number of shares.
        -   `collected_at` (str): The ISO 8601 formatted collection timestamp.
-   **Returns:** A string representing the ID of the created PerformanceORM record.
-   **Details:**
    1.  Creates a `PerformanceORM` instance with the provided data.
    2.  Calculates the feedback score using `calculate_feedback_score`.
    3.  Adds the record to the database session.
    4.  Flushes the session to get the generated ID.

## Input Validation

-   The controller expects the `performance_data` dictionary to contain specific keys (`article_id`, `collected_at`) and uses `.get()` for optional fields (`views`, `read_time`, `reactions`, `comments`, `shares`).
-   It uses `datetime.fromisoformat` to parse the `collected_at` timestamp.

## Error Handling

-   The `@error_handler` decorator is used to wrap the `ingest_performance` method, providing a consistent way to catch exceptions, log errors, and return structured error responses.

## Notes

-   The controller is relatively simple, focusing on ingesting and storing data.
-   The `calculate_feedback_score` method provides a basic metric for evaluating post performance.
-   The controller relies on external services (e.g., Hashnode) to provide the performance data.