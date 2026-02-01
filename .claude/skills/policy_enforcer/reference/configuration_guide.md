# Policy Enforcer Configuration Guide

## Overview
This guide provides comprehensive configuration instructions for the Policy Enforcer skill, which ensures all actions taken by the Personal AI Employee comply with predefined organizational policies, governance requirements, and compliance standards.

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- SQLite 3.25 or higher (for policy store)
- Required Python packages:
  - sqlite3 (usually comes with Python)
  - json (usually comes with Python)
  - datetime (usually comes with Python)
  - logging (usually comes with Python)
  - re (for pattern matching)

### Environment Variables
Set these environment variables for secure configuration:

```
POLICY_ENFORCER_DB_PATH=/path/to/policy_store.db
POLICY_ENFORCER_LOG_LEVEL=INFO
POLICY_ENFORCER_CONFIG_PATH=/path/to/policies.json
POLICY_ENFORCER_AUDIT_LOG_PATH=/path/to/policy_audit.log
```

## Policy Configuration Structure

### Policy Definition Format
Each policy is defined with the following structure:

```json
{
  "id": "policy_unique_identifier",
  "name": "Descriptive Policy Name",
  "category": "governance|financial|security|compliance",
  "priority": "critical|high|medium|low|informational",
  "description": "Detailed description of what the policy governs",
  "conditions": [
    {
      "attribute": "action.type",
      "operator": "equals|contains|greater_than|less_than|matches_regex",
      "value": "specific_value_or_pattern"
    }
  ],
  "actions": [
    {
      "type": "allow|block|review|alert|conditional",
      "parameters": {}
    }
  ],
  "exceptions": [
    {
      "role": "role_name",
      "scope": "global|department|project",
      "duration": "time_period"
    }
  ],
  "enabled": true,
  "created_date": "YYYY-MM-DD",
  "last_updated": "YYYY-MM-DD",
  "version": "1.0"
}
```

### Policy Categories Configuration

#### Governance Policies
```json
{
  "governance_policies": {
    "authorization": {
      "enforce_authorization_matrix": true,
      "require_role_verification": true,
      "enable_delegation": true,
      "delegation_max_duration_hours": 24
    },
    "approval": {
      "enforce_approval_levels": true,
      "require_multi_level_approvals": true,
      "auto_approve_threshold_amount": 100,
      "approval_timeout_hours": 24
    },
    "segregation_of_duties": {
      "enforce_segregation": true,
      "prohibited_combinations": [
        {
          "first_task": "initiate_payment",
          "second_task": "approve_payment"
        }
      ]
    },
    "access_control": {
      "enforce_permissions": true,
      "require_mfa_for_sensitive_actions": true,
      "session_timeout_minutes": 30
    }
  }
}
```

#### Financial Policies
```json
{
  "financial_policies": {
    "spending_limits": {
      "daily_individual_limit": 500,
      "weekly_team_limit": 2000,
      "monthly_department_limit": 10000,
      "require_approval_above_threshold": 1000
    },
    "payment_authorization": {
      "require_two_person_approval": true,
      "vendor_verification_required": true,
      "payment_method_restrictions": ["ACH", "wire_transfer"],
      "maximum_single_payment_amount": 5000
    },
    "expense_classification": {
      "mandatory_categories": ["travel", "supplies", "services", "software"],
      "require_receipts_above_amount": 25,
      "require_business_justification_above_amount": 100
    },
    "budget_adherence": {
      "budget_check_required": true,
      "alert_threshold_percentage": 80,
      "block_exceeding_budget": true
    }
  }
}
```

#### Security Policies
```json
{
  "security_policies": {
    "data_protection": {
      "classify_sensitive_data": true,
      "encrypt_transmission_required": true,
      "restrict_external_sharing": true,
      "require_dlp_scan": true
    },
    "authentication": {
      "require_mfa_for_all_users": true,
      "password_complexity_rules": {
        "minimum_length": 12,
        "require_uppercase": true,
        "require_lowercase": true,
        "require_numbers": true,
        "require_special_chars": true
      },
      "password_expiry_days": 90
    },
    "system_access": {
      "principle_least_privilege": true,
      "regular_access_reviews": true,
      "automated_deprovisioning": true,
      "access_request_workflow": true
    },
    "incident_response": {
      "automatic_incident_detection": true,
      "escalation_timeframes": {
        "critical": 15,
        "high": 60,
        "medium": 240,
        "low": 1440
      }
    }
  }
}
```

