# Dashboard Updater Configuration Guide

## Overview
This guide provides comprehensive configuration instructions for the Dashboard Updater skill, which maintains real-time dashboards with key metrics, ensuring stakeholders have access to the most current business intelligence.

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Node.js 14+ (for frontend components)
- Required Python packages:
  - flask (for web server)
  - flask-socketio (for real-time updates)
  - pandas (for data manipulation)
  - numpy (for numerical computations)
  - redis (for caching)
  - celery (for background tasks)
  - requests (for API calls)
  - sqlalchemy (for database connections)
  - schedule (for scheduled updates)
  - plotly (for interactive charts)
  - psycopg2-binary (for PostgreSQL) or mysql-connector-python (for MySQL)

### Environment Variables
Set these environment variables for secure configuration:

```
DASHBOARD_DB_URL=postgresql://user:pass@localhost/dashboard_db
DASHBOARD_REDIS_URL=redis://localhost:6379/0
DASHBOARD_SERVER_HOST=0.0.0.0
DASHBOARD_SERVER_PORT=5000
DASHBOARD_LOG_LEVEL=INFO
DASHBOARD_SECRET_KEY=your-secret-key-here
DASHBOARD_API_KEY=your-api-key-here
DASHBOARD_COMPANY_NAME="Acme Corporation"
```

## Dashboard Configuration

### Dashboard Definition Format
Each dashboard is defined with the following structure:

```json
{
  "dashboards": [
    {
      "id": "dashboard_unique_identifier",
      "name": "Dashboard Name",
      "description": "Dashboard description",
      "layout": {
        "rows": 4,
        "columns": 6,
        "widgets": [
          {
            "id": "widget_001",
            "type": "chart",
            "title": "Revenue Trend",
            "position": {"row": 0, "col": 0, "width": 3, "height": 2},
            "component": "line_chart",
            "data_source": "revenue_data",
            "refresh_interval": 300
          }
        ]
      },
      "permissions": {
        "view_roles": ["admin", "executive", "manager"],
        "edit_roles": ["admin"],
        "share_with": ["team1", "team2"]
      },
      "enabled": true
    }
  ]
}
```

### Widget Types
```json
{
  "widget_types": {
    "chart": {
      "supported_charts": ["line", "bar", "pie", "area", "scatter", "gauge"],
      "configuration": {
        "title": "string",
        "x_axis": "string",
        "y_axis": "string",
        "color_scheme": "string",
        "legend_position": "top|bottom|right|left",
        "refresh_interval": "integer (seconds)"
      }
    },
    "metric": {
      "supported_metrics": ["counter", "gauge", "progress", "status"],
      "configuration": {
        "title": "string",
        "metric_type": "counter|gauge|progress|status",
        "format": "number|currency|percentage|time",
        "thresholds": {
          "warning": "number",
          "critical": "number"
        },
        "refresh_interval": "integer (seconds)"
      }
    },
    "table": {
      "configuration": {
        "title": "string",
        "columns": ["array of column definitions"],
        "pagination": true,
        "sortable": true,
        "searchable": true,
        "refresh_interval": "integer (seconds)"
      }
    },
    "text": {
      "configuration": {
        "title": "string",
        "content": "string (markdown supported)",
        "refresh_interval": "integer (seconds)"
      }
    }
  }
}
```

## Data Source Configuration

### Data Source Definition Format
Each data source is defined with the following structure:

```json
{
  "data_sources": [
    {
      "id": "source_unique_identifier",
      "name": "Source Name",
      "type": "api|database|file|streaming|websocket",
      "connection": {
        "url": "connection_url",
        "username_env_var": "USERNAME_ENV_VAR",
        "password_env_var": "PASSWORD_ENV_VAR",
        "api_key_env_var": "API_KEY_ENV_VAR",
        "database_name": "database_name",
        "table_name": "table_name",
        "file_path": "/path/to/data/file.csv"
      },
      "schedule": {
        "frequency": "realtime|minute|hourly|daily|weekly",
        "interval": 300,
        "timezone": "UTC"
      },
      "mapping": {
        "field_mappings": {
          "source_field_name": "dashboard_field_name"
        },
        "filters": [
          {
            "field": "date",
            "operator": "gte|lte|eq|neq",
            "value": "last_week"
          }
        ]
      },
      "enabled": true
    }
  ]
}
```

### Supported Data Source Types

