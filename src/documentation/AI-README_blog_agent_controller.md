# BlogAgentController Documentation

## Overview

The `BlogAgentController` is responsible for managing AI-driven blog content generation and publishing workflows. It orchestrates various AI agents to discover topics, plan articles, generate content, perform SEO audits, and make publishing decisions. It also integrates with Hashnode for publishing and analytics.

## Purpose

- Automate and enhance blog content creation using AI.
- Discover relevant topics, generate high-quality articles, and optimize them for SEO.
- Schedule and publish drafts to Hashnode.
- Gather feedback on published articles and refine them.

## Dependencies

-   `HashnodeService`: Interacts with the Hashnode API for publishing and analytics.
-   AI Agents: `TopicDiscoveryAgent`, `ArticlePlannerAgent`, `ContentGeneratorAgent`, `SEOAuditAgent`, `PublishingDecisionAgent`, `SocialAmplifierAgent`, `ABTestDesignerAgent`, `ArchiveCuratorAgent`, `PerformanceMonitorAgent`, `RefinerAgent`.
-   Database Models: `BlogTopicORM`, `ArticleORM`, `ScheduledPostORM`, `PerformanceORM`.
-   `Flask`: Used for application context.

## Methods

### `__init__(self, factory)`

-   **Description:** Initializes the controller with a session factory, logger, and Hashnode service.
    -   Calls the superclass constructor (`Controllers.__init__(factory)`).
    -   Sets up a logger for the controller.
    -   Initializes the `HashnodeService` if a `HASHNODE_TOKEN` is configured.
-   **Parameters:**
    -   `factory`: The session factory used to create database sessions.
-   **Returns:** None

### `async_init(self)`

-   **Description:** Asynchronously initializes the AI agents.
-   **Parameters:** None
-   **Returns:** None
-   **Details:**
    -   Retrieves the system admin user.
    -   Initializes each AI agent with the system admin's user ID.

### `init_app(self, app: Flask)`

-   **Description:** Registers the controller with a Flask application.
-   **Parameters:**
    -   `app`: The Flask application instance.
-   **Returns:** None
-   **Details:**
    -   Calls the superclass's `init_app` method.
    -   Initializes the AI agents within the Flask application context.

### `cron_topic_generator(self) -> int`

-   **Description:** Discovers blog topics and persists them to the database.
-   **Parameters:** None
-   **Returns:** The number of topics discovered.
-   **Details:**
    1.  Fetches the Hashnode sitemap.
    2.  Runs the `TopicDiscoveryAgent` to discover topics.
    3.  Persists the discovered topics to the `BlogTopicORM` database table.

### `cron_article_creator(self) -> int`

-   **Description:** Creates article drafts and persists them to the database.
-   **Parameters:** None
-   **Returns:** The number of articles created.
-   **Details:**
    1.  Iterates over all topics in the `BlogTopicORM` table.
    2.  Checks if an article already exists for the topic.
    3.  Runs the `ArticlePlannerAgent` to generate an outline.
    4.  Runs the `ContentGeneratorAgent` to generate content.
    5.  Generates a cover image and social card.
    6.  Creates a draft post on Hashnode using the `HashnodeService`.
    7.  Persists the article to the `ArticleORM` database table.

### `cron_draft_scheduler(self) -> int`

-   **Description:** Schedules drafts for publishing.
-   **Parameters:** None
-   **Returns:** The number of drafts scheduled.
-   **Details:**
    1.  Iterates over all articles that are not yet scheduled.
    2.  Creates a `ScheduledPostORM` record for each article, scheduling it for publishing at a specific time.

### `cron_feedback_gatherer(self) -> int | None`

-   **Description:** Pulls Hashnode analytics into the `PerformanceORM` table.
-   **Parameters:** None
-   **Returns:** The number of analytics collected or None if an error occurred.
-   **Details:**
    1.  Retrieves user information from Hashnode.
    2.  Iterates over all scheduled posts with a status of "live."
    3.  Retrieves analytics for each post from Hashnode.
    4.  Persists the analytics to the `PerformanceORM` database table.

### `fetch_hashnode_sitemap(self) -> Dict[str, List[str]]`

-   **Description:** Fetches the Hashnode sitemap.
-   **Parameters:** None
-   **Returns:** A dictionary containing a list of post slugs.
-   **Details:**
    1.  Retrieves user information from Hashnode to extract the domain.
    2.  Fetches the sitemap XML from Hashnode.
    3.  Parses the XML to extract the post slugs.

### `list_hashnode_posts(self, page: int = 0, limit: int = 10) -> Dict[str, Any]`

-   **Description:** Lists posts from Hashnode.
-   **Parameters:**
    -   `page` (int): The page number to retrieve (default: 0).
    -   `limit` (int): The number of posts to retrieve per page (default: 10).
-   **Returns:** A dictionary containing a list of posts.
-   **Details:**
    1.  Retrieves user information from Hashnode to extract the publication ID.
    2.  Lists the posts using the `HashnodeService`.

### `get_hashnode_analytics(self, post_id: str) -> Dict[str, Any]`

-   **Description:** Gets analytics for a specific post from Hashnode.
-   **Parameters:**
    -   `post_id` (str): The ID of the post to retrieve analytics for.
-   **Returns:** A dictionary containing the analytics data.
-   **Details:**
    1.  Retrieves user information from Hashnode to extract the publication ID.
    2.  Retrieves the analytics using the `HashnodeService`.

### `generate_and_publish_post(self, site_map: Dict[str, List[str]], publication_id: str, publish: bool = False) -> Dict[str, Any]`

-   **Description:** Generates and publishes or schedules a post to Hashnode.
-   **Parameters:**
    -   `site_map` (Dict[str, List[str]]): The sitemap to use for topic discovery.
    -   `publication_id` (str): The ID of the Hashnode publication.
    -   `publish` (bool): Whether to publish the post immediately (default: False).
-   **Returns:** A dictionary containing the status of the operation and the Hashnode ID and slug of the post.
-   **Details:**
    1.  Runs the `TopicDiscoveryAgent` to discover topics.
    2.  Runs the `ArticlePlannerAgent` to generate an outline.
    3.  Runs the `ContentGeneratorAgent` to generate content.
    4.  Runs the `SEOAuditAgent` to audit the content.
    5.  Runs the `PublishingDecisionAgent` to determine whether to publish the post.
    6.  Creates a draft post on Hashnode using the `HashnodeService`.

### `refine_existing_post(self, post_id: str) -> Dict[str, Any]`

-   **Description:** Refines an existing post on Hashnode based on analytics data.
-   **Parameters:**
    -   `post_id` (str): The ID of the post to refine.
-   **Returns:** A dictionary containing the status of the operation and the refinement data.
-   **Details:**
    1.  Retrieves user information from Hashnode to extract the publication ID.
    2.  Retrieves the analytics for the post from Hashnode.
    3.  Runs the `RefinerAgent` to generate refinement suggestions.

## Input Validation

-   The controller relies on the underlying services and agents to handle input validation.
-   It checks for the presence of required data (e.g., user, job, CV) before proceeding with analysis or generation.

## Error Handling

-   The `@error_handler` decorator is used to wrap most methods, providing a consistent way to catch exceptions, log errors, and return structured error responses.
-   The controller logs important events and errors to provide insights into the system's behavior.

## Notes

-   The controller relies heavily on other services and agents to perform its tasks, so ensure those dependencies are properly configured.
-   The controller makes extensive use of asynchronous operations to improve performance.
-   Many methods of this controller are marked as deprecated, and are being superseded by automated cron jobs.