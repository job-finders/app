# notifications.py Documentation

## Overview

This module defines Pydantic models for representing notifications within the Job Finders platform. It includes models for defining notification channels, notification types, and notification payloads.

## Models

### NotificationChannel

An enumeration of possible notification channels:

*   `email`: Email notification.
*   `sms`: SMS notification.
*   `in_app`: In-app notification.

### NotificationType

An enumeration of possible notification types:

*   `email_verification`: Email verification notification.
*   `job_alert`: Job alert notification.
*   `applicant_applied`: Applicant applied for a job notification.

### NotificationPayload

Represents the payload for a notification.

*   `subject`: Optional subject of the notification.
*   `body`: Optional body of the notification.
*   `data`: A dictionary containing additional data for the notification.

### BaseNotification

Represents a base notification.

*   `id`: Unique identifier for the notification (UUID).
*   `user_id`: Optional ID of the user receiving the notification.
*   `company_id`: Optional ID of the company sending the notification.
*   `email`: Optional email address to send the notification to.
*   `notification_type`: The type of notification (from `NotificationType`).
*   `channel`: The channel to send the notification through (from `NotificationChannel`).
*   `payload`: The `NotificationPayload` for the notification.
*   `is_sent`: Indicates whether the notification has been sent.
*   `sent_at`: The date and time the notification was sent.
*   `created_at`: The date and time the notification was created.

## Relationships to SQL Models

There are no direct SQL models related to these pydantic models.
These models are primarily used for data transfer and validation within the application's notification system and might be used in conjunction with other ORM models, but they do not have direct counterparts in the database schema.