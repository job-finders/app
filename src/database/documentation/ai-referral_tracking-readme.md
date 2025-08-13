# referral_tracking.py Documentation

## Overview

This module defines Pydantic models for representing referral tracking information. It includes models for referral statuses and job referrals.

## Models

### ReferralStatus

An enumeration of possible referral statuses:

*   `PENDING`: Referral is pending.
*   `APPLIED`: Referred user has applied for the job.
*   `INTERVIEWED`: Referred user has been interviewed.
*   `HIRED`: Referred user has been hired.
*   `REJECTED`: Referred user has been rejected.
*   `COMPLETED`: Referral process is completed.

### JobReferral

Represents a job referral.

*   `referral_id`: Unique identifier for the referral (UUID).
*   `job_id`: ID of the job being referred to.
*   `referrer_id`: ID of the user who made the referral.
*   `referred_email`: Email address of the referred user.
*   `referral_code`: Unique referral code for tracking.
*   `shared_at`: Timestamp when the referral was shared.
*   `application_id`: Optional ID of the application created through the referral.
*   `application_date`: Optional date the application was submitted.
*   `status`: Current status of the referral (from `ReferralStatus`).
*   `bonus_awarded`: Bonus amount awarded for the referral.
*   `bonus_paid`: Indicates whether the bonus has been paid.
*   `created_at`: Timestamp when the referral was created.
*   `updated_at`: Timestamp when the referral was updated.

## Relationships to SQL Models

There are no direct SQL models related to these Pydantic models.
These models are primarily used for data transfer and validation within the application's referral tracking system and might be used in conjunction with other ORM models, but they do not have direct counterparts in the database schema.