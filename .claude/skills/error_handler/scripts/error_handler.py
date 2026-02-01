#!/usr/bin/env python3
"""
Error Handler

This module provides centralized error handling, logging, and recovery mechanisms
across all other skills in the Personal AI Employee system. It captures exceptions,
implements retry logic, escalates critical issues, and ensures system resilience
by maintaining operational stability even when individual components fail.

Features:
- Centralized error handling and logging
- Retry mechanisms with exponential backoff
- Circuit breaker pattern implementation
- Error classification and severity assessment
- Notification and escalation systems
- Data sanitization and security protection
"""

import json
import os
import logging
import traceback
import time
import sqlite3
import threading
import hashlib
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class ErrorSeverity(Enum):
    """Enumeration for error severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ErrorCategory(Enum):
    """Enumeration for error categories."""
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """Data class to hold error information."""
    error_type: str
    message: str
    traceback_info: str
    timestamp: str
    skill_name: str
    operation: str
    retry_count: int
    context: Dict[str, Any]
    severity: ErrorSeverity
    category: ErrorCategory
    handled: bool = False
    escalated: bool = False
    recovery_attempts: int = 0


class CircuitBreaker:
    """Implementation of the circuit breaker pattern."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        self.lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs):
        """Call a function with circuit breaker protection."""
        with self.lock:
            if self.state == "open":
                if time.time() - self.last_failure_time >= self.timeout:
                    self.state = "half_open"
                else:
                    raise Exception("Circuit breaker is OPEN - service unavailable")

            try:
                result = func(*args, **kwargs)
                self.on_success()
                return result
            except Exception as e:
                self.on_failure()
                raise e

    def on_success(self):
        """Reset the circuit breaker on success."""
        self.failure_count = 0
        self.state = "closed"

    def on_failure(self):
        """Increment failure count and possibly open the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class ErrorSanitizer:
    """Handles sanitization of error messages to protect sensitive data."""

    def __init__(self):
        self.patterns = [
            # Password patterns
            (re.compile(r'(password|token|key|secret|credential|auth)[=:][^\s&]+', re.IGNORECASE), r'\1=***REDACTED***'),
            # Credit card patterns
            (re.compile(r'\b(\d{4}[ -]?){3}\d{4}\b'), r'****-****-****-****'),
            # Email patterns
            (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), r'***REDACTED***@example.com'),
            # Phone patterns
            (re.compile(r'\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'), r'(***) ***-****'),
        ]
        self.fields_to_redact = [
            'password', 'token', 'secret', 'key', 'credential', 'auth',
            'ssn', 'phone', 'email', 'address', 'credit_card', 'bank_account'
        ]

    def sanitize_error_message(self, message: str) -> str:
        """Sanitize an error message by removing sensitive information."""
        sanitized = message
        for pattern, replacement in self.patterns:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    def sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize context data by removing sensitive fields."""
        sanitized = {}
        for key, value in context.items():
            if key.lower() in self.fields_to_redact:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, str):
                sanitized[key] = self.sanitize_error_message(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_context(value)
            else:
                sanitized[key] = value
        return sanitized


class ErrorStatistics:
    """Manages error statistics and metrics."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables."""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS error_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    error_type TEXT,
                    severity TEXT,
                    skill_name TEXT,
                    operation TEXT,
                    count INTEGER DEFAULT 1
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS error_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_id INTEGER,
                    message TEXT,
                    traceback TEXT,
                    context TEXT,
                    FOREIGN KEY (error_id) REFERENCES error_stats (id)
                )
            ''')

    @contextmanager
    def get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def record_error(self, error_info: ErrorInfo):
        """Record an error in the statistics database."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO error_stats (error_type, severity, skill_name, operation)
                VALUES (?, ?, ?, ?)
            ''', (error_info.error_type, error_info.severity.value, error_info.skill_name, error_info.operation))

            error_id = cursor.lastrowid

            conn.execute('''
                INSERT INTO error_details (error_id, message, traceback, context)
                VALUES (?, ?, ?, ?)
            ''', (error_id, error_info.message, error_info.traceback_info, json.dumps(error_info.context)))

    def get_error_count(self, skill_name: str = None, severity: ErrorSeverity = None) -> int:
        """Get error count with optional filters."""
        with self.get_connection() as conn:
            query = "SELECT COUNT(*) FROM error_stats WHERE 1=1"
            params = []

            if skill_name:
                query += " AND skill_name = ?"
                params.append(skill_name)

            if severity:
                query += " AND severity = ?"
                params.append(severity.value)

            cursor = conn.execute(query, params)
            return cursor.fetchone()[0]


