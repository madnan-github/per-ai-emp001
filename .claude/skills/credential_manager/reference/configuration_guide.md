# Credential Manager Configuration Guide

## Overview
This guide provides comprehensive configuration instructions for the Credential Manager skill, which provides secure credential storage, retrieval, and management for the Personal AI Employee system.

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Required Python packages:
  - cryptography (for encryption)
  - sqlite3 (for credential registry)
  - secrets (for secure random generation)
  - os (for environment access)
  - json (for configuration parsing)
  - hashlib (for credential hashing)

### Environment Variables
Set these environment variables for secure configuration:

```
CREDENTIAL_MANAGER_VAULT_PATH=/secure/credentials/
CREDENTIAL_MANAGER_MASTER_KEY_PATH=/secure/master.key
CREDENTIAL_MANAGER_LOG_LEVEL=INFO
CREDENTIAL_MANAGER_DATABASE_PATH=/data/credential_registry.db
CREDENTIAL_MANAGER_ENCRYPTION_ALGORITHM=AES-256-GCM
CREDENTIAL_MANAGER_ROTATION_INTERVAL_DAYS=30
CREDENTIAL_MANAGER_AUDIT_LOG_PATH=/logs/credential_audit.log
```

## Credential Storage Configuration

### Storage Backend Options
```json
{
  "storage": {
    "type": "encrypted_file",  // encrypted_file, database, or external_vault
    "encrypted_file": {
      "path": "/secure/credentials/",
      "file_permissions": "600",
      "encryption": {
        "algorithm": "AES-256-GCM",
        "key_derivation": "PBKDF2",
        "iterations": 100000
      }
    },
    "database": {
      "type": "sqlite",
      "path": "/data/credential_registry.db",
      "connection_pool_size": 5,
      "timeout_seconds": 30
    },
    "external_vault": {
      "type": "hashicorp_vault",  // hashicorp_vault, aws_secrets_manager, azure_key_vault
      "address": "https://vault.example.com",
      "token_env_var": "VAULT_TOKEN"
    }
  }
}
```

### Master Key Configuration
```json
{
  "master_key": {
    "source": "file",  // file, environment, or hsm
    "file_path": "/secure/master.key",
    "environment_variable": "MASTER_CREDENTIAL_KEY",
    "key_size": 256,
    "rotation_interval_days": 90
  }
}
```

## Authentication Configuration

### Authentication Methods
```json
{
  "authentication": {
    "methods": [
      {
        "type": "api_key",
        "enabled": true,
        "required_for_access": true
      },
      {
        "type": "oauth",
        "enabled": false,
        "provider": "google",
        "client_id_env_var": "OAUTH_CLIENT_ID",
        "client_secret_env_var": "OAUTH_CLIENT_SECRET"
      },
      {
        "type": "certificate",
        "enabled": true,
        "certificate_path": "/secure/client_cert.pem",
        "private_key_path": "/secure/client_key.pem"
      }
    ]
  }
}
```

### Access Control Configuration
```json
{
  "access_control": {
    "rbac_enabled": true,
    "roles": [
      {
        "name": "admin",
        "permissions": [
          "create_credential",
          "read_credential",
          "update_credential",
          "delete_credential",
          "rotate_credential",
          "manage_access"
        ]
      },
      {
        "name": "service",
        "permissions": [
          "read_credential",
          "rotate_own_credential"
        ]
      },
      {
        "name": "auditor",
        "permissions": [
          "read_audit_logs",
          "generate_reports"
        ]
      }
    ],
    "attribute_based": {
      "enabled": false,
      "attributes": [
        "service_name",
        "environment",
        "user_department",
        "security_clearance"
      ]
    }
  }
}
```

## Encryption Configuration

### Encryption Settings
```json
{
  "encryption": {
    "algorithm": "AES-256-GCM",
    "key_size": 256,
    "key_derivation": {
      "algorithm": "PBKDF2",
      "iterations": 100000,
      "salt_size": 128
    },
    "key_wrapping": {
      "enabled": true,
      "algorithm": "RSA-OAEP",
      "key_size": 2048
    },
    "file_encryption": {
      "enabled": true,
      "chunk_size": 8192
    }
  }
}
```

### Key Management
```json
{
  "key_management": {
    "rotation": {
      "enabled": true,
      "interval_days": 90,
      "overlap_days": 7,
      "notification_recipients": ["security@example.com"]
    },
    "backup": {
      "enabled": true,
      "destination": "secure_backup_location",
      "encryption": true,
      "schedule": "daily"
    },
    "hsm_integration": {
      "enabled": false,
      "provider": "aws_cloudhsm",
      "cluster_id": "cluster-12345"
    }
  }
}
```

