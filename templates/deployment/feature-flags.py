"""
JobFinders Template Migration Feature Flags System

This module provides feature flag functionality to enable gradual rollout
of the new template system while maintaining backward compatibility.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from functools import wraps

logger = logging.getLogger(__name__)


class FeatureFlagStatus(Enum):
    """Feature flag status enumeration"""
    DISABLED = "disabled"
    ENABLED = "enabled"
    ROLLOUT = "rollout"
    TESTING = "testing"


class RolloutStrategy(Enum):
    """Rollout strategy enumeration"""
    PERCENTAGE = "percentage"
    USER_LIST = "user_list"
    USER_TYPE = "user_type"
    GEOGRAPHIC = "geographic"
    TIME_BASED = "time_based"


@dataclass
class FeatureFlag:
    """Feature flag configuration"""
    name: str
    status: FeatureFlagStatus
    description: str
    rollout_strategy: Optional[RolloutStrategy] = None
    rollout_percentage: int = 0
    target_users: List[str] = None
    target_user_types: List[str] = None
    target_regions: List[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime = None
    updated_at: datetime = None
    created_by: str = ""

    def __post_init__(self):
        if self.target_users is None:
            self.target_users = []
        if self.target_user_types is None:
            self.target_user_types = []
        if self.target_regions is None:
            self.target_regions = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


class FeatureFlagManager:
    """Feature flag management system"""

    def __init__(self, config_path: str = "templates/deployment/feature-flags.json"):
        self.config_path = config_path
        self.flags: Dict[str, FeatureFlag] = {}
        self.load_flags()

    def load_flags(self):
        """Load feature flags from configuration file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    for flag_name, flag_data in data.items():
                        # Convert datetime strings back to datetime objects
                        if flag_data.get('created_at'):
                            flag_data['created_at'] = datetime.fromisoformat(flag_data['created_at'])
                        if flag_data.get('updated_at'):
                            flag_data['updated_at'] = datetime.fromisoformat(flag_data['updated_at'])
                        if flag_data.get('start_date'):
                            flag_data['start_date'] = datetime.fromisoformat(flag_data['start_date'])
                        if flag_data.get('end_date'):
                            flag_data['end_date'] = datetime.fromisoformat(flag_data['end_date'])

                        # Convert enum strings back to enums
                        flag_data['status'] = FeatureFlagStatus(flag_data['status'])
                        if flag_data.get('rollout_strategy'):
                            flag_data['rollout_strategy'] = RolloutStrategy(flag_data['rollout_strategy'])

                        self.flags[flag_name] = FeatureFlag(**flag_data)
            else:
                self.create_default_flags()
        except Exception as e:
            logger.error(f"Error loading feature flags: {e}")
            self.create_default_flags()

    def save_flags(self):
        """Save feature flags to configuration file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            # Convert flags to serializable format
            serializable_flags = {}
            for flag_name, flag in self.flags.items():
                flag_dict = asdict(flag)
                # Convert datetime objects to ISO strings
                if flag_dict.get('created_at'):
                    flag_dict['created_at'] = flag_dict['created_at'].isoformat()
                if flag_dict.get('updated_at'):
                    flag_dict['updated_at'] = flag_dict['updated_at'].isoformat()
                if flag_dict.get('start_date'):
                    flag_dict['start_date'] = flag_dict['start_date'].isoformat()
                if flag_dict.get('end_date'):
                    flag_dict['end_date'] = flag_dict['end_date'].isoformat()

                # Convert enums to strings
                flag_dict['status'] = flag_dict['status'].value
                if flag_dict.get('rollout_strategy'):
                    flag_dict['rollout_strategy'] = flag_dict['rollout_strategy'].value

                serializable_flags[flag_name] = flag_dict

            with open(self.config_path, 'w') as f:
                json.dump(serializable_flags, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving feature flags: {e}")

    def create_default_flags(self):
        """Create default feature flags for template migration"""
        default_flags = {
            'new_template_system': FeatureFlag(
                name='new_template_system',
                status=FeatureFlagStatus.DISABLED,
                description='Enable new template system globally',
                rollout_strategy=RolloutStrategy.PERCENTAGE,
                rollout_percentage=0,
                created_by='system'
            ),
            'new_auth_templates': FeatureFlag(
                name='new_auth_templates',
                status=FeatureFlagStatus.DISABLED,
                description='Enable new authentication templates',
                rollout_strategy=RolloutStrategy.PERCENTAGE,
                rollout_percentage=0,
                created_by='system'
            ),
            'new_job_templates': FeatureFlag(
                name='new_job_templates',
                status=FeatureFlagStatus.DISABLED,
                description='Enable new job listing and detail templates',
                rollout_strategy=RolloutStrategy.PERCENTAGE,
                rollout_percentage=0,
                created_by='system'
            ),
            'new_company_templates': FeatureFlag(
                name='new_company_templates',
                status=FeatureFlagStatus.DISABLED,
                description='Enable new company and employer templates',
                rollout_strategy=RolloutStrategy.PERCENTAGE,
                rollout_percentage=0,
                created_by='system'
            ),
            'new_admin_templates': FeatureFlag(
                name='new_admin_templates',
                status=FeatureFlagStatus.DISABLED,
                description='Enable new admin dashboard templates',
                rollout_strategy=RolloutStrategy.USER_TYPE,
                target_user_types=['admin'],
                created_by='system'
            ),
            'new_error_pages': FeatureFlag(
                name='new_error_pages',
                status=FeatureFlagStatus.DISABLED,
                description='Enable new error page templates',
                rollout_strategy=RolloutStrategy.PERCENTAGE,
                rollout_percentage=0,
                created_by='system'
            )
        }

        self.flags.update(default_flags)
        self.save_flags()

    def is_enabled(self, flag_name: str, user_id: str = None, user_type: str = None,
                   region: str = None, request_ip: str = None) -> bool:
        """Check if a feature flag is enabled for the given context"""
        if flag_name not in self.flags:
            logger.warning(f"Feature flag '{flag_name}' not found")
            return False

        flag = self.flags[flag_name]

        # Check if flag is globally disabled
        if flag.status == FeatureFlagStatus.DISABLED:
            return False

        # Check if flag is globally enabled
        if flag.status == FeatureFlagStatus.ENABLED:
            return True

        # Check time-based constraints
        now = datetime.utcnow()
        if flag.start_date and now < flag.start_date:
            return False
        if flag.end_date and now > flag.end_date:
            return False

        # Apply rollout strategy
        if flag.rollout_strategy == RolloutStrategy.PERCENTAGE:
            return self._check_percentage_rollout(flag, user_id)
        elif flag.rollout_strategy == RolloutStrategy.USER_LIST:
            return user_id in flag.target_users if user_id else False
        elif flag.rollout_strategy == RolloutStrategy.USER_TYPE:
            return user_type in flag.target_user_types if user_type else False
        elif flag.rollout_strategy == RolloutStrategy.GEOGRAPHIC:
            return region in flag.target_regions if region else False
        elif flag.rollout_strategy == RolloutStrategy.TIME_BASED:
            return self._check_time_based_rollout(flag)

        return False

    def _check_percentage_rollout(self, flag: FeatureFlag, user_id: str) -> bool:
        """Check percentage-based rollout"""
        if not user_id:
            return False

        # Use hash of user_id and flag name for consistent results
        hash_input = f"{user_id}:{flag.name}"
        hash_value = hash(hash_input) % 100
        return hash_value < flag.rollout_percentage

    def _check_time_based_rollout(self, flag: FeatureFlag) -> bool:
        """Check time-based rollout"""
        now = datetime.utcnow()
        if flag.start_date and flag.end_date:
            return flag.start_date <= now <= flag.end_date
        return True

    def enable_flag(self, flag_name: str, user_id: str = "system"):
        """Enable a feature flag"""
        if flag_name in self.flags:
            self.flags[flag_name].status = FeatureFlagStatus.ENABLED
            self.flags[flag_name].updated_at = datetime.utcnow()
            self.save_flags()
            logger.info(f"Feature flag '{flag_name}' enabled by {user_id}")

    def disable_flag(self, flag_name: str, user_id: str = "system"):
        """Disable a feature flag"""
        if flag_name in self.flags:
            self.flags[flag_name].status = FeatureFlagStatus.DISABLED
            self.flags[flag_name].updated_at = datetime.utcnow()
            self.save_flags()
            logger.info(f"Feature flag '{flag_name}' disabled by {user_id}")

    def set_rollout_percentage(self, flag_name: str, percentage: int, user_id: str = "system"):
        """Set rollout percentage for a feature flag"""
        if flag_name in self.flags and 0 <= percentage <= 100:
            self.flags[flag_name].rollout_percentage = percentage
            self.flags[flag_name].status = FeatureFlagStatus.ROLLOUT
            self.flags[flag_name].updated_at = datetime.utcnow()
            self.save_flags()
            logger.info(f"Feature flag '{flag_name}' rollout set to {percentage}% by {user_id}")

    def add_target_user(self, flag_name: str, user_id: str, admin_user: str = "system"):
        """Add a user to the target list for a feature flag"""
        if flag_name in self.flags:
            if user_id not in self.flags[flag_name].target_users:
                self.flags[flag_name].target_users.append(user_id)
                self.flags[flag_name].updated_at = datetime.utcnow()
                self.save_flags()
                logger.info(f"User {user_id} added to feature flag '{flag_name}' by {admin_user}")

    def remove_target_user(self, flag_name: str, user_id: str, admin_user: str = "system"):
        """Remove a user from the target list for a feature flag"""
        if flag_name in self.flags:
            if user_id in self.flags[flag_name].target_users:
                self.flags[flag_name].target_users.remove(user_id)
                self.flags[flag_name].updated_at = datetime.utcnow()
                self.save_flags()
                logger.info(f"User {user_id} removed from feature flag '{flag_name}' by {admin_user}")

    def get_flag_status(self, flag_name: str) -> Dict[str, Any]:
        """Get detailed status of a feature flag"""
        if flag_name not in self.flags:
            return {"error": "Flag not found"}

        flag = self.flags[flag_name]
        return {
            "name": flag.name,
            "status": flag.status.value,
            "description": flag.description,
            "rollout_strategy": flag.rollout_strategy.value if flag.rollout_strategy else None,
            "rollout_percentage": flag.rollout_percentage,
            "target_users_count": len(flag.target_users),
            "target_user_types": flag.target_user_types,
            "target_regions": flag.target_regions,
            "created_at": flag.created_at.isoformat(),
            "updated_at": flag.updated_at.isoformat(),
            "created_by": flag.created_by
        }

    def list_flags(self) -> Dict[str, Dict[str, Any]]:
        """List all feature flags with their status"""
        return {name: self.get_flag_status(name) for name in self.flags.keys()}


# Global feature flag manager instance
feature_flags = FeatureFlagManager()


def feature_flag_required(flag_name: str, fallback_template: str = None):
    """Decorator to check feature flags for template routes"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user context from request or session
            user_id = getattr(g, 'user_id', None) if 'g' in globals() else None
            user_type = getattr(g, 'user_type', None) if 'g' in globals() else None

            if feature_flags.is_enabled(flag_name, user_id=user_id, user_type=user_type):
                return func(*args, **kwargs)
            else:
                if fallback_template:
                    # Render fallback template
                    from flask import render_template
                    return render_template(fallback_template, **kwargs)
                else:
                    # Return original function result
                    return func(*args, **kwargs)

        return wrapper

    return decorator


