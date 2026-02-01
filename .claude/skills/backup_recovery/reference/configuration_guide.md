# Backup & Recovery Configuration Guide

## Overview
This guide provides comprehensive configuration instructions for the Backup & Recovery skill, which provides automated backup and recovery of critical data for the Personal AI Employee system.

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Required Python packages:
  - paramiko (for remote backups)
  - boto3 (for cloud storage)
  - py7zr (for 7z compression)
  - cryptography (for encryption)
  - sqlite3 (for backup catalog)
  - schedule (for backup scheduling)
  - psutil (for system monitoring)

### Environment Variables
Set these environment variables for secure configuration:

```
BACKUP_RECOVERY_STORAGE_PATH=/backups/
BACKUP_RECOVERY_LOG_LEVEL=INFO
BACKUP_RECOVERY_DATABASE_PATH=/data/backup_catalog.db
BACKUP_RECOVERY_ENCRYPTION_KEY_PATH=/secure/backup.key
BACKUP_RECOVERY_RETENTION_DAYS=30
BACKUP_RECOVERY_COMPRESSION=gzip
BACKUP_RECOVERY_VERIFICATION_ENABLED=true
BACKUP_RECOVERY_ALERT_EMAIL=admin@example.com
```

## Backup Storage Configuration

### Storage Backend Options
```json
{
  "storage": {
    "type": "hybrid",  // local, remote, cloud, or hybrid
    "local": {
      "path": "/backups/",
      "retention_days": 7,
      "compression": "gzip",
      "encryption": true
    },
    "remote": {
      "type": "sftp",
      "host": "backup.example.com",
      "port": 22,
      "username": "backup_user",
      "password_env_var": "BACKUP_SFTP_PASSWORD",
      "path": "/remote/backups/"
    },
    "cloud": {
      "type": "s3",  // s3, azure_blob, google_cloud_storage
      "bucket": "my-backup-bucket",
      "region": "us-east-1",
      "access_key_env_var": "AWS_ACCESS_KEY_ID",
      "secret_key_env_var": "AWS_SECRET_ACCESS_KEY"
    },
    "hybrid": {
      "primary": "local",
      "secondary": "cloud",
      "sync_strategy": "async_replication"
    }
  }
}
```

### Encryption Configuration
```json
{
  "encryption": {
    "enabled": true,
    "algorithm": "AES-256-GCM",
    "key_size": 256,
    "key_derivation": {
      "algorithm": "PBKDF2",
      "iterations": 100000,
      "salt_size": 128
    },
    "key_management": {
      "source": "file",  // file, environment, or hsm
      "file_path": "/secure/backup.key",
      "environment_variable": "BACKUP_ENCRYPTION_KEY"
    }
  }
}
```

## Backup Scheduling Configuration

### Schedule Definitions
```json
{
  "schedules": {
    "daily_incremental": {
      "type": "incremental",
      "cron_expression": "0 2 * * *",  // Daily at 2 AM
      "retention_days": 7,
      "include_paths": [
        "/home/user/Documents/",
        "/home/user/Pictures/",
        "/Data/"
      ],
      "exclude_patterns": [
        "*.tmp",
        "*.cache",
        "/temp/",
        "*.log"
      ]
    },
    "weekly_full": {
      "type": "full",
      "cron_expression": "0 1 * * 0",  // Weekly at 1 AM on Sunday
      "retention_days": 30,
      "include_paths": [
        "/home/user/",
        "/Data/",
        "/Configs/"
      ]
    },
    "hourly_critical": {
      "type": "incremental",
      "cron_expression": "0 * * * *",  // Hourly
      "retention_days": 1,
      "include_paths": [
        "/Data/critical_data/",
        "/Configs/"
      ]
    }
  }
}
```

### Advanced Scheduling
```json
{
  "advanced_scheduling": {
    "adaptive_backup": {
      "enabled": true,
      "change_threshold": 0.1,  // 10% change triggers backup
      "monitoring_paths": [
        "/Data/",
        "/Configs/"
      ],
      "max_frequency_minutes": 30
    },
    "event_driven": {
      "enabled": true,
      "triggers": [
        {
          "type": "file_change",
          "paths": ["/Configs/", "/Data/critical_data/"],
          "action": "immediate_backup"
        },
        {
          "type": "pre_operation",
          "operations": ["system_update", "software_install"],
          "action": "backup_before_operation"
        }
      ]
    }
  }
}
```