#### API Sources
```json
{
  "api_sources": [
    {
      "id": "crm_api",
      "name": "CRM System API",
      "type": "api",
      "connection": {
        "url": "https://crm.example.com/api/v1",
        "api_key_env_var": "CRM_API_KEY",
        "headers": {
          "Content-Type": "application/json",
          "Authorization": "Bearer {{api_key}}"
        }
      },
      "endpoints": [
        {
          "endpoint": "/opportunities",
          "method": "GET",
          "params": {
            "start_date": "{{last_week_start}}",
            "end_date": "{{last_week_end}}"
          },
          "rate_limit": {
            "requests_per_minute": 100
          },
          "response_mapping": {
            "data_path": "$.opportunities",
            "field_mapping": {
              "id": "opportunity_id",
              "name": "opportunity_name",
              "amount": "opportunity_amount",
              "stage": "opportunity_stage"
            }
          }
        }
      ]
    }
  ]
}
```

#### Database Sources
```json
{
  "database_sources": [
    {
      "id": "analytics_db",
      "name": "Analytics Database",
      "type": "database",
      "connection": {
        "driver": "postgresql",  // postgresql, mysql, sqlite, mssql
        "host": "db.example.com",
        "port": 5432,
        "database": "analytics",
        "username_env_var": "DB_USERNAME",
        "password_env_var": "DB_PASSWORD"
      },
      "queries": [
        {
          "name": "daily_revenue",
          "sql": "SELECT date, revenue FROM daily_revenue WHERE date >= :start_date ORDER BY date DESC LIMIT 30",
          "parameters": {
            "start_date": "{{last_month_start}}"
          },
          "field_mapping": {
            "date": "date",
            "revenue": "revenue"
          }
        }
      ]
    }
  ]
}
```

#### Streaming Sources
```json
{
  "streaming_sources": [
    {
      "id": "realtime_metrics",
      "name": "Real-time Metrics Stream",
      "type": "streaming",
      "connection": {
        "url": "wss://metrics.example.com/ws",
        "auth_token_env_var": "METRICS_AUTH_TOKEN"
      },
      "topics": [
        {
          "topic": "revenue",
          "mapping": {
            "timestamp": "timestamp",
            "amount": "revenue"
          }
        }
      ]
    }
  ]
}
```

## Update Mechanism Configuration

### Real-time Update Settings
```json
{
  "real_time_updates": {
    "websocket": {
      "enabled": true,
      "ping_interval": 25,
      "ping_timeout": 60,
      "max_http_buffer_size": 100000,
      "cors_allowed_origins": ["*"]
    },
    "server_sent_events": {
      "enabled": false,
      "heartbeat_interval": 30,
      "buffer_size": 1000
    },
    "polling": {
      "enabled": true,
      "default_interval": 30,
      "min_interval": 5,
      "max_interval": 3600
    }
  }
}
```

### Scheduled Update Configuration
```json
{
  "scheduled_updates": {
    "update_schedules": [
      {
        "name": "high_freq_metrics",
        "interval": 60,
        "timezone": "UTC",
        "data_sources": ["realtime_metrics"],
        "dashboards": ["executive_dashboard"]
      },
      {
        "name": "daily_metrics",
        "interval": 3600,
        "timezone": "America/New_York",
        "data_sources": ["crm_api", "analytics_db"],
        "dashboards": ["operational_dashboard", "financial_dashboard"]
      },
      {
        "name": "weekly_summary",
        "interval": 86400,
        "timezone": "UTC",
        "data_sources": ["all_sources"],
        "dashboards": ["executive_dashboard"]
      }
    ]
  }
}
```

### Conditional Update Configuration
```json
{
  "conditional_updates": {
    "threshold_based": {
      "enabled": true,
      "checks": [
        {
          "data_source": "revenue_data",
          "field": "revenue_change_pct",
          "operator": "gt",
          "threshold": 5.0,
          "action": "immediate_update"
        },
        {
          "data_source": "error_rate",
          "field": "error_rate",
          "operator": "gt",
          "threshold": 0.01,
          "action": "alert_and_update"
        }
      ]
    },
    "anomaly_detection": {
      "enabled": true,
      "algorithm": "isolation_forest",
      "contamination": 0.1,
      "update_on_anomaly": true
    },
    "change_detection": {
      "enabled": true,
      "threshold": 0.01,
      "comparison_method": "percentage_change",
      "update_on_change": true
    }
  }
}
```

## Dashboard Layout Configuration