#### Compliance Policies
```json
{
  "compliance_policies": {
    "regulatory_compliance": {
      "gdpr_requirements": true,
      "sox_compliance": true,
      "industry_specific_regulations": [],
      "compliance_reporting_frequency": "monthly"
    },
    "audit_requirements": {
      "detailed_audit_trails": true,
      "retention_period_years": 7,
      "regular_audit_reviews": true,
      "independent_validation": true
    },
    "privacy_regulations": {
      "data_minimization_principle": true,
      "consent_management": true,
      "right_to_be_forgotten": true,
      "data_breach_notification_timeline": 72
    }
  }
}
```

## Policy Enforcement Settings

### Pre-Action Validation
```json
{
  "pre_action_validation": {
    "policy_lookup_timeout_seconds": 30,
    "fail_open_behavior": false,
    "cache_policy_results": true,
    "cache_duration_minutes": 5,
    "parallel_validation_enabled": true
  }
}
```

### Real-Time Monitoring
```json
{
  "real_time_monitoring": {
    "monitoring_interval_seconds": 10,
    "violation_alert_recipients": ["admin@example.com", "compliance@example.com"],
    "violation_severity_thresholds": {
      "critical": ["block_immediately"],
      "high": ["alert_immediately", "review_within_1_hour"],
      "medium": ["log_violation", "review_daily"],
      "low": ["log_violation", "review_weekly"]
    }
  }
}
```

### Post-Action Verification
```json
{
  "post_action_verification": {
    "verification_delay_minutes": 5,
    "verification_retries": 3,
    "non_compliance_notification_recipients": ["admin@example.com"],
    "automatic_correction_enabled": false
  }
}
```

## Exception Handling Configuration

### Override Mechanism
```json
{
  "exception_handling": {
    "override_authorization": {
      "allow_manual_overrides": true,
      "override_approval_required": true,
      "override_reason_required": true,
      "override_maximum_duration_hours": 24
    },
    "emergency_procedures": {
      "emergency_override_enabled": true,
      "emergency_contact_required": true,
      "emergency_reason_minimum_length": 20,
      "emergency_approval_chain": ["manager", "director", "vp"]
    },
    "temporary_waivers": {
      "waiver_request_process": true,
      "waiver_approval_workflow": true,
      "waiver_maximum_duration_days": 30,
      "waiver_review_frequency": "daily"
    }
  }
}
```

## Integration Configuration

### External System Connections
```json
{
  "integration_settings": {
    "erp_integration": {
      "enabled": true,
      "api_endpoint": "https://erp.example.com/api",
      "api_key_env_var": "ERP_API_KEY",
      "sync_frequency_minutes": 60
    },
    "hris_integration": {
      "enabled": true,
      "api_endpoint": "https://hris.example.com/api",
      "api_key_env_var": "HRIS_API_KEY",
      "sync_frequency_minutes": 120
    },
    "document_management": {
      "enabled": true,
      "repository_url": "https://docs.example.com",
      "username_env_var": "DOC_REPO_USERNAME",
      "password_env_var": "DOC_REPO_PASSWORD"
    }
  }
}
```

### Audit and Logging Configuration
```json
{
  "audit_logging": {
    "log_level": "INFO",
    "log_file_path": "/var/log/policy_enforcer.log",
    "log_rotation": {
      "size_mb": 100,
      "backup_count": 5
    },
    "sensitive_data_masking": true,
    "external_log_forwarding": {
      "enabled": false,
      "syslog_server": "",
      "format": "rfc5424"
    }
  }
}
```

## Performance Tuning

### Caching Configuration
```json
{
  "performance_tuning": {
    "caching": {
      "policy_cache_enabled": true,
      "policy_cache_size": 1000,
      "policy_cache_ttl_minutes": 15,
      "result_cache_enabled": true,
      "result_cache_size": 5000,
      "result_cache_ttl_minutes": 5
    },
    "database_optimization": {
      "connection_pool_size": 10,
      "query_timeout_seconds": 30,
      "index_optimization": true
    }
  }
}
```