class NotificationManager:
    """Manages error notifications through various channels."""

    def __init__(self):
        self.logger = logging.getLogger('NotificationManager')

    def send_email_notification(self, subject: str, body: str, recipients: List[str]):
        """Send email notification about an error."""
        try:
            smtp_server = os.getenv('ERROR_HANDLER_SMTP_SERVER', 'localhost')
            smtp_port = int(os.getenv('ERROR_HANDLER_SMTP_PORT', '587'))
            sender_email = os.getenv('ERROR_HANDLER_SENDER_EMAIL', 'errors@acme.com')
            sender_password = os.getenv('ERROR_HANDLER_SENDER_PASSWORD', '')

            if not recipients:
                return

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()

            self.logger.info(f"Email notification sent to {recipients}")
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")

    def send_slack_notification(self, message: str, webhook_url: str = None):
        """Send Slack notification about an error."""
        try:
            import requests

            webhook_url = webhook_url or os.getenv('ERROR_HANDLER_SLACK_WEBHOOK_URL')
            if not webhook_url:
                return

            payload = {
                "text": message,
                "username": "Error Handler Bot",
                "icon_emoji": ":warning:"
            }

            response = requests.post(webhook_url, json=payload)
            if response.status_code != 200:
                self.logger.error(f"Failed to send Slack notification: {response.text}")
            else:
                self.logger.info("Slack notification sent")
        except ImportError:
            self.logger.warning("Requests library not available for Slack notifications")
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}")

    def notify_error(self, error_info: ErrorInfo, escalation_recipients: List[str] = None):
        """Send notifications based on error severity."""
        message = f"""
        ERROR ALERT

        Skill: {error_info.skill_name}
        Operation: {error_info.operation}
        Type: {error_info.error_type}
        Severity: {error_info.severity.value}
        Message: {error_info.message}
        Time: {error_info.timestamp}
        Retry Count: {error_info.retry_count}
        """

        if error_info.severity == ErrorSeverity.CRITICAL:
            # Send critical notifications
            if escalation_recipients:
                self.send_email_notification(f"CRITICAL ERROR in {error_info.skill_name}", message, escalation_recipients)

            # Send Slack notification if configured
            self.send_slack_notification(message)