## Credential Lifecycle Configuration

### Rotation Policies
```json
{
  "rotation_policies": {
    "default": {
      "interval_days": 90,
      "notification_days_before": 7,
      "grace_period_days": 14
    },
    "api_keys": {
      "interval_days": 30,
      "notification_days_before": 3,
      "grace_period_days": 7
    },
    "database_passwords": {
      "interval_days": 60,
      "notification_days_before": 5,
      "grace_period_days": 10
    },
    "oauth_tokens": {
      "interval_days": 7,
      "notification_days_before": 1,
      "grace_period_days": 2
    }
  }
}
```

### Expiration Settings
```json
{
  "expiration": {
    "check_interval_minutes": 15,
    "auto_revoke_expired": true,
    "notification_enabled": true,
    "notification_days_before": 7,
    "renewal_grace_period_days": 30
  }
}
```

## Audit and Compliance Configuration

### Audit Settings
```json
{
  "audit": {
    "enabled": true,
    "log_level": "INFO",
    "file_path": "/logs/credential_audit.log",
    "rotation": {
      "max_size_mb": 100,
      "backup_count": 10
    },
    "events_to_log": [
      "credential_access",
      "credential_creation",
      "credential_modification",
      "credential_deletion",
      "failed_authentication",
      "permission_changes",
      "rotation_events"
    ],
    "pii_masking": {
      "enabled": true,
      "patterns": [
        "password",
        "token",
        "key",
        "secret",
        "credential"
      ]
    }
  }
}
```

### Compliance Settings
```json
{
  "compliance": {
    "standards": {
      "soc2": {
        "enabled": true,
        "requirements": [
          "access_monitoring",
          "audit_logging",
          "key_management"
        ]
      },
      "gdpr": {
        "enabled": true,
        "requirements": [
          "data_minimization",
          "right_to_erasure",
          "data_portability"
        ]
      },
      "hipaa": {
        "enabled": true,
        "requirements": [
          "access_controls",
          "audit_logging",
          "encryption"
        ]
      }
    },
    "retention_policies": {
      "audit_logs": "7_years",
      "credential_metadata": "5_years",
      "access_records": "3_years"
    }
  }
}
```

## Notification Configuration

### Notification Channels
```json
{
  "notifications": {
    "channels": {
      "email": {
        "enabled": true,
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "username_env_var": "SMTP_USERNAME",
        "password_env_var": "SMTP_PASSWORD",
        "sender_email": "credentials@acme.com"
      },
      "slack": {
        "enabled": true,
        "webhook_url_env_var": "SLACK_WEBHOOK_URL",
        "channel": "#security-alerts"
      },
      "dashboard": {
        "enabled": true,
        "url": "https://dashboard.acme.com/credentials"
      }
    },
    "event_triggers": [
      {
        "name": "credential_expiring",
        "condition": "days_until_expiration <= 7",
        "recipients": ["security@example.com", "admin@example.com"],
        "channels": ["email", "slack"]
      },
      {
        "name": "failed_access_attempt",
        "condition": "failed_attempts > 5",
        "recipients": ["security@example.com"],
        "channels": ["email", "dashboard"]
      },
      {
        "name": "credential_rotated",
        "condition": "rotation_completed",
        "recipients": ["owner@example.com"],
        "channels": ["email"]
      }
    ]
  }
}
```

## Performance Tuning

### Caching Configuration
```json
{
  "caching": {
    "enabled": true,
    "backend": "in_memory",  // in_memory or redis
    "ttl_seconds": 300,
    "max_entries": 1000,
    "eviction_policy": "lru",
    "redis_config": {
      "url": "redis://localhost:6379/0",
      "password_env_var": "REDIS_PASSWORD"
    }
  }
}
```

### Resource Management
```json
{
  "performance": {
    "connection_pool": {
      "size": 10,
      "timeout_seconds": 30,
      "max_idle_time_minutes": 10
    },
    "threading": {
      "max_workers": 20,
      "queue_size": 100
    },
    "memory": {
      "max_heap_size_mb": 512,
      "gc_threshold": 1000
    }
  }
}
```

## Integration Configuration