### Resource Limits
```json
{
  "resource_limits": {
    "max_concurrent_validations": 100,
    "validation_timeout_seconds": 60,
    "memory_limit_mb": 512,
    "cpu_quota_percentage": 50
  }
}
```

## Security Configuration

### Authentication and Authorization
```json
{
  "security_config": {
    "api_authentication": {
      "require_api_keys": true,
      "api_key_storage_location": "environment_variable",
      "api_key_rotation_days": 90
    },
    "encryption_settings": {
      "data_at_rest_encryption": true,
      "data_in_transit_encryption": true,
      "encryption_algorithm": "AES-256-GCM",
      "key_management_system": "os_environment"
    }
  }
}
```

### Network Security
```json
{
  "network_security": {
    "allowed_ip_ranges": ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],
    "rate_limiting": {
      "requests_per_minute": 100,
      "burst_capacity": 200
    },
    "ssl_configuration": {
      "require_ssl": true,
      "minimum_tls_version": "TLSv1.2",
      "cipher_suites": ["ECDHE-RSA-AES256-GCM-SHA384", "ECDHE-RSA-AES128-GCM-SHA256"]
    }
  }
}
```

## Monitoring and Alerting

### Health Checks
```json
{
  "monitoring": {
    "health_check_endpoint": "/health",
    "metrics_endpoint": "/metrics",
    "health_check_interval_seconds": 30,
    "metrics_collection_enabled": true,
    "metrics_format": "prometheus"
  }
}
```

### Alert Configuration
```json
{
  "alerts": {
    "policy_violation_alerts": {
      "critical_violations": ["email", "slack"],
      "high_violations": ["email"],
      "medium_violations": ["dashboard"],
      "low_violations": ["log_only"]
    },
    "system_health_alerts": {
      "service_down": ["email", "sms"],
      "high_error_rate": ["email"],
      "slow_performance": ["email"]
    },
    "notification_channels": {
      "email": {
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "sender_email": "alerts@example.com",
        "recipients": ["admin@example.com"]
      },
      "slack": {
        "webhook_url_env_var": "SLACK_WEBHOOK_URL",
        "channel": "#policy-violations"
      }
    }
  }
}
```

## Sample Configuration File

Create a `policies.json` file with your policy definitions:

```json
{
  "metadata": {
    "version": "1.0",
    "last_updated": "2026-02-01T10:00:00Z",
    "organization": "Acme Corporation"
  },
  "global_settings": {
    "default_priority": "medium",
    "fail_open_behavior": false,
    "logging_level": "INFO"
  },
  "policies": [
    {
      "id": "spending-limit-001",
      "name": "Individual Daily Spending Limit",
      "category": "financial",
      "priority": "high",
      "description": "Limits individual daily spending to $500",
      "conditions": [
        {
          "attribute": "action.type",
          "operator": "equals",
          "value": "expense_submission"
        },
        {
          "attribute": "action.amount",
          "operator": "greater_than",
          "value": 500
        }
      ],
      "actions": [
        {
          "type": "block",
          "parameters": {
            "reason": "Exceeds daily spending limit of $500"
          }
        }
      ],
      "exceptions": [],
      "enabled": true,
      "created_date": "2026-01-15",
      "last_updated": "2026-01-15",
      "version": "1.0"
    },
    {
      "id": "data-protection-001",
      "name": "Sensitive Data Sharing Policy",
      "category": "security",
      "priority": "critical",
      "description": "Blocks sharing of sensitive data externally",
      "conditions": [
        {
          "attribute": "action.type",
          "operator": "equals",
          "value": "file_share"
        },
        {
          "attribute": "action.destination",
          "operator": "equals",
          "value": "external"
        },
        {
          "attribute": "action.file.contains_sensitive_data",
          "operator": "equals",
          "value": true
        }
      ],
      "actions": [
        {
          "type": "block",
          "parameters": {
            "reason": "Contains sensitive data and destination is external"
          }
        }
      ],
      "exceptions": [
        {
          "role": "data_officer",
          "scope": "global",
          "duration": "24_hours"
        }
      ],
      "enabled": true,
      "created_date": "2026-01-15",
      "last_updated": "2026-01-15",
      "version": "1.0"
    }
  ]
}
```