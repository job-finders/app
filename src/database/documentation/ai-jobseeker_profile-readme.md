# jobseeker_profile.py Documentation

## Overview

This module defines Pydantic models for representing job seeker profiles and related information, such as referral tracking, settings, and application details.

## Models

### HintPriority

Enum for the priority of a hint

* HIGH
* MEDIUM
* LOW

### Hint

Represents a hint for the user

* message: the message to display
* priority: the priority of the message, which can be HIGH, MEDIUM, or LOW
* context: the context the hint applies to, such as the profile or a specific application

### JobSeekerProfile

Represents a job seeker's profile.

*   `user_uid`: Foreign key to the Users model's uid.
*   `referrer_id`: ID of the referrer (if any).
*   `referral_count`: Number of successful referrals.
*   `referral_bonus_earned`: Referral bonus earned.
*   `first_name`: First name of the job seeker.
*   `last_name`: Last name of the job seeker.
*   `email`: Email address of the job seeker.
*   `bio`: Optional biography of the job seeker.
*   `profile_image_url`: Optional URL to the job seeker's profile image.
*   `has_disability`: Has disability
*   `alerts_enabled`: Indicates whether job alerts are enabled.
*   `receive_deadline_reminders`: Indicates whether deadline reminders are enabled.
*   `reminder_days_before`: Number of days before the deadline to send a reminder.
*   `last_reminded_at`: Timestamp of the last reminder sent.
*   `receive_company_updates`: Indicates whether to receive company updates.
*   `visibility`: Indicates whether the profile is visible to employers.
*   `last_updated`: Timestamp of the last profile update.
*   `verified_email`: Indicates whether the email address is verified.
*   `verified_phone`: Indicates whether the phone number is verified.
*   `verified_linkedin`: Indicates whether the LinkedIn profile is verified.
*   `verified_github`: Indicates whether the GitHub profile is verified.
*   `location`: Optional location of the job seeker.
*   `phone`: Optional phone number of the job seeker.
*   `website`: Optional website URL of the job seeker.
*   `linkedin`: Optional LinkedIn URL of the job seeker.
*   `github`: Optional GitHub URL of the job seeker.
*   `job_titles_of_interest`: Optional list of job titles of interest.
*   `industries_of_interest`: Optional list of industries of interest.
*   `locations_of_interest`: Optional list of locations of interest.
*   `remote_preference`: Optional remote preference.
*   `availability`: Optional availability information.
*   `expected_salary`: Optional expected salary.
*   `is_freelancer`: Is the jobseeker a freelancer
*   `freelance_skills`: List of skills for freelancing
*   `hourly_rate`: How much the jobseeker charges per hour
*   `freelance_experience`: text that explains experience with freelancing
*   `freelance_availability`: when the jobseeker is available for freelancing
*   `ip_address`: Optional IP address of the job seeker.
*   `device_finger_print`: Optional device fingerprint of the job seeker.

## Relationships to SQL Models

This model corresponds to the following SQL model:

*   [`JobSeekerProfileORM`](src/database/sql/jobseeker_profile.py:10)

The Pydantic models map directly to their corresponding ORM models in `src/database/sql/jobseeker_profile.py`.