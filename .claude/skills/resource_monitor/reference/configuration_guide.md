# Resource Monitor Configuration Guide

## Overview
This guide provides comprehensive configuration instructions for the Resource Monitor skill, which provides continuous monitoring and management of system resources for the Personal AI Employee system.

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Required Python packages:
  - psutil (for system monitoring)
  - influxdb (for time-series storage)
  - prometheus-client (for metrics exposure)
  - grafana-sdk (for dashboard creation)
  - requests (for API calls)
  - schedule (for scheduling)

### Environment Variables
Set these environment variables for secure configuration:

```
RESOURCE_MONITOR_DATABASE_URL=influxdb://localhost:8086/resource_db
RESOURCE_MONITOR_LOG_LEVEL=INFO
RESOURCE_MONITOR_ALERT_EMAIL=admin@example.com
RESOURCE_MONITOR_METRICS_PORT=9090
RESOURCE_MONITOR_COLLECTION_INTERVAL_SECONDS=30
RESOURCE_MONITOR_RETENTION_DAYS=30
RESOURCE_MONITOR_MAX_METRICS_AGE_DAYS=7
```

## Resource Monitoring Configuration

### Basic Monitoring Settings
```json
{
  "monitoring": {
    "collection_interval_seconds": 30,
    "aggregation_window_seconds": 300,
    "retention_days": 30,
    "max_metrics_age_days": 7,
    "batch_size": 100,
    "buffer_size": 1000
  }
}
```

### Resource Types Configuration
```json
{
  "resources": {
    "cpu": {
      "enabled": true,
      "collection_interval": 10,
      "metrics": [
        "usage_percent",
        "load_average",
        "core_usage"
      ],
      "thresholds": {
        "warning": 80,
        "critical": 90
      }
    },
    "memory": {
      "enabled": true,
      "collection_interval": 15,
      "metrics": [
        "usage_percent",
        "available_mb",
        "cached_mb",
        "buffers_mb"
      ],
      "thresholds": {
        "warning": 85,
        "critical": 95
      }
    },
    "disk": {
      "enabled": true,
      "collection_interval": 60,
      "paths": ["/", "/home", "/tmp"],
      "metrics": [
        "usage_percent",
        "free_space_gb",
        "read_write_operations"
      ],
      "thresholds": {
        "warning": 80,
        "critical": 95
      }
    },
    "network": {
      "enabled": true,
      "collection_interval": 30,
      "interfaces": ["eth0", "wlan0"],
      "metrics": [
        "bytes_sent",
        "bytes_recv",
        "packets_sent",
        "packets_recv",
        "drop_rate"
      ],
      "thresholds": {
        "warning": 80,
        "critical": 95
      }
    }
  }
}
```

## Alert Configuration

### Alert Thresholds
```json
{
  "alerts": {
    "thresholds": {
      "cpu_usage": {
        "warning": 80,
        "critical": 90,
        "duration_seconds": 60
      },
      "memory_usage": {
        "warning": 85,
        "critical": 95,
        "duration_seconds": 120
      },
      "disk_usage": {
        "warning": 80,
        "critical": 95,
        "duration_seconds": 300
      },
      "network_bandwidth": {
        "warning": 80,
        "critical": 95,
        "duration_seconds": 60
      }
    }
  }
}
```

### Alert Conditions
```json
{
  "alert_conditions": {
    "simple": {
      "operator": "gt",  // gt, lt, eq, gte, lte
      "value": 80,
      "duration": 60
    },
    "complex": {
      "type": "composite",
      "conditions": [
        {
          "metric": "cpu_usage",
          "operator": "gt",
          "value": 80,
          "weight": 1.0
        },
        {
          "metric": "memory_usage",
          "operator": "gt",
          "value": 85,
          "weight": 1.5
        }
      ],
      "threshold": 1.25,
      "duration": 120
    }
  }
}
```

## Data Storage Configuration

