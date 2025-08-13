# Documentation for admin_models.py

This file defines the data models and enums used for admin moderation.

## UserStatusFlagEnum

An enum defining the possible statuses for a user:

- `FLAGGED`: User is flagged for review.
- `RESOLVED`: User has been reviewed and the flag has been resolved.
- `ISOLATED`: User is isolated from the community.
- `SUSPENDED`: User is suspended from the platform.
- `DELETED`: User is deleted from the platform.

## RiskRecommendation

An enum defining the possible risk recommendations for a user:

- `LOW`: User poses a low risk.
- `MONITOR`: User should be monitored for suspicious activity.
- `ISOLATE`: User should be isolated from the community.
- `SUSPEND`: User should be suspended from the platform.
- `DELETE`: User should be deleted from the platform.

## RiskThreshold

A Pydantic model defining the thresholds for each risk recommendation:

- `label`: The RiskRecommendation label.
- `min_score`: The minimum score for this risk level (inclusive).
- `max_score`: The maximum score for this risk level (exclusive).

## FlaggedUser

A Pydantic model representing a flagged user record:

- `flag_id`: A unique identifier for the flag.
- `reference_id`: The ID of the user being flagged.
- `reason`: The reason for flagging the user.
- `flagged_by`: The admin who flagged the user.
- `date_flagged_at`: The date and time the user was flagged.
- `status`: The status of the flag (UserStatusFlagEnum).

## AdminModel

A Pydantic model representing the admin moderation model, which processes flagged user history and recommends risk status using age-based decay scoring:

- `admin_id`: A unique identifier for the admin model.
- `admin_users`: The ID of the admin user.
- `flagged_records`: A list of FlaggedUser records.

### Methods

- `_decayed_weight(flagged_date: AwareDatetime) -> float`: Computes the decayed score for a single flag using exponential decay. The older the flag, the less it contributes.
- `_calculate_user_scores() -> Dict[str, float]`: Calculates decayed risk scores for each unique user. Only counts flags with status FLAGGED or RESOLVED.
- `user_risk_recommendations -> Dict[str, RiskRecommendation]`: Returns a mapping of users to their recommended risk category based on decayed score.
- `high_risk_users -> List[str]`: Users that are recommended for DELETE due to persistent or recent violations.
- `isolation_candidates -> List[str]`: Users that should be considered for ISOLATE, SUSPEND, or DELETE.
- `generate_user_risk_recommendations() -> Dict[str, RiskRecommendation]`: Evaluates all flagged user records and returns a recommendation for each user.