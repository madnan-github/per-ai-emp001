# Error Handler Configuration Guide

## Overview
This guide provides comprehensive configuration instructions for the Error Handler skill, which provides centralized error handling, logging, and recovery mechanisms across all other skills in the Personal AI Employee system.

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Required Python packages:
  - logging (built-in)
  - traceback (built-in)
  - json (built-in)
  - requests (for notifications)
  - sqlite3 (for error statistics)
  - redis (optional, for distributed error tracking)

### Environment Variables
Set these environment variables for secure configuration:

```
ERROR_HANDLER_LOG_LEVEL=INFO
ERROR_HANDLER_MAX_RETRY_ATTEMPTS=5
ERROR_HANDLER_INITIAL_DELAY_SECONDS=1
ERROR_HANDLER_BACKOFF_FACTOR=2.0
ERROR_HANDLER_MAX_DELAY_SECONDS=60
ERROR_HANDLER_ERROR_DATABASE_PATH=/data/error_statistics.db
ERROR_HANDLER_LOG_FILE_PATH=/logs/error_log.log
ERROR_HANDLER_CRITICAL_ERROR_EMAIL=admin@example.com
ERROR_HANDLER_NOTIFICATION_CHANNEL=slack
```

## Error Classification Configuration

### Error Type Definitions
```json
{
  "error_types": {
    "transient": [
      "ConnectionError",
      "TimeoutError",
      "RateLimitError",
      "ServiceUnavailableError",
      "TemporaryFileError",
      "DatabaseConnectionError"
    ],
    "permanent": [
      "ValidationError",
      "AuthenticationError",
      "PermissionDeniedError",
      "NotFoundError",
      "ConfigurationError",
      "InvalidCredentialsError"
    ],
    "critical": [
      "SecurityBreachError",
      "DataCorruptionError",
      "SystemCrashError",
      "MemoryExhaustionError",
      "DiskFullError",
      "IrrecoverableStateError"
    ]
  }
}
```

### Severity Level Configuration
```json
{
  "severity_levels": {
    "critical": {
      "escalation_threshold": 0,
      "notification_channels": ["email", "sms", "dashboard"],
      "escalation_recipients": ["admin@example.com"],
      "retry_enabled": false
    },
    "high": {
      "escalation_threshold": 1,
      "notification_channels": ["email", "dashboard"],
      "escalation_recipients": ["ops@example.com"],
      "retry_enabled": true
    },
    "medium": {
      "escalation_threshold": 3,
      "notification_channels": ["dashboard"],
      "escalation_recipients": [],
      "retry_enabled": true
    },
    "low": {
      "escalation_threshold": 5,
      "notification_channels": [],
      "escalation_recipients": [],
      "retry_enabled": true
    }
  }
}
```

## Retry Configuration

### Retry Settings
```json
{
  "retry_config": {
    "default_max_attempts": 5,
    "initial_delay_seconds": 1,
    "backoff_factor": 2.0,
    "max_delay_seconds": 60,
    "jitter_enabled": true,
    "retry_on_transient_errors": true,
    "retry_on_timeout_errors": true,
    "retry_on_connection_errors": true
  }
}
```

### Circuit Breaker Configuration
```json
{
  "circuit_breaker": {
    "failure_threshold": 5,
    "timeout_seconds": 60,
    "half_open_request_count": 1,
    "enabled": true
  }
}
```

## Logging Configuration

### Log Format Settings
```json
{
  "logging": {
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "file_rotation": {
      "max_size_mb": 100,
      "backup_count": 5
    },
    "sanitize_patterns": [
      "password",
      "token",
      "key",
      "secret",
      "credential",
      "auth"
    ]
  }
}
```

### Log Level Configuration
```json
{
  "log_levels": {
    "debug": {
      "enabled": false,
      "include_tracebacks": true,
      "log_performance": true
    },
    "info": {
      "enabled": true,
      "include_basic_context": true,
      "log_operations": true
    },
    "warning": {
      "enabled": true,
      "include_context": true,
      "log_potential_issues": true
    },
    "error": {
      "enabled": true,
      "include_full_context": true,
      "log_errors": true
    },
    "critical": {
      "enabled": true,
      "include_full_context": true,
      "log_critical": true
    }
  }
}
```

## Notification Configuration

### Notification Channels
```json
{
  "notification_channels": {
    "email": {
      "enabled": true,
      "smtp_server": "smtp.example.com",
      "smtp_port": 587,
      "username_env_var": "SMTP_USERNAME",
      "password_env_var": "SMTP_PASSWORD",
      "sender_email": "errors@acme.com"
    },
    "slack": {
      "enabled": true,
      "webhook_url_env_var": "SLACK_WEBHOOK_URL",
      "channel": "#errors",
      "bot_name": "Error Handler Bot"
    },
    "sms": {
      "enabled": false,
      "provider": "twilio",
      "account_sid_env_var": "TWILIO_ACCOUNT_SID",
      "auth_token_env_var": "TWILIO_AUTH_TOKEN",
      "from_number": "+1234567890"
    },
    "dashboard": {
      "enabled": true,
      "update_interval_seconds": 30
    }
  }
}
```

### Alert Thresholds
```json
{
  "alert_thresholds": {
    "error_rate": {
      "warning_threshold": 0.05,
      "critical_threshold": 0.10,
      "time_window_minutes": 5
    },
    "response_time": {
      "warning_threshold": 5.0,
      "critical_threshold": 10.0,
      "time_window_minutes": 10
    },
    "resource_usage": {
      "cpu_warning": 80,
      "cpu_critical": 95,
      "memory_warning": 80,
      "memory_critical": 95
    }
  }
}
```

## Data Protection Configuration