class ErrorHandler:
    """
    Main error handler class that provides centralized error handling,
    logging, and recovery mechanisms.
    """

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.logger = self.setup_logger()
        self.sanitizer = ErrorSanitizer()
        self.stats = ErrorStatistics(os.getenv('ERROR_HANDLER_DATABASE_PATH', ':memory:'))
        self.notifications = NotificationManager()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_classifications = self.load_error_classifications()

        # Load configuration
        self.config = self.load_config()

    def setup_logger(self) -> logging.Logger:
        """Setup logging for the error handler."""
        logger = logging.getLogger('ErrorHandler')
        logger.setLevel(getattr(logging, os.getenv('ERROR_HANDLER_LOG_LEVEL', 'INFO')))

        # Create file handler
        log_file = os.getenv('ERROR_HANDLER_LOG_FILE_PATH', '/tmp/error_handler.log')
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment."""
        config = {
            'retry_config': {
                'default_max_attempts': int(os.getenv('ERROR_HANDLER_MAX_RETRY_ATTEMPTS', '5')),
                'initial_delay_seconds': int(os.getenv('ERROR_HANDLER_INITIAL_DELAY_SECONDS', '1')),
                'backoff_factor': float(os.getenv('ERROR_HANDLER_BACKOFF_FACTOR', '2.0')),
                'max_delay_seconds': int(os.getenv('ERROR_HANDLER_MAX_DELAY_SECONDS', '60')),
                'jitter_enabled': os.getenv('ERROR_HANDLER_JITTER_ENABLED', 'true').lower() == 'true'
            },
            'circuit_breaker': {
                'failure_threshold': int(os.getenv('ERROR_HANDLER_CB_THRESHOLD', '5')),
                'timeout_seconds': int(os.getenv('ERROR_HANDLER_CB_TIMEOUT', '60')),
                'enabled': os.getenv('ERROR_HANDLER_CB_ENABLED', 'true').lower() == 'true'
            }
        }

        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    # Merge file config with defaults
                    for key, value in file_config.items():
                        if isinstance(value, dict) and key in config:
                            config[key].update(value)
                        else:
                            config[key] = value
            except Exception as e:
                self.logger.warning(f"Failed to load config from {self.config_path}: {e}")

        return config

    def load_error_classifications(self) -> Dict[str, List[str]]:
        """Load error type classifications."""
        return {
            'transient': [
                'ConnectionError', 'TimeoutError', 'RateLimitError',
                'ServiceUnavailableError', 'TemporaryFileError', 'DatabaseConnectionError'
            ],
            'permanent': [
                'ValidationError', 'AuthenticationError', 'PermissionDeniedError',
                'NotFoundError', 'ConfigurationError', 'InvalidCredentialsError'
            ],
            'critical': [
                'SecurityBreachError', 'DataCorruptionError', 'SystemCrashError',
                'MemoryExhaustionError', 'DiskFullError', 'IrrecoverableStateError'
            ]
        }

    def classify_error(self, error_type: str) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify an error by category and severity."""
        for category, errors in self.error_classifications.items():
            if error_type in errors:
                if category == 'critical':
                    return ErrorCategory.CRITICAL, ErrorSeverity.CRITICAL
                elif category == 'transient':
                    return ErrorCategory.TRANSIENT, ErrorSeverity.MEDIUM
                else:
                    return ErrorCategory.PERMANENT, ErrorSeverity.HIGH

        # Default classification
        return ErrorCategory.PERMANENT, ErrorSeverity.LOW

    def create_error_info(self, error: Exception, skill_name: str, operation: str,
                         context: Dict[str, Any] = None, retry_count: int = 0) -> ErrorInfo:
        """Create an ErrorInfo object from an exception."""
        error_type = type(error).__name__
        message = str(error)
        traceback_info = traceback.format_exc()
        timestamp = datetime.now().isoformat()

        category, severity = self.classify_error(error_type)

        # Sanitize sensitive information
        sanitized_message = self.sanitizer.sanitize_error_message(message)
        sanitized_context = self.sanitizer.sanitize_context(context or {})

        return ErrorInfo(
            error_type=error_type,
            message=sanitized_message,
            traceback_info=traceback_info,
            timestamp=timestamp,
            skill_name=skill_name,
            operation=operation,
            retry_count=retry_count,
            context=sanitized_context,
            severity=severity,
            category=category
        )

    def log_error(self, error_info: ErrorInfo):
        """Log the error with appropriate level."""
        log_func = getattr(self.logger, error_info.severity.value)
        log_func(f"[{error_info.skill_name}] {error_info.operation} - {error_info.error_type}: {error_info.message}")

        # Record in statistics
        self.stats.record_error(error_info)

    def retry_with_backoff(self, func: Callable, max_attempts: int = None,
                          initial_delay: int = None, backoff_factor: float = None,
                          skill_name: str = "", operation: str = "",
                          context: Dict[str, Any] = None) -> Any:
        """
        Execute a function with retry logic and exponential backoff.
        """
        if max_attempts is None:
            max_attempts = self.config['retry_config']['default_max_attempts']
        if initial_delay is None:
            initial_delay = self.config['retry_config']['initial_delay_seconds']
        if backoff_factor is None:
            backoff_factor = self.config['retry_config']['backoff_factor']

        last_exception = None

        for attempt in range(max_attempts):
            try:
                return func()
            except Exception as e:
                last_exception = e

                # Create error info for logging
                error_info = self.create_error_info(e, skill_name, operation, context, attempt)

                # Log the error
                self.log_error(error_info)

                # If this is the last attempt, break
                if attempt == max_attempts - 1:
                    break

                # Check if error is transient (should retry) or permanent
                category, _ = self.classify_error(type(e).__name__)
                if category == ErrorCategory.PERMANENT:
                    self.logger.info(f"Permanent error encountered, not retrying: {e}")
                    break

                # Calculate delay with exponential backoff and optional jitter
                delay = initial_delay * (backoff_factor ** attempt)
                if self.config['retry_config']['jitter_enabled']:
                    import random
                    delay *= (0.9 + 0.2 * random.random())  # Add ±10% jitter

                self.logger.info(f"Attempt {attempt + 1} failed, retrying in {delay:.2f} seconds...")
                time.sleep(delay)

        # If we exhausted all retries, raise the last exception
        raise last_exception

    def handle_error(self, error: Exception, skill_name: str, operation: str,
                     context: Dict[str, Any] = None, escalate_on_critical: bool = True,
                     escalation_recipients: List[str] = None) -> Dict[str, Any]:
        """
        Handle an error by logging, classifying, and taking appropriate action.

        Returns:
            Dictionary with handling results
        """
        error_info = self.create_error_info(error, skill_name, operation, context)

        # Log the error
        self.log_error(error_info)

        # Mark as handled
        error_info.handled = True

        # Handle critical errors by escalating
        if error_info.severity == ErrorSeverity.CRITICAL and escalate_on_critical:
            error_info.escalated = True
            self.notifications.notify_error(error_info, escalation_recipients)

        # Update statistics
        self.stats.record_error(error_info)

        return {
            'handled': True,
            'escalated': error_info.escalated,
            'severity': error_info.severity.value,
            'category': error_info.category.value,
            'error_id': self.get_error_id(error_info)
        }

    def get_error_id(self, error_info: ErrorInfo) -> str:
        """Generate a unique ID for an error."""
        error_str = f"{error_info.skill_name}:{error_info.operation}:{error_info.timestamp}:{error_info.message}"
        return hashlib.sha256(error_str.encode()).hexdigest()[:16]

    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a service."""
        if service_name not in self.circuit_breakers:
            cb_config = self.config['circuit_breaker']
            self.circuit_breakers[service_name] = CircuitBreaker(
                failure_threshold=cb_config['failure_threshold'],
                timeout=cb_config['timeout_seconds']
            )
        return self.circuit_breakers[service_name]

    def get_error_statistics(self, skill_name: str = None, severity: ErrorSeverity = None) -> int:
        """Get error statistics."""
        return self.stats.get_error_count(skill_name, severity)

    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of error statistics."""
        total_errors = self.get_error_statistics()
        critical_errors = self.get_error_statistics(severity=ErrorSeverity.CRITICAL)
        high_errors = self.get_error_statistics(severity=ErrorSeverity.HIGH)

        return {
            'total_errors': total_errors,
            'critical_errors': critical_errors,
            'high_errors': high_errors,
            'circuit_breaker_states': {name: cb.state for name, cb in self.circuit_breakers.items()}
        }


