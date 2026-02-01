# Scheduler Coordinator Configuration Guide

## Overview
This guide provides comprehensive configuration instructions for the Scheduler Coordinator skill, which provides centralized task scheduling and coordination for the Personal AI Employee system.

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Required Python packages:
  - APScheduler (for advanced scheduling)
  - redis (for distributed scheduling)
  - celery (for task queuing)
  - kombu (for messaging)
  - sqlalchemy (for database integration)
  - psutil (for system monitoring)
  - requests (for API calls)

### Environment Variables
Set these environment variables for secure configuration:

```
SCHEDULER_COORDINATOR_DATABASE_PATH=/data/schedule_registry.db
SCHEDULER_COORDINATOR_LOG_LEVEL=INFO
SCHEDULER_COORDINATOR_WORKER_COUNT=4
SCHEDULER_COORDINATOR_QUEUE_BACKEND=redis
SCHEDULER_COORDINATOR_REDIS_URL=redis://localhost:6379/0
SCHEDULER_COORDINATOR_MAX_TASK_DURATION_SECONDS=3600
SCHEDULER_COORDINATOR_HEARTBEAT_INTERVAL_SECONDS=30
SCHEDULER_COORDINATOR_ALERT_EMAIL=admin@example.com
```

## Scheduling Configuration

### Basic Scheduling Options
```json
{
  "scheduling": {
    "default_timezone": "UTC",
    "scheduler_type": "apscheduler",  // apscheduler, celery, or custom
    "job_stores": {
      "default": {
        "type": "sqlalchemy",
        "url": "sqlite:///jobs.sqlite"
      }
    },
    "executors": {
      "default": {
        "type": "threadpool",
        "max_workers": 20
      },
      "processpool": {
        "type": "processpool",
        "max_workers": 5
      }
    },
    "job_defaults": {
      "coalesce": false,
      "max_instances": 3,
      "misfire_grace_time": 30
    }
  }
}
```

### Task Execution Configuration
```json
{
  "execution": {
    "worker_pool": {
      "min_workers": 2,
      "max_workers": 10,
      "worker_timeout_seconds": 300
    },
    "task_limits": {
      "max_execution_time_seconds": 3600,
      "max_memory_mb": 512,
      "max_cpu_percent": 80
    },
    "concurrency": {
      "max_concurrent_tasks": 5,
      "queue_size": 100
    }
  }
}
```

## Priority and Resource Configuration

### Priority Settings
```json
{
  "priorities": {
    "levels": {
      "critical": {
        "value": 1,
        "max_concurrent": 1,
        "timeout_multiplier": 1.0
      },
      "high": {
        "value": 10,
        "max_concurrent": 3,
        "timeout_multiplier": 1.2
      },
      "normal": {
        "value": 50,
        "max_concurrent": 5,
        "timeout_multiplier": 1.5
      },
      "low": {
        "value": 100,
        "max_concurrent": 10,
        "timeout_multiplier": 2.0
      }
    },
    "default_priority": "normal"
  }
}
```

### Resource Allocation
```json
{
  "resources": {
    "allocation_strategy": "weighted_round_robin",  // weighted_round_robin, priority_based, or fair_share
    "system_limits": {
      "cpu_threshold_percent": 80,
      "memory_threshold_percent": 85,
      "disk_threshold_percent": 90,
      "network_threshold_mbps": 100
    },
    "task_resources": {
      "default": {
        "cpu_percent": 10,
        "memory_mb": 128,
        "disk_iops": 100
      },
      "critical": {
        "cpu_percent": 25,
        "memory_mb": 256,
        "disk_iops": 200
      }
    }
  }
}
```

## Retry and Failure Handling Configuration

### Retry Policies
```json
{
  "retry_policies": {
    "default": {
      "strategy": "exponential",
      "max_attempts": 3,
      "initial_delay_seconds": 1,
      "backoff_factor": 2.0,
      "max_delay_seconds": 60
    },
    "transient_errors": {
      "strategy": "fixed",
      "max_attempts": 5,
      "delay_seconds": 5
    },
    "network_errors": {
      "strategy": "exponential",
      "max_attempts": 3,
      "initial_delay_seconds": 2,
      "backoff_factor": 3.0
    }
  }
}
```

### Circuit Breaker Configuration
```json
{
  "circuit_breaker": {
    "enabled": true,
    "failure_threshold": 5,
    "timeout_seconds": 60,
    "recovery_threshold": 3
  }
}
```

## Queue and Messaging Configuration

### Queue Backend Options
```json
{
  "queues": {
    "backend": "redis",  // redis, rabbitmq, or database
    "redis": {
      "url": "redis://localhost:6379/0",
      "password_env_var": "REDIS_PASSWORD",
      "socket_timeout": 30,
      "connection_pool_size": 20
    },
    "rabbitmq": {
      "url": "amqp://guest:guest@localhost:5672//",
      "virtual_host": "/",
      "heartbeat": 60
    },
    "database": {
      "url": "sqlite:///tasks.db",
      "pool_size": 10,
      "pool_timeout": 30
    }
  }
}
```

### Queue Configuration
```json
{
  "queue_settings": {
    "default_queue": "default",
    "queues": {
      "critical": {
        "routing_key": "critical",
        "priority": 1,
        "max_length": 1000,
        "consumers": 3
      },
      "high": {
        "routing_key": "high",
        "priority": 10,
        "max_length": 1000,
        "consumers": 2
      },
      "normal": {
        "routing_key": "normal",
        "priority": 50,
        "max_length": 1000,
        "consumers": 1
      },
      "low": {
        "routing_key": "low",
        "priority": 100,
        "max_length": 1000,
        "consumers": 1
      }
    }
  }
}
```

