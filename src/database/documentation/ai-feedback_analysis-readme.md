# feedback_analysis.py Documentation

## Overview

This module defines Pydantic models for representing feedback analysis related to blog content. It includes models for article feedback entries, feedback analysis summaries, and blog prompt feedback.

## Models

### ArticleFeedbackEntry

Represents a single feedback entry for a blog article.

*   `article_id`: The ID of the article.
*   `feedback_score`: A numerical score representing the feedback (e.g., 1-5 stars).
*   `comments`: Optional comments provided with the feedback.

### FeedbackAnalysisSummary

Represents a summary of feedback analysis for a collection of articles.

*   `high_performing_topics`: A list of topics that are performing well based on feedback.
*   `underperforming_topics`: A list of topics that are not performing well based on feedback.
*   `average_score`: The average feedback score across all articles.
*   `insights`: A list of insights derived from the feedback analysis.
*   `new_prompt_ideas`: A list of new prompt ideas generated from the feedback analysis.

### BlogFeedbackInput

Represents input data for blog feedback.

*   `prompt_id`: The ID of the blog prompt.
*   `views`: Number of views for this prompt
*   `likes`: Number of likes for this prompt
*   `comments`: Number of comments for this prompt

### BlogFeedbackOutput

Represents output data for blog feedback.

*   `prompt_id`: The ID of the blog prompt.
*   `feedback_score`: The calculated feedback score for the prompt.
*   `views`: Number of views for this prompt
*   `likes`: Number of likes for this prompt
*   `comments`: Number of comments for this prompt
*   `submitted_at`: The timestamp when the feedback was submitted.

### BlogPrompt

Represents a blog prompt.

*   `blog_prompt_id`: The ID of the blog prompt.
*   `content`: The content of the blog prompt.
*   `topic_id`: The ID of the blog topic.
*   `created_at`: The timestamp when the blog prompt was created.
*   `feedback_score`: The feedback score of the blog prompt.
*   `topic`: The `BlogTopic` object this prompt belongs to.

### BlogTopic

Represents a blog topic.

*   `blog_topic_id`: The ID of the blog topic.
*   `title`: The title of the blog topic.
*   `created_at`: The timestamp when the blog topic was created.
*   `prompts`: A list of `BlogPrompt` objects belonging to this topic.
*   `description`: Description of the topic

## Relationships to SQL Models

There are no direct SQL models related to these pydantic models.
These models are primarily used for data transfer and validation within the application's business logic, and might be used in conjunction with other ORM models, but they do not have direct counterparts in the database schema.