### Storage Backend Options
```json
{
  "storage": {
    "type": "timeseries",  // timeseries, relational, or document
    "timeseries": {
      "backend": "influxdb",  // influxdb, prometheus, or timescaledb
      "influxdb": {
        "url": "http://localhost:8086",
        "database": "resource_monitor",
        "username": "monitor_user",
        "password_env_var": "INFLUXDB_PASSWORD",
        "retention_policy": "autogen",
        "retention_duration": "30d"
      },
      "prometheus": {
        "enabled": true,
        "port": 9090,
        "namespace": "resource_monitor",
        "path": "/metrics"
      }
    },
    "relational": {
      "backend": "postgresql",  // postgresql, mysql, or sqlite
      "postgresql": {
        "host": "localhost",
        "port": 5432,
        "database": "resource_monitor",
        "username": "monitor_user",
        "password_env_var": "POSTGRES_PASSWORD"
      }
    }
  }
}
```

### Data Retention Policies
```json
{
  "retention": {
    "realtime": {
      "duration_days": 1,
      "resolution_seconds": 10
    },
    "hourly": {
      "duration_days": 30,
      "resolution_seconds": 3600
    },
    "daily": {
      "duration_days": 365,
      "resolution_seconds": 86400
    },
    "cleanup_schedule": {
      "cron_expression": "0 2 * * *",  // Daily at 2 AM
      "batch_size": 1000
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
        "sender_email": "monitor@acme.com"
      },
      "slack": {
        "enabled": true,
        "webhook_url_env_var": "SLACK_WEBHOOK_URL",
        "channel": "#infrastructure-alerts"
      },
      "webhook": {
        "enabled": true,
        "url": "https://hooks.example.com/monitoring",
        "headers": {
          "Authorization": "Bearer ${WEBHOOK_TOKEN}"
        }
      },
      "dashboard": {
        "enabled": true,
        "url": "https://dashboard.acme.com/monitoring"
      }
    },
    "recipients": {
      "warning": ["admin@example.com", "ops@example.com"],
      "critical": ["admin@example.com", "pager-duty@example.com"]
    }
  }
}
```

### Alert Routing
```json
{
  "alert_routing": {
    "routes": [
      {
        "matchers": [
          {
            "name": "severity",
            "value": "critical",
            "operator": "="
          }
        ],
        "receivers": ["critical_alerts"],
        "group_by": ["alertname", "severity"],
        "group_wait": "30s",
        "group_interval": "5m",
        "repeat_interval": "1h"
      },
      {
        "matchers": [
          {
            "name": "severity",
            "value": "warning",
            "operator": "="
          }
        ],
        "receivers": ["warning_alerts"],
        "group_by": ["alertname"],
        "group_wait": "1m",
        "group_interval": "10m",
        "repeat_interval": "4h"
      }
    ],
    "receivers": [
      {
        "name": "critical_alerts",
        "email_configs": [
          {
            "to": ["admin@example.com", "pager-duty@example.com"],
            "send_resolved": true
          }
        ],
        "slack_configs": [
          {
            "channel": "#critical-alerts",
            "send_resolved": true
          }
        ]
      },
      {
        "name": "warning_alerts",
        "email_configs": [
          {
            "to": ["admin@example.com", "ops@example.com"],
            "send_resolved": true
          }
        ]
      }
    ]
  }
}
```

## Performance Tuning