def get_template_path(base_template: str, new_template: str, flag_name: str,
                      user_id: str = None, user_type: str = None) -> str:
    """Get the appropriate template path based on feature flags"""
    if feature_flags.is_enabled(flag_name, user_id=user_id, user_type=user_type):
        return new_template
    return base_template


# Template migration helper functions
def should_use_new_templates(user_id: str = None, user_type: str = None) -> bool:
    """Check if new template system should be used"""
    return feature_flags.is_enabled('new_template_system', user_id=user_id, user_type=user_type)


def get_auth_template(template_name: str, user_id: str = None) -> str:
    """Get authentication template path"""
    if feature_flags.is_enabled('new_auth_templates', user_id=user_id):
        return f"templates/auth/{template_name}"
    return f"template/{template_name}"


def get_job_template(template_name: str, user_id: str = None) -> str:
    """Get job template path"""
    if feature_flags.is_enabled('new_job_templates', user_id=user_id):
        return f"templates/jobs/{template_name}"
    return f"template/jobs/{template_name}"


def get_company_template(template_name: str, user_id: str = None, user_type: str = None) -> str:
    """Get company template path"""
    if feature_flags.is_enabled('new_company_templates', user_id=user_id, user_type=user_type):
        return f"templates/company/{template_name}"
    return f"template/company/{template_name}"


def get_admin_template(template_name: str, user_id: str = None, user_type: str = None) -> str:
    """Get admin template path"""
    if feature_flags.is_enabled('new_admin_templates', user_id=user_id, user_type=user_type):
        return f"templates/admin/{template_name}"
    return f"template/admin/{template_name}"


def get_error_template(template_name: str, user_id: str = None) -> str:
    """Get error template path"""
    if feature_flags.is_enabled('new_error_pages', user_id=user_id):
        return f"templates/error/{template_name}"
    return f"template/{template_name}"