### External System Integration
```json
{
  "integrations": {
    "identity_providers": [
      {
        "name": "google_workspace",
        "enabled": true,
        "client_id_env_var": "GOOGLE_CLIENT_ID",
        "client_secret_env_var": "GOOGLE_CLIENT_SECRET",
        "domain": "acme.com"
      },
      {
        "name": "azure_ad",
        "enabled": false,
        "tenant_id_env_var": "AZURE_TENANT_ID",
        "client_id_env_var": "AZURE_CLIENT_ID",
        "client_secret_env_var": "AZURE_CLIENT_SECRET"
      }
    ],
    "cloud_vaults": [
      {
        "name": "aws_secrets_manager",
        "enabled": false,
        "region": "us-east-1",
        "access_key_env_var": "AWS_ACCESS_KEY_ID",
        "secret_key_env_var": "AWS_SECRET_ACCESS_KEY"
      },
      {
        "name": "hashicorp_vault",
        "enabled": false,
        "address": "https://vault.example.com",
        "token_env_var": "VAULT_TOKEN"
      }
    ]
  }
}
```

### API Configuration
```json
{
  "api": {
    "host": "0.0.0.0",
    "port": 8080,
    "ssl": {
      "enabled": true,
      "cert_path": "/secure/server.crt",
      "key_path": "/secure/server.key"
    },
    "rate_limiting": {
      "enabled": true,
      "requests_per_minute": 100,
      "burst_capacity": 200
    },
    "cors": {
      "enabled": false,
      "allowed_origins": ["https://dashboard.acme.com"]
    }
  }
}
```

## Security Configuration

### Network Security
```json
{
  "network_security": {
    "firewall": {
      "enabled": true,
      "allowed_ips": ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
    },
    "tls": {
      "enabled": true,
      "min_version": "TLSv1.2",
      "cipher_suites": [
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES128-GCM-SHA256"
      ]
    },
    "authentication": {
      "require_client_cert": true,
      "require_api_key": true,
      "require_oauth": false
    }
  }
}
```

### File System Security
```json
{
  "file_security": {
    "credential_directory": {
      "path": "/secure/credentials/",
      "owner": "credential_service",
      "group": "credential_group",
      "permissions": "700"
    },
    "log_directory": {
      "path": "/logs/",
      "owner": "credential_service",
      "group": "credential_group",
      "permissions": "750"
    },
    "config_directory": {
      "path": "/etc/credentials/",
      "owner": "root",
      "group": "credential_group",
      "permissions": "640"
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
      "storage_connectivity": true,
      "encryption_functionality": true,
      "authentication_service": true,
      "external_vault_connectivity": true
    },
    "metrics_collection": {
      "enabled": true,
      "collection_interval_minutes": 5,
      "metrics": [
        "credential_access_rate",
        "encryption_performance",
        "authentication_success_rate",
        "storage_utilization",
        "api_response_time"
      ]
    },
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/credential_manager.log",
      "rotation": {
        "size_mb": 100,
        "backup_count": 10
      },
      "sensitive_data_masking": true
    }
  }
}
```

### Alert Configuration
```json
{
  "alerts": {
    "alert_triggers": [
      {
        "name": "high_failure_rate",
        "condition": "authentication_failure_rate > 0.1",
        "severity": "high",
        "recipients": ["admin@example.com", "security@example.com"],
        "notification_method": ["email", "slack"]
      },
      {
        "name": "storage_full",
        "condition": "storage_utilization > 0.9",
        "severity": "critical",
        "recipients": ["admin@example.com", "ops@example.com"],
        "notification_method": ["email", "sms"]
      },
      {
        "name": "unauthorized_access",
        "condition": "unauthorized_access_attempts > 0",
        "severity": "critical",
        "recipients": ["security@example.com"],
        "notification_method": ["email", "sms"]
      }
    ]
  }
}
```

## Sample Configuration File

Create a `credential_config.json` file with your configuration:

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
    "confidentiality_level": "restricted"
  },
  "storage": {
    "type": "encrypted_file",
    "encrypted_file": {
      "path": "/secure/credentials/",
      "encryption": {
        "algorithm": "AES-256-GCM",
        "key_derivation": "PBKDF2",
        "iterations": 100000
      }
    }
  },
  "master_key": {
    "source": "file",
    "file_path": "/secure/master.key",
    "key_size": 256
  },
  "authentication": {
    "methods": [
      {
        "type": "api_key",
        "enabled": true,
        "required_for_access": true
      }
    ]
  },
  "access_control": {
    "rbac_enabled": true,
    "roles": [
      {
        "name": "admin",
        "permissions": [
          "create_credential",
          "read_credential",
          "update_credential",
          "delete_credential"
        ]
      }
    ]
  },
  "encryption": {
    "algorithm": "AES-256-GCM",
    "key_derivation": {
      "algorithm": "PBKDF2",
      "iterations": 100000
    }
  },
  "rotation_policies": {
    "default": {
      "interval_days": 90,
      "notification_days_before": 7
    }
  }
}
```