## Compression Configuration

### Compression Settings
```json
{
  "compression": {
    "default_algorithm": "gzip",
    "algorithms": {
      "gzip": {
        "enabled": true,
        "compression_level": 6,
        "speed_vs_size": "balanced"
      },
      "bzip2": {
        "enabled": true,
        "compression_level": 9,
        "speed_vs_size": "size_optimized"
      },
      "xz": {
        "enabled": true,
        "compression_level": 6,
        "speed_vs_size": "size_optimized"
      },
      "7z": {
        "enabled": true,
        "compression_level": 5,
        "encryption": true
      }
    },
    "thresholds": {
      "min_file_size_kb": 100,
      "compression_enabled": true
    }
  }
}
```

## Retention and Cleanup Policies

### Retention Policies
```json
{
  "retention_policies": {
    "default": {
      "full_backup_retention_days": 30,
      "incremental_backup_retention_days": 7,
      "differential_backup_retention_days": 14
    },
    "critical_data": {
      "full_backup_retention_days": 90,
      "incremental_backup_retention_days": 14,
      "monthly_snapshot_retention_days": 365
    },
    "compliance": {
      "retention_days": 730,  // 2 years for compliance
      "legal_hold_enabled": true,
      "immutable_backup": true
    }
  },
  "cleanup_schedule": {
    "cron_expression": "0 3 * * *",  // Daily at 3 AM
    "batch_size": 100,
    "grace_period_hours": 24
  }
}
```

## Recovery Configuration

### Recovery Settings
```json
{
  "recovery": {
    "verification_enabled": true,
    "parallel_restore_threads": 4,
    "restore_validation": {
      "checksum_verification": true,
      "file_integrity_check": true,
      "metadata_validation": true
    },
    "rollback_enabled": true,
    "point_in_time_recovery": {
      "enabled": true,
      "granularity_minutes": 15,
      "log_retention_days": 30
    }
  }
}
```

## Monitoring and Alerting Configuration

### Monitoring Settings
```json
{
  "monitoring": {
    "enabled": true,
    "metrics_collection": {
      "collection_interval_minutes": 5,
      "metrics": [
        "backup_success_rate",
        "storage_utilization",
        "backup_duration",
        "network_throughput",
        "compression_ratio"
      ]
    },
    "health_checks": {
      "storage_connectivity": true,
      "backup_service_availability": true,
      "encryption_functionality": true,
      "catalog_integrity": true
    },
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/backup_recovery.log",
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
        "name": "backup_failure",
        "condition": "consecutive_failures > 2",
        "severity": "high",
        "recipients": ["admin@example.com", "ops@example.com"],
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
        "name": "recovery_failure",
        "condition": "recovery_attempts > 3",
        "severity": "critical",
        "recipients": ["admin@example.com"],
        "notification_method": ["email", "sms"]
      },
      {
        "name": "slow_backup",
        "condition": "backup_duration > expected_duration * 2",
        "severity": "medium",
        "recipients": ["admin@example.com"],
        "notification_method": ["email"]
      }
    ]
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
        "sender_email": "backups@acme.com"
      },
      "slack": {
        "enabled": true,
        "webhook_url_env_var": "SLACK_WEBHOOK_URL",
        "channel": "#backup-alerts"
      },
      "dashboard": {
        "enabled": true,
        "url": "https://dashboard.acme.com/backups"
      }
    },
    "event_triggers": [
      {
        "name": "backup_completed",
        "condition": "backup_status == 'success'",
        "recipients": ["admin@example.com"],
        "channels": ["email", "dashboard"]
      },
      {
        "name": "backup_failed",
        "condition": "backup_status == 'failed'",
        "recipients": ["admin@example.com", "ops@example.com"],
        "channels": ["email", "slack"]
      },
      {
        "name": "recovery_completed",
        "condition": "recovery_status == 'success'",
        "recipients": ["requestor@example.com"],
        "channels": ["email"]
      }
    ]
  }
}
```

## Performance Tuning

