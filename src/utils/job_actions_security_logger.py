"""
Job Actions Security Logger

Comprehensive security event logging for job actions operations.
This module provides centralized security logging with proper context,
threat detection, and audit trail capabilities.

Security Events Tracked:
- Authentication failures and suspicious login attempts
- Authorization violations and privilege escalation attempts
- Input validation failures and potential injection attacks
- Rate limiting violations and abuse patterns
- Data access violations and unauthorized operations
- Performance anomalies that may indicate attacks
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

from src.logger import init_logger


class SecurityEventType(Enum):
    """Enumeration of security event types for consistent logging"""
    AUTHENTICATION_FAILURE = "authentication_failure"
    AUTHORIZATION_VIOLATION = "authorization_violation"
    INPUT_VALIDATION_FAILURE = "input_validation_failure"
    RATE_LIMIT_VIOLATION = "rate_limit_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_ACCESS_VIOLATION = "data_access_violation"
    PERFORMANCE_ANOMALY = "performance_anomaly"
    INJECTION_ATTEMPT = "injection_attempt"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    AUDIT_TRAIL = "audit_trail"


class SecuritySeverity(Enum):
    """Security event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class JobActionsSecurityLogger:
    """
    Centralized security logging for job actions operations.
    
    This class provides comprehensive security event logging with proper
    context information, threat detection capabilities, and audit trail
    functionality for all job actions operations.
    
    Features:
        - Structured security event logging with consistent format
        - IP address tracking and geolocation context
        - User behavior pattern analysis
        - Threat detection and alerting
        - Audit trail for compliance requirements
        - Performance monitoring for security implications
    """

    def __init__(self):
        """
        Initialize the security logger with proper configuration.
        
        Sets up logging infrastructure, threat detection patterns,
        and security monitoring capabilities.
        """
        self.logger = init_logger("JobActionsSecurityLogger")
        self.audit_logger = init_logger("JobActionsAuditTrail")
        self.threat_logger = init_logger("JobActionsThreatDetection")

        # Security thresholds for anomaly detection
        self.rate_limit_threshold = 100  # requests per minute
        self.validation_failure_threshold = 10  # failures per minute
        self.performance_threshold = 5.0  # seconds

        # Suspicious patterns for detection
        self.suspicious_patterns = {
            'sql_injection': ['union', 'select', 'drop', 'insert', 'update', 'delete', '--', ';'],
            'xss_attempt': ['<script', 'javascript:', 'onerror=', 'onload=', 'eval('],
            'path_traversal': ['../', '..\\\\', '/etc/', '/proc/', 'c:\\\\'],
            'command_injection': ['|', '&&', '||', ';', '`', '$(']
        }

    def log_security_event(
            self,
            event_type: SecurityEventType,
            severity: SecuritySeverity,
            user_id: Optional[str] = None,
            job_id: Optional[str] = None,
            action: Optional[str] = None,
            ip_address: Optional[str] = None,
            user_agent: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None,
            request_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a security event with comprehensive context information.
        
        Args:
            event_type: Type of security event from SecurityEventType enum
            severity: Severity level from SecuritySeverity enum
            user_id: User ID involved in the event (if applicable)
            job_id: Job ID involved in the event (if applicable)
            action: Specific action being performed
            ip_address: Client IP address
            user_agent: Client user agent string
            details: Additional event-specific details
            request_data: Request data that triggered the event
        """
        try:
            # Build comprehensive security event context
            security_event = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type.value,
                "severity": severity.value,
                "user_id": user_id,
                "job_id": job_id,
                "action": action,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "details": details or {},
                "request_data": self._sanitize_request_data(request_data) if request_data else None
            }

            # Log to appropriate logger based on severity
            log_message = f"Security Event: {event_type.value} | Severity: {severity.value} | User: {user_id} | Action: {action}"

            if severity in [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]:
                self.threat_logger.error(log_message, extra={"security_event": security_event})
            elif severity == SecuritySeverity.MEDIUM:
                self.logger.warning(log_message, extra={"security_event": security_event})
            else:
                self.logger.info(log_message, extra={"security_event": security_event})

            # Always log to audit trail for compliance
            self.audit_logger.info(f"AUDIT: {log_message}", extra={"audit_event": security_event})

            # Trigger alerts for critical events
            if severity == SecuritySeverity.CRITICAL:
                self._trigger_security_alert(security_event)

        except Exception as e:
            # Fallback logging to prevent security logging failures from breaking the application
            self.logger.error(f"Failed to log security event: {e}", exc_info=True)

    def log_authentication_failure(
            self,
            user_id: Optional[str],
            reason: str,
            ip_address: Optional[str] = None,
            user_agent: Optional[str] = None,
            attempt_count: int = 1
    ) -> None:
        """
        Log authentication failure events with threat detection.
        
        Args:
            user_id: User ID that failed authentication
            reason: Reason for authentication failure
            ip_address: Client IP address
            user_agent: Client user agent
            attempt_count: Number of consecutive failures
        """
        severity = SecuritySeverity.MEDIUM
        if attempt_count >= 5:
            severity = SecuritySeverity.HIGH
        elif attempt_count >= 10:
            severity = SecuritySeverity.CRITICAL

        self.log_security_event(
            event_type=SecurityEventType.AUTHENTICATION_FAILURE,
            severity=severity,
            user_id=user_id,
            action="authentication",
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "failure_reason": reason,
                "attempt_count": attempt_count,
                "threat_level": "brute_force" if attempt_count >= 5 else "normal"
            }
        )

    def log_authorization_violation(
            self,
            user_id: str,
            action: str,
            resource: str,
            required_permission: str,
            ip_address: Optional[str] = None
    ) -> None:
        """
        Log authorization violation attempts.
        
        Args:
            user_id: User ID attempting unauthorized action
            action: Action being attempted
            resource: Resource being accessed
            required_permission: Permission required for the action
            ip_address: Client IP address
        """
        self.log_security_event(
            event_type=SecurityEventType.AUTHORIZATION_VIOLATION,
            severity=SecuritySeverity.HIGH,
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            details={
                "resource": resource,
                "required_permission": required_permission,
                "violation_type": "privilege_escalation"
            }
        )

    def log_input_validation_failure(
            self,
            user_id: Optional[str],
            action: str,
            validation_errors: Dict[str, Any],
            input_data: Dict[str, Any],
            ip_address: Optional[str] = None
    ) -> None:
        """
        Log input validation failures with injection attempt detection.
        
        Args:
            user_id: User ID submitting invalid input
            action: Action being performed
            validation_errors: Validation error details
            input_data: Input data that failed validation
            ip_address: Client IP address
        """
        # Detect potential injection attempts
        threat_detected = self._detect_injection_attempts(input_data)
        severity = SecuritySeverity.HIGH if threat_detected else SecuritySeverity.LOW

        self.log_security_event(
            event_type=SecurityEventType.INPUT_VALIDATION_FAILURE,
            severity=severity,
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            details={
                "validation_errors": validation_errors,
                "threat_detected": threat_detected,
                "injection_patterns": self._get_detected_patterns(input_data) if threat_detected else None
            },
            request_data=input_data
        )

    def log_audit_trail(
            self,
            user_id: str,
            action: str,
            resource: str,
            result: str,
            job_id: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log audit trail events for compliance and monitoring.
        
        Args:
            user_id: User ID performing the action
            action: Action being performed
            resource: Resource being accessed
            result: Result of the action (success/failure)
            job_id: Job ID if applicable
            details: Additional audit details
        """
        self.log_security_event(
            event_type=SecurityEventType.AUDIT_TRAIL,
            severity=SecuritySeverity.LOW,
            user_id=user_id,
            job_id=job_id,
            action=action,
            details={
                "resource": resource,
                "result": result,
                "audit_category": "job_actions",
                **(details or {})
            }
        )

    def _detect_injection_attempts(self, input_data: Dict[str, Any]) -> bool:
        """
        Detect potential injection attempts in input data.
        
        Args:
            input_data: Input data to analyze
            
        Returns:
            bool: True if potential injection attempt detected
        """
        if not input_data:
            return False

        input_str = json.dumps(input_data).lower()

        for pattern_type, patterns in self.suspicious_patterns.items():
            for pattern in patterns:
                if pattern in input_str:
                    return True

        return False

    def _get_detected_patterns(self, input_data: Dict[str, Any]) -> Dict[str, list]:
        """
        Get detected suspicious patterns in input data.
        
        Args:
            input_data: Input data to analyze
            
        Returns:
            Dict mapping pattern types to detected patterns
        """
        detected = {}
        if not input_data:
            return detected

        input_str = json.dumps(input_data).lower()

        for pattern_type, patterns in self.suspicious_patterns.items():
            found_patterns = [pattern for pattern in patterns if pattern in input_str]
            if found_patterns:
                detected[pattern_type] = found_patterns

        return detected

    def _sanitize_request_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize request data for safe logging (remove sensitive information).
        
        Args:
            request_data: Raw request data
            
        Returns:
            Sanitized request data safe for logging
        """
        if not request_data:
            return {}

        # Fields to exclude from logging for security
        sensitive_fields = {'password', 'token', 'secret', 'key', 'auth', 'credential'}

        sanitized = {}
        for key, value in request_data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + "...[TRUNCATED]"
            else:
                sanitized[key] = value

        return sanitized

    def _trigger_security_alert(self, security_event: Dict[str, Any]) -> None:
        """
        Trigger security alerts for critical events.
        
        Args:
            security_event: Security event data
        """
        try:
            # In a real implementation, this would send alerts via email, Slack, etc.
            alert_message = (
                f"CRITICAL SECURITY EVENT: {security_event['event_type']} | "
                f"User: {security_event.get('user_id', 'Unknown')} | "
                f"IP: {security_event.get('ip_address', 'Unknown')} | "
                f"Action: {security_event.get('action', 'Unknown')}"
            )

            self.threat_logger.critical(f"SECURITY ALERT: {alert_message}", extra={"alert": security_event})

            # TODO: Implement actual alerting mechanism (email, Slack, PagerDuty, etc.)

        except Exception as e:
            self.logger.error(f"Failed to trigger security alert: {e}", exc_info=True)


# Global security logger instance
job_actions_security_logger = JobActionsSecurityLogger()
