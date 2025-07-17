# Notifications System Refactor Plan – JobFinders.app

## 📁 Phase 1: Core Refactor – Models & Architecture
- [ ] Redesign `NotificationsORM` to support:
  - `user_id` or `company_id` (nullable, support both sides)
  - `notification_type` (enum: `email_verification`, `job_alert`, `applicant_applied`, etc.)
  - `channel` (email, sms, in_app — futureproof)
  - `payload` (JSON blob for event data)
  - `is_sent` (bool)
  - `sent_at` (datetime)
- [ ] Update Pydantic models to reflect the new structure (e.g., `BaseNotification`, `EmailNotificationPayload`, etc.)
- [ ] Introduce notification event types as constants/enums
- [ ] Introduce user/company notification preferences model:
  - frequency (immediate, daily, weekly)
  - subscribed events

## ⚙️ Phase 2: Notifications Service Layer
- [ ] Create a `NotificationService` class to:
  - Handle creation of notifications by event type
  - Handle sending logic (delegate to email/sms/in-app workers)
- [ ] Make `NotificationsController` a thin wrapper around `NotificationService`
- [ ] Refactor email sending to be template-driven + payload-based
- [ ] Move all `url_for`, context generation logic into service layer or template helpers

## 🔁 Phase 3: Background Tasks & Async Safety
- [ ] Replace daemon with proper background task queue (Celery, APScheduler, or FastAPI/Flask background tasks)
- [ ] Make all notification-sending calls non-blocking and retryable
- [ ] Add logging, retry on failure, and exponential backoff

## 📬 Phase 4: Notification Triggers (Event Sources)
- [ ] Trigger email verification on user/company registration
- [ ] Trigger job alert digest based on user subscriptions (daily or weekly)
- [ ] Trigger employer alert when a candidate applies
- [ ] Add support for internal app events to dispatch notifications

## 🧪 Phase 5: Testing, Logging, Monitoring
- [ ] Unit tests for notification creation logic
- [ ] Integration tests for major workflows (e.g., verification, job alerts)
- [ ] Add Sentry or similar logging for errors
- [ ] Add monitoring for failed notifications (e.g., dead-letter queue)

## 🚀 Phase 6: In-App Notifications (Optional Next)
- [ ] Create UI for in-app notification center
- [ ] API endpoint: `/notifications/me` for users to see unread/past notifications
- [ ] Mark as read / delete