### Layout Templates
```json
{
  "layout_templates": {
    "executive_dashboard": {
      "name": "Executive Dashboard",
      "description": "High-level KPIs for executives",
      "grid_size": {
        "columns": 12,
        "row_height": 100
      },
      "widgets": [
        {
          "id": "revenue_kpi",
          "type": "metric",
          "title": "Total Revenue",
          "position": {"x": 0, "y": 0, "w": 3, "h": 2},
          "data_source": "revenue_data",
          "field": "total_revenue",
          "format": "currency",
          "refresh_interval": 300
        },
        {
          "id": "revenue_trend",
          "type": "chart",
          "title": "Revenue Trend",
          "position": {"x": 3, "y": 0, "w": 6, "h": 4},
          "chart_type": "line",
          "data_source": "revenue_data",
          "x_axis": "date",
          "y_axis": "revenue",
          "refresh_interval": 600
        },
        {
          "id": "customer_satisfaction",
          "type": "chart",
          "title": "Customer Satisfaction",
          "position": {"x": 9, "y": 0, "w": 3, "h": 4},
          "chart_type": "gauge",
          "data_source": "satisfaction_data",
          "field": "satisfaction_score",
          "refresh_interval": 900
        }
      ]
    },
    "operational_dashboard": {
      "name": "Operational Dashboard",
      "description": "Real-time operational metrics",
      "grid_size": {
        "columns": 12,
        "row_height": 80
      },
      "widgets": [
        {
          "id": "active_processes",
          "type": "metric",
          "title": "Active Processes",
          "position": {"x": 0, "y": 0, "w": 2, "h": 2},
          "data_source": "process_data",
          "field": "active_count",
          "refresh_interval": 30
        },
        {
          "id": "system_health",
          "type": "chart",
          "title": "System Health",
          "position": {"x": 2, "y": 0, "w": 10, "h": 2},
          "chart_type": "bar",
          "data_source": "health_data",
          "x_axis": "service",
          "y_axis": "status",
          "refresh_interval": 60
        }
      ]
    }
  }
}
```

### Responsive Design Settings
```json
{
  "responsive_design": {
    "breakpoints": {
      "mobile": 576,
      "tablet": 768,
      "desktop": 1024,
      "large_desktop": 1200
    },
    "layouts": {
      "mobile": {
        "columns": 1,
        "row_height": 150
      },
      "tablet": {
        "columns": 2,
        "row_height": 120
      },
      "desktop": {
        "columns": 4,
        "row_height": 100
      },
      "large_desktop": {
        "columns": 6,
        "row_height": 80
      }
    }
  }
}
```

## Alert and Notification Configuration

### Alert Types and Thresholds
```json
{
  "alerts": {
    "threshold_alerts": [
      {
        "id": "revenue_decline",
        "name": "Revenue Decline Alert",
        "description": "Alert when revenue declines significantly",
        "data_source": "revenue_data",
        "field": "revenue_change_pct",
        "operator": "lt",
        "threshold": -5.0,
        "severity": "high",
        "recipients": ["finance-team@example.com", "executives@example.com"],
        "notification_methods": ["email", "dashboard_banner"]
      },
      {
        "id": "high_error_rate",
        "name": "High Error Rate Alert",
        "description": "Alert when error rate exceeds threshold",
        "data_source": "system_metrics",
        "field": "error_rate",
        "operator": "gt",
        "threshold": 0.05,
        "severity": "critical",
        "recipients": ["ops-team@example.com", "tech-lead@example.com"],
        "notification_methods": ["email", "sms", "slack"]
      }
    ],
    "trend_alerts": [
      {
        "id": "declining_trend",
        "name": "Declining Trend Alert",
        "description": "Alert when metrics show sustained decline",
        "data_source": "any_data",
        "field": "metric_value",
        "trend_direction": "decreasing",
        "duration": 7,  // days
        "severity": "medium",
        "recipients": ["relevant-team@example.com"],
        "notification_methods": ["email"]
      }
    ]
  }
}
```

### Notification Channel Configuration
```json
{
  "notification_channels": {
    "email": {
      "smtp_server": "smtp.example.com",
      "smtp_port": 587,
      "username_env_var": "SMTP_USERNAME",
      "password_env_var": "SMTP_PASSWORD",
      "sender_email": "dashboard-alerts@acme.com",
      "use_tls": true
    },
    "sms": {
      "provider": "twilio",
      "account_sid_env_var": "TWILIO_ACCOUNT_SID",
      "auth_token_env_var": "TWILIO_AUTH_TOKEN",
      "from_number": "+1234567890"
    },
    "slack": {
      "webhook_url_env_var": "SLACK_WEBHOOK_URL",
      "channel": "#dashboard-alerts",
      "bot_name": "Dashboard Alert Bot"
    },
    "push_notifications": {
      "enabled": true,
      "service": "firebase",
      "credentials_path_env_var": "FCM_CREDENTIALS_PATH"
    }
  }
}
```

## Security Configuration

