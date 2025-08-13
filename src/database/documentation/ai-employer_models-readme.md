# employer_models.py Documentation

## Overview

This module defines Pydantic models for representing employer data and related entities. It includes models for employer profiles and employer invitations.

## Models

### Employer

Represents an employer profile.

*   `employer_id`: Unique identifier for the employer (UUID).
*   `user_uid`: Linked Auth0/Firebase UID.
*   `company_id`: The Company ID the Employer represents.
*   `is_verified`: Admin-approved status.
*   `is_admin`: Admin-approved status.
*   `verification_token`: Optional verification token.
*   `verification_token_expires_at`: Optional expiration timestamp for the verification token.
*   `created_at`: Timestamp when the employer profile was created.
*   `updated_at`: Timestamp when the employer profile was last updated.
*   `full_name`: Employer's full name.
*   `job_title`: Employer's position at the company.
*   `profile_picture_url`: URL to employer's profile picture.
*   `bio`: Short professional bio.
*   `company_email`: Professional email address.
*   `personal_email`: Personal email address (optional).
*   `phone_number`: Phone number in E.164 format.
*   `alternate_phone`: Alternate phone number.
*   `linkedin_url`: LinkedIn profile URL.
*   `twitter_handle`: Twitter username.
*   `department`: Department within the company.
*   `hire_date`: Date joined the company.
*   `responsibilities`: List of job responsibilities.
*   `hiring_authority`: Has authority to make hiring decisions.
*   `signature`: Email signature block.

### EmployerInvitation

Represents an invitation sent to an employer to join a company.

*   `invitation_id`: Unique identifier for the invitation (UUID).
*   `employer_id`: The employer being invited.
*   `token`: Unique invitation token.
*   `created_at`: Timestamp when the invitation was created.
*   `expires_at`: Token expiration time.

## Relationships to SQL Models

This model corresponds to the following SQL models:

*   [`EmployerORM`](src/database/sql/employer.py:12)
*   [`EmployerInvitationORM`](src/database/sql/employer.py:117)

The Pydantic models map directly to their corresponding ORM models in `src/database/sql/employer.py`.