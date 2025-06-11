from collections import defaultdict
from enum import Enum
from typing import List, Dict
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict, AwareDatetime

from src.database.constants import utc_time


class UserStatusFlagEnum(str, Enum):
    FLAGGED = "flagged"
    RESOLVED = "resolved"
    ISOLATED = "isolated"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class RiskRecommendation(str, Enum):
    LOW = "low"
    MONITOR = "monitor"
    ISOLATE = "isolate"
    SUSPEND = "suspend"
    DELETE = "recommend_delete"

    model_config = ConfigDict(from_attributes=True)

DECAY_HALF_LIFE_DAYS = 30  # Every 30 days, a record's weight is halved

class RiskThreshold(BaseModel):
    label: RiskRecommendation
    min_score: float  # inclusive
    max_score: float  # exclusive

    model_config = ConfigDict(from_attributes=True)

# Configurable risk levels
RISK_THRESHOLDS: list[RiskThreshold] = [
    RiskThreshold(label=RiskRecommendation.LOW, min_score=0.0, max_score=1.0),
    RiskThreshold(label=RiskRecommendation.MONITOR, min_score=1.0, max_score=2.0),
    RiskThreshold(label=RiskRecommendation.ISOLATE, min_score=2.0, max_score=3.5),
    RiskThreshold(label=RiskRecommendation.SUSPEND, min_score=3.5, max_score=5.0),
    RiskThreshold(label=RiskRecommendation.DELETE, min_score=5.0, max_score=float("inf")),
]

class FlaggedUser(BaseModel):
    flag_id: int = Field(default_factory=lambda: uuid4().int)
    reference_id: str
    reason: str
    flagged_by: str
    date_flagged_at: AwareDatetime
    status: str = Field(default=UserStatusFlagEnum.FLAGGED.value)

    model_config = ConfigDict(from_attributes=True)

class AdminModel(BaseModel):
    """
    Admin moderation model which processes flagged user history
    and recommends risk status using age-based decay scoring.
    """
    admin_id: int = Field(default_factory=lambda: uuid4().int)
    admin_users: str
    flagged_records: List[FlaggedUser] = []
    model_config = ConfigDict(from_attributes=True)

    @staticmethod
    def _decayed_weight(flagged_date: AwareDatetime) -> float:
        """
        Compute decayed score for a single flag using exponential decay.
        The older the flag, the less it contributes.
        """
        days_old = (utc_time() - flagged_date).days
        return 0.5 ** (days_old / DECAY_HALF_LIFE_DAYS)

    def _calculate_user_scores(self) -> Dict[str, float]:
        """
        Calculates decayed risk scores for each unique user (by reference_id).
        Only counts flags with status FLAGGED or RESOLVED.
        """
        scores = defaultdict(float)

        for record in self.flagged_records:
            if record.status in [UserStatusFlagEnum.FLAGGED, UserStatusFlagEnum.RESOLVED]:
                weight = self._decayed_weight(record.date_flagged_at)
                scores[record.reference_id] += weight

        return dict(scores)

    @property
    def user_risk_recommendations(self) -> Dict[str, RiskRecommendation]:
        """
        Returns a mapping of users to their recommended risk category based on decayed score.
        Thresholds are defined in the RISK_THRESHOLDS list.
        """
        scores = self._calculate_user_scores()
        recommendations = {}

        for ref_id, score in scores.items():
            for threshold in RISK_THRESHOLDS:
                if threshold.min_score <= score < threshold.max_score:
                    recommendations[ref_id] = threshold.label
                    break  # Stop at first matching threshold

        return recommendations


    @property
    def high_risk_users(self) -> List[str]:
        """
        Users that are recommended for DELETE due to persistent or recent violations.
        """
        return [
            ref_id for ref_id, risk in self.user_risk_recommendations.items()
            if risk == RiskRecommendation.DELETE
        ]

    @property
    def isolation_candidates(self) -> List[str]:
        """
        Users that should be considered for ISOLATE, SUSPEND, or DELETE.
        """
        return [
            ref_id for ref_id, risk in self.user_risk_recommendations.items()
            if risk in [RiskRecommendation.ISOLATE, RiskRecommendation.SUSPEND, RiskRecommendation.DELETE]
        ]

    def generate_user_risk_recommendations(self) -> Dict[str, RiskRecommendation]:
        """
        Evaluates all flagged user records and returns a recommendation for each user.

        The score is calculated using an age-decayed model. Flags with status 'FLAGGED' and 'RESOLVED'
        are considered. Users are mapped to a risk category using configured risk thresholds.
        """
        scores = self._calculate_user_scores()
        recommendations = {}

        for ref_id, score in scores.items():
            for threshold in RISK_THRESHOLDS:
                if threshold.min_score <= score < threshold.max_score:
                    recommendations[ref_id] = threshold.label
                    break

        return recommendations