### Authentication and Authorization
```json
{
  "security": {
    "authentication": {
      "methods": [
        {
          "type": "oauth2",
          "provider": "google",
          "client_id_env_var": "GOOGLE_CLIENT_ID",
          "client_secret_env_var": "GOOGLE_CLIENT_SECRET"
        },
        {
          "type": "basic_auth",
          "enabled": true,
          "users_env_var": "DASHBOARD_USERS_JSON"
        }
      ]
    },
    "authorization": {
      "rbac_enabled": true,
      "roles": [
        {
          "name": "admin",
          "permissions": [
            "view_dashboard", "edit_dashboard", "manage_users",
            "configure_alerts", "access_all_data", "manage_settings"
          ]
        },
        {
          "name": "executive",
          "permissions": [
            "view_dashboard", "view_executive_dashboards",
            "receive_alerts", "view_reports"
          ]
        },
        {
          "name": "manager",
          "permissions": [
            "view_dashboard", "view_managed_dashboards",
            "receive_relevant_alerts"
          ]
        },
        {
          "name": "analyst",
          "permissions": [
            "view_dashboard", "view_analytical_dashboards",
            "download_data", "create_filters"
          ]
        }
      ]
    },
    "session_management": {
      "timeout_minutes": 120,
      "remember_me_timeout_days": 30,
      "max_concurrent_sessions": 5
    }
  }
}
```

### Data Privacy and Compliance
```json
{
  "privacy_compliance": {
    "data_classification": {
      "levels": ["public", "internal", "confidential", "restricted"],
      "default_level": "internal"
    },
    "gdpr_compliance": {
      "right_to_access": true,
      "right_to_rectification": true,
      "right_to_erasure": true,
      "data_portability": true,
      "consent_management": true
    },
    "data_retention": {
      "dashboard_data": "2_years",
      "access_logs": "1_year",
      "alert_history": "5_years",
      "automated_cleanup": true
    },
    "masking_rules": [
      {
        "field_patterns": ["credit_card", "ssn", "phone"],
        "masking_type": "partial_mask",
        "visible_chars": 2
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
    "data_cache": {
      "enabled": true,
      "backend": "redis",
      "ttl_seconds": 300,
      "max_size_mb": 512,
      "eviction_policy": "lru"
    },
    "widget_cache": {
      "enabled": true,
      "ttl_seconds": 60,
      "max_widgets": 100
    },
    "chart_cache": {
      "enabled": true,
      "ttl_seconds": 120,
      "max_charts": 50,
      "storage_path": "/tmp/chart_cache/"
    },
    "dashboard_cache": {
      "enabled": true,
      "ttl_seconds": 30,
      "max_dashboards": 20
    }
  }
}
```

### Resource Management
```json
{
  "performance_tuning": {
    "data_processing": {
      "max_workers": 8,
      "chunk_size": 10000,
      "memory_limit_mb": 2048,
      "processing_timeout_minutes": 10
    },
    "rendering": {
      "max_concurrent_renders": 10,
      "render_timeout_seconds": 30,
      "canvas_pool_size": 5
    },
    "api_limits": {
      "max_requests_per_minute": 1000,
      "max_payload_size_kb": 1024,
      "rate_limit_window_seconds": 60
    }
  }
}
```

## Integration Configuration

### System Integrations
```json
{
  "integrations": {
    "business_systems": [
      {
        "name": "salesforce",
        "enabled": true,
        "connection": {
          "instance_url": "https://acme.my.salesforce.com",
          "api_key_env_var": "SF_API_KEY"
        },
        "objects": ["Opportunity", "Account", "Contact"],
        "sync_frequency": 300
      },
      {
        "name": "sap",
        "enabled": true,
        "connection": {
          "url": "https://sap.example.com",
          "username_env_var": "SAP_USERNAME",
          "password_env_var": "SAP_PASSWORD"
        },
        "modules": ["FI", "CO", "SD"],
        "sync_frequency": 1800
      }
    ],
    "analytics_platforms": [
      {
        "name": "google_analytics",
        "enabled": true,
        "connection": {
          "property_id": "GA_PROPERTY_ID",
          "api_secret_env_var": "GA_API_SECRET"
        },
        "metrics": ["sessions", "users", "bounceRate"],
        "dimensions": ["date", "deviceCategory", "country"],
        "sync_frequency": 3600
      }
    ]
  }
}
```

### Third-party Services
```json
{
  "third_party_services": [
    {
      "name": "weather_api",
      "enabled": true,
      "provider": "openweathermap",
      "api_key_env_var": "WEATHER_API_KEY",
      "location": "New York,NY,US",
      "sync_frequency": 3600,
      "data_mapping": {
        "temperature": "weather_temp",
        "humidity": "weather_humidity",
        "condition": "weather_condition"
      }
    }
  ]
}
```