### Resource Management
```json
{
  "performance": {
    "resource_limits": {
      "cpu_percentage": 50,
      "memory_percentage": 30,
      "disk_io_percentage": 40,
      "network_bandwidth_limit_mbps": 100
    },
    "threading": {
      "backup_threads": 4,
      "restore_threads": 4,
      "verification_threads": 2,
      "compression_threads": 2
    },
    "bandwidth_shaping": {
      "enabled": true,
      "throttling_schedule": {
        "work_hours": "20 Mbps",
        "off_hours": "100 Mbps"
      }
    }
  }
}
```

## Integration Configuration

### External System Integration
```json
{
  "integrations": {
    "cloud_storage": [
      {
        "name": "aws_s3",
        "enabled": true,
        "region": "us-east-1",
        "bucket": "my-backup-bucket",
        "access_key_env_var": "AWS_ACCESS_KEY_ID",
        "secret_key_env_var": "AWS_SECRET_ACCESS_KEY"
      },
      {
        "name": "azure_blob",
        "enabled": false,
        "account_name": "myaccount",
        "container": "backups",
        "account_key_env_var": "AZURE_ACCOUNT_KEY"
      },
      {
        "name": "google_cloud_storage",
        "enabled": false,
        "bucket": "my-backup-bucket",
        "credentials_path": "/secure/gcp_credentials.json"
      }
    ],
    "monitoring_tools": [
      {
        "name": "prometheus",
        "enabled": true,
        "endpoint": "http://prometheus:9090",
        "push_gateway": "http://pushgateway:9091"
      },
      {
        "name": "datadog",
        "enabled": false,
        "api_key_env_var": "DATADOG_API_KEY",
        "site": "datadoghq.com"
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
    "port": 8081,
    "ssl": {
      "enabled": true,
      "cert_path": "/secure/server.crt",
      "key_path": "/secure/server.key"
    },
    "authentication": {
      "enabled": true,
      "method": "api_key",
      "api_key_env_var": "BACKUP_API_KEY"
    },
    "rate_limiting": {
      "enabled": true,
      "requests_per_minute": 100,
      "burst_capacity": 200
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
      "require_api_key": true
    }
  }
}
```

### File System Security
```json
{
  "file_security": {
    "backup_directory": {
      "path": "/backups/",
      "owner": "backup_service",
      "group": "backup_group",
      "permissions": "700"
    },
    "log_directory": {
      "path": "/logs/",
      "owner": "backup_service",
      "group": "backup_group",
      "permissions": "750"
    },
    "config_directory": {
      "path": "/etc/backups/",
      "owner": "root",
      "group": "backup_group",
      "permissions": "640"
    }
  }
}
```

## Compliance Configuration

### Compliance Settings
```json
{
  "compliance": {
    "standards": {
      "soc2": {
        "enabled": true,
        "requirements": [
          "data_backup",
          "disaster_recovery",
          "access_monitoring",
          "audit_logging"
        ]
      },
      "gdpr": {
        "enabled": true,
        "requirements": [
          "data_portability",
          "right_to_erasure",
          "data_minimization"
        ]
      },
      "hipaa": {
        "enabled": true,
        "requirements": [
          "data_backup",
          "disaster_recovery",
          "access_controls",
          "audit_logging"
        ]
      }
    },
    "retention_policies": {
      "audit_logs": "7_years",
      "backup_metadata": "7_years",
      "recovery_records": "7_years"
    }
  }
}
```

## Sample Configuration File

Create a `backup_config.json` file with your configuration:

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
    "backup_retention_days": 30,
    "encryption_enabled": true
  },
  "storage": {
    "type": "hybrid",
    "local": {
      "path": "/backups/",
      "retention_days": 7,
      "compression": "gzip"
    },
    "cloud": {
      "type": "s3",
      "bucket": "my-backup-bucket",
      "region": "us-east-1"
    }
  },
  "schedules": {
    "daily_incremental": {
      "type": "incremental",
      "cron_expression": "0 2 * * *",
      "retention_days": 7,
      "include_paths": ["/Data/", "/Configs/"]
    }
  },
  "encryption": {
    "enabled": true,
    "algorithm": "AES-256-GCM",
    "key_derivation": {
      "algorithm": "PBKDF2",
      "iterations": 100000
    }
  },
  "monitoring": {
    "enabled": true,
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/backup_recovery.log"
    }
  }
}
```