## Dependency Management Configuration

### Dependency Resolution
```json
{
  "dependencies": {
    "resolution_strategy": "breadth_first",  // breadth_first, depth_first, or priority_based
    "cycle_detection": true,
    "timeout_seconds": 300,
    "max_depth": 10,
    "validation": {
      "enabled": true,
      "strict_mode": false
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
        "task_execution_rate",
        "queue_length",
        "worker_utilization",
        "system_resources",
        "task_success_rate"
      ]
    },
    "health_checks": {
      "scheduler_health": true,
      "worker_health": true,
      "queue_connectivity": true,
      "database_connectivity": true
    },
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/scheduler_coordinator.log",
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
        "name": "high_queue_length",
        "condition": "queue_length > 100",
        "severity": "medium",
        "recipients": ["admin@example.com"],
        "notification_method": ["email", "slack"]
      },
      {
        "name": "scheduler_down",
        "condition": "scheduler_health == false",
        "severity": "critical",
        "recipients": ["admin@example.com", "ops@example.com"],
        "notification_method": ["email", "sms"]
      },
      {
        "name": "task_failure_rate",
        "condition": "failure_rate > 0.1",
        "severity": "high",
        "recipients": ["admin@example.com"],
        "notification_method": ["email", "slack"]
      },
      {
        "name": "resource_saturation",
        "condition": "cpu_usage > 0.9 || memory_usage > 0.95",
        "severity": "high",
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
        "sender_email": "scheduler@acme.com"
      },
      "slack": {
        "enabled": true,
        "webhook_url_env_var": "SLACK_WEBHOOK_URL",
        "channel": "#scheduler-alerts"
      },
      "dashboard": {
        "enabled": true,
        "url": "https://dashboard.acme.com/scheduler"
      }
    },
    "event_triggers": [
      {
        "name": "task_completed",
        "condition": "task_status == 'completed'",
        "recipients": ["task_owner@example.com"],
        "channels": ["email", "dashboard"]
      },
      {
        "name": "task_failed",
        "condition": "task_status == 'failed'",
        "recipients": ["admin@example.com", "task_owner@example.com"],
        "channels": ["email", "slack"]
      },
      {
        "name": "dependency_blocked",
        "condition": "dependency_status == 'blocked'",
        "recipients": ["admin@example.com"],
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
      "cpu_percentage": 70,
      "memory_percentage": 50,
      "disk_io_percentage": 60,
      "network_bandwidth_limit_mbps": 100
    },
    "threading": {
      "worker_threads": 10,
      "io_threads": 5,
      "management_threads": 2
    },
    "caching": {
      "enabled": true,
      "backend": "redis",
      "ttl_seconds": 300,
      "max_entries": 1000
    }
  }
}
```

## Integration Configuration

### External System Integration
```json
{
  "integrations": {
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
    ],
    "task_queues": [
      {
        "name": "celery",
        "enabled": true,
        "broker_url": "redis://localhost:6379/0",
        "result_backend": "redis://localhost:6379/0"
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
    "port": 8082,
    "ssl": {
      "enabled": true,
      "cert_path": "/secure/server.crt",
      "key_path": "/secure/server.key"
    },
    "authentication": {
      "enabled": true,
      "method": "api_key",
      "api_key_env_var": "SCHEDULER_API_KEY"
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

### Access Control Configuration
```json
{
  "access_control": {
    "rbac_enabled": true,
    "roles": [
      {
        "name": "scheduler_admin",
        "permissions": [
          "create_task",
          "modify_task",
          "delete_task",
          "view_schedules",
          "manage_workers",
          "view_metrics"
        ]
      },
      {
        "name": "task_creator",
        "permissions": [
          "create_task",
          "view_own_tasks",
          "cancel_own_tasks"
        ]
      },
      {
        "name": "scheduler_viewer",
        "permissions": [
          "view_schedules",
          "view_metrics"
        ]
      }
    ]
  }
}
```

## Sample Configuration File

Create a `scheduler_config.json` file with your configuration:

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
    "max_concurrent_tasks": 5,
    "default_priority": "normal"
  },
  "scheduling": {
    "scheduler_type": "apscheduler",
    "job_stores": {
      "default": {
        "type": "sqlalchemy",
        "url": "sqlite:///jobs.sqlite"
      }
    },
    "executors": {
      "default": {
        "type": "threadpool",
        "max_workers": 20
      }
    }
  },
  "execution": {
    "worker_pool": {
      "min_workers": 2,
      "max_workers": 10
    },
    "task_limits": {
      "max_execution_time_seconds": 3600
    }
  },
  "priorities": {
    "default_priority": "normal",
    "levels": {
      "critical": {
        "value": 1,
        "max_concurrent": 1
      },
      "high": {
        "value": 10,
        "max_concurrent": 3
      },
      "normal": {
        "value": 50,
        "max_concurrent": 5
      },
      "low": {
        "value": 100,
        "max_concurrent": 10
      }
    }
  },
  "queues": {
    "backend": "redis",
    "redis": {
      "url": "redis://localhost:6379/0"
    }
  },
  "monitoring": {
    "enabled": true,
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/scheduler_coordinator.log"
    }
  }
}
```