## Monitoring and Alerting

### Health Checks
```json
{
  "monitoring": {
    "health_checks": {
      "data_pipeline_health": true,
      "dashboard_server_health": true,
      "database_connections": true,
      "cache_health": true,
      "external_api_health": true
    },
    "metrics_collection": {
      "enabled": true,
      "collection_interval_minutes": 5,
      "metrics": [
        "data_update_latency",
        "dashboard_load_time",
        "api_response_time",
        "error_rate",
        "active_connections",
        "memory_usage",
        "cpu_usage"
      ]
    },
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/dashboard_updater.log",
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
        "condition": "error_rate > 0.05",
        "severity": "critical",
        "recipients": ["admin@example.com"],
        "notification_method": "email"
      },
      {
        "name": "slow_response_time",
        "condition": "avg_response_time > 5.0",
        "severity": "high",
        "recipients": ["admin@example.com", "ops@example.com"],
        "notification_method": ["email", "slack"]
      },
      {
        "name": "data_pipeline_failure",
        "condition": "data_update_failures > 3",
        "severity": "critical",
        "recipients": ["admin@example.com", "data-team@example.com"],
        "notification_method": ["email", "sms"]
      }
    ]
  }
}
```

## Backup and Recovery

### Backup Configuration
```json
{
  "backup": {
    "schedule": {
      "full_backup": {
        "frequency": "daily",
        "time": "02:00",
        "timezone": "UTC"
      },
      "incremental_backup": {
        "frequency": "hourly",
        "retention_days": 7
      }
    },
    "storage": {
      "local_path": "/backups/dashboard/",
      "remote_storage": {
        "enabled": true,
        "provider": "aws_s3",
        "bucket": "dashboard-backups-bucket",
        "access_key_env_var": "AWS_ACCESS_KEY",
        "secret_key_env_var": "AWS_SECRET_KEY"
      }
    },
    "retention": {
      "daily_backups": 30,
      "weekly_backups": 8,
      "monthly_backups": 12
    }
  }
}
```

### Disaster Recovery
```json
{
  "disaster_recovery": {
    "recovery_procedures": {
      "data_loss": {
        "procedure": "restore_from_backup",
        "target_recovery_time": 3600,
        "target_recovery_point": 300
      },
      "system_outage": {
        "procedure": "failover_to_standby",
        "target_recovery_time": 600,
        "target_recovery_point": 60
      }
    },
    "standby_setup": {
      "enabled": true,
      "replication_interval": 300,
      "health_check_interval": 60
    }
  }
}
```

## Sample Configuration File

Create a `dashboard_config.json` file with your configuration:

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
  "dashboards": [
    {
      "id": "executive_dashboard",
      "name": "Executive Dashboard",
      "description": "High-level KPIs for executives",
      "layout": {
        "rows": 4,
        "columns": 6,
        "widgets": [
          {
            "id": "revenue_widget",
            "type": "chart",
            "title": "Revenue Trend",
            "position": {"row": 0, "col": 0, "width": 3, "height": 2},
            "component": "line_chart",
            "data_source": "revenue_data",
            "refresh_interval": 300
          }
        ]
      },
      "permissions": {
        "view_roles": ["admin", "executive"],
        "edit_roles": ["admin"]
      },
      "enabled": true
    }
  ],
  "data_sources": [
    {
      "id": "revenue_db",
      "name": "Revenue Database",
      "type": "database",
      "connection": {
        "driver": "postgresql",
        "host": "revenue-db.internal",
        "port": 5432,
        "database": "revenue_data",
        "username_env_var": "REVENUE_DB_USER",
        "password_env_var": "REVENUE_DB_PASS"
      },
      "queries": [
        {
          "name": "daily_revenue",
          "sql": "SELECT date, revenue FROM daily_revenue WHERE date >= :start_date ORDER BY date DESC LIMIT 30",
          "parameters": {
            "start_date": "{{last_month_start}}"
          },
          "field_mapping": {
            "date": "date",
            "revenue": "revenue"
          }
        }
      ]
    }
  ],
  "real_time_updates": {
    "websocket": {
      "enabled": true,
      "ping_interval": 25,
      "ping_timeout": 60
    }
  },
  "scheduled_updates": {
    "update_schedules": [
      {
        "name": "daily_metrics",
        "interval": 3600,
        "timezone": "America/New_York",
        "data_sources": ["revenue_db"],
        "dashboards": ["executive_dashboard"]
      }
    ]
  }
}
```