### Sanitization Rules
```json
{
  "sanitization": {
    "patterns": [
      {
        "regex": "(password|token|key|secret|credential|auth)[=:][^\\s&]+",
        "replacement": "$1=***REDACTED***"
      },
      {
        "regex": "\\b(\\d{4}[ -]?){3}\\d{4}\\b",
        "replacement": "****-****-****-****"
      },
      {
        "regex": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b",
        "replacement": "***REDACTED***@example.com"
      }
    ],
    "fields_to_redact": [
      "password",
      "token",
      "secret",
      "key",
      "credential",
      "auth",
      "ssn",
      "phone",
      "email"
    ]
  }
}
```

### Encryption Settings
```json
{
  "encryption": {
    "enabled": true,
    "algorithm": "AES-256-GCM",
    "key_source": "environment_variable",
    "key_env_var": "ERROR_ENCRYPTION_KEY"
  }
}
```

## Performance Tuning

### Resource Management
```json
{
  "performance": {
    "max_log_queue_size": 1000,
    "async_logging": true,
    "batch_log_processing": true,
    "batch_size": 100,
    "flush_interval_seconds": 5,
    "memory_limit_mb": 100
  }
}
```

### Error Statistics Configuration
```json
{
  "statistics": {
    "enabled": true,
    "collection_interval_seconds": 60,
    "retention_days": 30,
    "aggregation_levels": ["hourly", "daily", "weekly"],
    "metrics": [
      "error_count",
      "error_rate",
      "retry_count",
      "escalation_count",
      "recovery_time"
    ]
  }
}
```

## Integration Configuration

### Database Configuration
```json
{
  "database": {
    "type": "sqlite",
    "path": "/data/error_statistics.db",
    "connection_pool_size": 5,
    "timeout_seconds": 30,
    "enable_wal_mode": true
  }
}
```

### External System Integration
```json
{
  "integrations": {
    "monitoring": {
      "prometheus": {
        "enabled": true,
        "port": 9090
      },
      "datadog": {
        "enabled": false,
        "api_key_env_var": "DATADOG_API_KEY"
      }
    },
    "log_aggregation": {
      "elasticsearch": {
        "enabled": false,
        "url": "http://elasticsearch:9200",
        "index_pattern": "error-logs-%Y.%m.%d"
      }
    }
  }
}
```

## Security Configuration

### Access Control
```json
{
  "security": {
    "api_authentication": {
      "require_api_keys": true,
      "api_key_storage_location": "environment_variable",
      "api_key_rotation_days": 90
    },
    "file_permissions": {
      "log_files": "640",
      "config_files": "600",
      "database_files": "600"
    }
  }
}
```

### Compliance Settings
```json
{
  "compliance": {
    "gdpr": {
      "right_to_access": true,
      "right_to_erasure": true,
      "data_portability": true
    },
    "data_retention": {
      "error_logs": "90_days",
      "statistics": "1_year",
      "escalation_records": "7_years"
    }
  }
}
```

## Monitoring and Alerting

### Health Checks
```json
{
  "monitoring": {
    "health_checks": {
      "logging_functionality": true,
      "notification_channels": true,
      "database_connectivity": true,
      "external_api_health": true
    },
    "metrics_collection": {
      "enabled": true,
      "collection_interval_minutes": 5,
      "metrics": [
        "error_rate",
        "retry_success_rate",
        "escalation_count",
        "recovery_time_avg",
        "log_processing_time"
      ]
    },
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/error_handler.log",
      "rotation": {
        "size_mb": 100,
        "backup_count": 10
      },
      "sensitive_data_masking": true
    }
  }
}
```

### System Alert Configuration
```json
{
  "system_alerts": {
    "alert_triggers": [
      {
        "name": "high_error_rate",
        "condition": "error_rate > 0.10",
        "severity": "critical",
        "recipients": ["admin@example.com"],
        "notification_method": "email"
      },
      {
        "name": "failed_escallations",
        "condition": "escalation_failures > 5",
        "severity": "high",
        "recipients": ["admin@example.com", "ops@example.com"],
        "notification_method": ["email", "slack"]
      },
      {
        "name": "database_failure",
        "condition": "db_errors > 0",
        "severity": "critical",
        "recipients": ["admin@example.com", "dba@example.com"],
        "notification_method": ["email", "sms"]
      }
    ]
  }
}
```

## Sample Configuration File

Create an `error_config.json` file with your configuration:

```json
{
  "metadata": {
    "version": "1.0",
    "last_updated": "2026-02-01T10:00:00Z",
    "organization": "Acme Corporation"
  },
  "global_settings": {
    "company_name": "Acme Corporation",
    "default_timezone": "America/New_York",
    "default_language": "en_US",
    "confidentiality_level": "internal"
  },
  "error_types": {
    "transient": [
      "ConnectionError",
      "TimeoutError",
      "RateLimitError",
      "ServiceUnavailableError"
    ],
    "permanent": [
      "ValidationError",
      "AuthenticationError",
      "PermissionDeniedError"
    ],
    "critical": [
      "SecurityBreachError",
      "DataCorruptionError",
      "SystemCrashError"
    ]
  },
  "retry_config": {
    "default_max_attempts": 5,
    "initial_delay_seconds": 1,
    "backoff_factor": 2.0,
    "max_delay_seconds": 60
  },
  "circuit_breaker": {
    "failure_threshold": 5,
    "timeout_seconds": 60,
    "enabled": true
  },
  "notification_channels": {
    "email": {
      "enabled": true,
      "smtp_server": "smtp.example.com",
      "sender_email": "errors@acme.com"
    },
    "slack": {
      "enabled": true,
      "channel": "#errors"
    }
  },
  "alert_thresholds": {
    "error_rate": {
      "critical_threshold": 0.10,
      "time_window_minutes": 5
    }
  }
}
```