def main():
    """Main function for testing the Error Handler."""
    print("Error Handler Skill")
    print("===================")

    # Initialize the error handler
    config_path = os.getenv('ERROR_HANDLER_CONFIG_PATH', './error_config.json')
    handler = ErrorHandler(config_path)

    print(f"Error Handler initialized with config: {config_path}")

    # Test error handling
    def test_function_that_fails():
        raise ConnectionError("Network connection failed")

    print("\nTesting error handling with retry...")
    try:
        # This will fail and trigger error handling
        result = handler.retry_with_backoff(
            test_function_that_fails,
            max_attempts=3,
            skill_name="TestSkill",
            operation="TestOperation",
            context={"param1": "value1", "sensitive_data": "secret_key_123"}
        )
    except Exception as e:
        print(f"Function ultimately failed after retries: {e}")

    # Test direct error handling
    print("\nTesting direct error handling...")
    try:
        raise ValueError("Invalid input provided")
    except Exception as e:
        result = handler.handle_error(
            e,
            skill_name="TestSkill",
            operation="DirectTest",
            context={"input": "invalid", "user_id": "12345"}
        )
        print(f"Error handled: {result}")

    # Show error summary
    summary = handler.get_error_summary()
    print(f"\nError Summary: {summary}")

    print("\nError Handler is ready to manage errors across all skills!")


if __name__ == "__main__":
    main()