### Resource Limits
```json
{
  "performance": {
    "resource_limits": {
      "cpu_percentage": 10,
      "memory_percentage": 5,
      "disk_io_percentage": 5,
      "network_bandwidth_limit_mbps": 10
    },
    "collection_frequency": {
      "high_freq_resources": {
        "cpu": 10,
        "memory": 15
      },
      "normal_freq_resources": {
        "disk": 60,
        "network": 30
      },
      "low_freq_resources": {
        "temperature": 300,
        "processes": 120
      }
    },
    "buffering": {
      "enabled": true,
      "size": 1000,
      "flush_interval_seconds": 5,
      "max_batch_size": 100
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
        "scrape_interval_seconds": 30,
        "endpoint": "http://prometheus:9090",
        "push_gateway": "http://pushgateway:9091"
      },
      {
        "name": "grafana",
        "enabled": true,
        "url": "http://grafana:3000",
        "api_key_env_var": "GRAFANA_API_KEY"
      },
      {
        "name": "datadog",
        "enabled": false,
        "api_key_env_var": "DATADOG_API_KEY",
        "site": "datadoghq.com"
      }
    ],
    "notification_services": [
      {
        "name": "pagerduty",
        "enabled": true,
        "integration_key_env_var": "PAGERDUTY_INTEGRATION_KEY"
      },
      {
        "name": "opsgenie",
        "enabled": false,
        "api_key_env_var": "OPSGENIE_API_KEY"
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
    "port": 8083,
    "ssl": {
      "enabled": true,
      "cert_path": "/secure/server.crt",
      "key_path": "/secure/server.key"
    },
    "authentication": {
      "enabled": true,
      "method": "api_key",
      "api_key_env_var": "MONITOR_API_KEY"
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

### Data Security
```json
{
  "data_security": {
    "encryption_at_rest": {
      "enabled": true,
      "algorithm": "AES-256",
      "key_rotation_days": 90
    },
    "encryption_in_transit": {
      "enabled": true,
      "protocol": "TLSv1.3"
    },
    "data_masking": {
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

## Monitoring Configuration

### Self-Monitoring
```json
{
  "self_monitoring": {
    "enabled": true,
    "metrics": [
      "monitor_uptime",
      "collection_success_rate",
      "alert_generation_rate",
      "storage_utilization",
      "processing_latency"
    ],
    "health_checks": {
      "storage_connectivity": true,
      "collection_agents": true,
      "notification_services": true,
      "api_endpoints": true
    }
  }
}
```

### Alert Configuration
```json
{
  "monitoring_alerts": {
    "alert_triggers": [
      {
        "name": "monitor_down",
        "condition": "uptime < 0.95",
        "severity": "critical",
        "recipients": ["admin@example.com", "ops@example.com"],
        "notification_method": ["email", "sms"]
      },
      {
        "name": "collection_failure",
        "condition": "collection_failure_rate > 0.1",
        "severity": "high",
        "recipients": ["admin@example.com"],
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
        "name": "high_latency",
        "condition": "processing_latency > 5000",
        "severity": "medium",
        "recipients": ["admin@example.com"],
        "notification_method": ["email"]
      }
    ]
  }
}
```

## Sample Configuration File

Create a `monitor_config.json` file with your configuration:

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
    "collection_interval_seconds": 30,
    "retention_days": 30
  },
  "monitoring": {
    "collection_interval_seconds": 30,
    "aggregation_window_seconds": 300
  },
  "resources": {
    "cpu": {
      "enabled": true,
      "collection_interval": 10,
      "thresholds": {
        "warning": 80,
        "critical": 90
      }
    },
    "memory": {
      "enabled": true,
      "collection_interval": 15,
      "thresholds": {
        "warning": 85,
        "critical": 95
      }
    },
    "disk": {
      "enabled": true,
      "collection_interval": 60,
      "paths": ["/", "/home"],
      "thresholds": {
        "warning": 80,
        "critical": 95
      }
    }
  },
  "storage": {
    "type": "timeseries",
    "timeseries": {
      "backend": "influxdb",
      "influxdb": {
        "url": "http://localhost:8086",
        "database": "resource_monitor"
      }
    }
  },
  "alerts": {
    "thresholds": {
      "cpu_usage": {
        "warning": 80,
        "critical": 90
      }
    }
  },
  "notifications": {
    "channels": {
      "email": {
        "enabled": true,
        "sender_email": "monitor@acme.com"
      }
    },
    "recipients": {
      "critical": ["admin@example.com"]
    }
  }
}
```