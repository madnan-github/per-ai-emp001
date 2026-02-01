# Performance Analyzer Configuration Guide

## Overview
This guide provides comprehensive configuration instructions for the Performance Analyzer skill, which monitors task completion times, identifies operational inefficiencies, and offers actionable insights to improve productivity.

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Required Python packages:
  - pandas (for data manipulation)
  - numpy (for numerical computations)
  - scikit-learn (for machine learning algorithms)
  - matplotlib/seaborn (for visualization)
  - plotly (for interactive charts)
  - scipy (for statistical analysis)
  - statsmodels (for advanced statistics)
  - sqlalchemy (for database connections)
  - requests (for API calls)
  - psutil (for system monitoring)
  - schedule (for automated analysis)

### Environment Variables
Set these environment variables for secure configuration:

```
PERFORMANCE_ANALYZER_DB_PATH=/path/to/performance_data.db
PERFORMANCE_ANALYZER_LOG_LEVEL=INFO
PERFORMANCE_ANALYZER_CONFIG_PATH=/path/to/performance_config.json
PERFORMANCE_ANALYZER_OUTPUT_PATH=/path/to/performance_reports/
PERFORMANCE_ANALYZER_ALERT_EMAIL=admin@example.com
PERFORMANCE_ANALYZER_COMPANY_NAME="Acme Corporation"
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
      "type": "api|database|log_file|system_monitor|manual_input",
      "connection": {
        "url": "connection_url",
        "username_env_var": "USERNAME_ENV_VAR",
        "password_env_var": "PASSWORD_ENV_VAR",
        "api_key_env_var": "API_KEY_ENV_VAR",
        "database_name": "database_name",
        "table_name": "table_name",
        "file_path": "/path/to/data/file.log"
      },
      "schedule": {
        "frequency": "minute|hourly|daily|weekly",
        "interval": 1,
        "timezone": "UTC"
      },
      "metrics": [
        {
          "name": "task_completion_time",
          "type": "numeric",
          "unit": "seconds",
          "description": "Time taken to complete a task"
        }
      ],
      "enabled": true
    }
  ]
}
```

### Supported Data Source Types

#### System Monitoring Sources
```json
{
  "system_monitoring_sources": [
    {
      "id": "system_performance",
      "name": "System Performance Monitor",
      "type": "system_monitor",
      "connection": {
        "monitor_cpu": true,
        "monitor_memory": true,
        "monitor_disk": true,
        "monitor_network": true
      },
      "schedule": {
        "frequency": "minute",
        "interval": 5
      },
      "metrics": [
        {
          "name": "cpu_usage_percent",
          "type": "numeric",
          "unit": "percentage",
          "description": "CPU utilization percentage"
        },
        {
          "name": "memory_usage_percent",
          "type": "numeric",
          "unit": "percentage",
          "description": "Memory utilization percentage"
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
      "id": "task_db",
      "name": "Task Management Database",
      "type": "database",
      "connection": {
        "driver": "postgresql",  // postgresql, mysql, sqlite, mssql
        "host": "db.example.com",
        "port": 5432,
        "database": "tasks",
        "username_env_var": "DB_USERNAME",
        "password_env_var": "DB_PASSWORD"
      },
      "queries": [
        {
          "name": "task_performance",
          "sql": "SELECT task_id, start_time, end_time, status FROM tasks WHERE created_at >= :start_date",
          "parameters": {
            "start_date": "{{last_week_start}}"
          },
          "metrics_mapping": {
            "start_time": "task_start_time",
            "end_time": "task_end_time",
            "status": "task_status"
          }
        }
      ]
    }
  ]
}
```

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
          "endpoint": "/activities",
          "method": "GET",
          "params": {
            "start_date": "{{last_week_start}}",
            "end_date": "{{last_week_end}}"
          },
          "rate_limit": {
            "requests_per_minute": 100
          },
          "metrics_extraction": [
            {
              "source_field": "duration_seconds",
              "metric_name": "activity_duration",
              "metric_type": "numeric",
              "unit": "seconds"
            }
          ]
        }
      ]
    }
  ]
}
```

## Analysis Configuration

### Performance Metrics Configuration
```json
{
  "performance_metrics": {
    "task_performance": {
      "cycle_time": {
        "enabled": true,
        "thresholds": {
          "warning": 3600,  // 1 hour in seconds
          "critical": 7200  // 2 hours in seconds
        },
        "weight": 0.3
      },
      "touch_time": {
        "enabled": true,
        "thresholds": {
          "warning": 1800,  // 30 minutes in seconds
          "critical": 3600  // 1 hour in seconds
        },
        "weight": 0.2
      },
      "wait_time": {
        "enabled": true,
        "thresholds": {
          "warning": 7200,  // 2 hours in seconds
          "critical": 14400  // 4 hours in seconds
        },
        "weight": 0.2
      },
      "success_rate": {
        "enabled": true,
        "thresholds": {
          "warning": 0.8,  // 80%
          "critical": 0.6  // 60%
        },
        "weight": 0.3
      }
    },
    "process_performance": {
      "throughput": {
        "enabled": true,
        "thresholds": {
          "warning": 10,  // 10 tasks per hour
          "critical": 5   // 5 tasks per hour
        },
        "weight": 0.25
      },
      "quality_index": {
        "enabled": true,
        "thresholds": {
          "warning": 0.8,  // 80%
          "critical": 0.6  // 60%
        },
        "weight": 0.25
      }
    }
  }
}
```

### Analysis Algorithms Configuration
```json
{
  "analysis_algorithms": {
    "time_series_analysis": {
      "enabled": true,
      "methods": [
        {
          "name": "moving_average",
          "window_size": 7,
          "weight": 0.3
        },
        {
          "name": "exponential_smoothing",
          "alpha": 0.3,
          "weight": 0.4
        },
        {
          "name": "arima_model",
          "p": 1,
          "d": 1,
          "q": 1,
          "weight": 0.3
        }
      ]
    },
    "anomaly_detection": {
      "enabled": true,
      "methods": [
        {
          "name": "isolation_forest",
          "contamination": 0.1,
          "weight": 0.4
        },
        {
          "name": "z_score",
          "threshold": 3,
          "weight": 0.3
        },
        {
          "name": "iqr_method",
          "factor": 1.5,
          "weight": 0.3
        }
      ]
    },
    "clustering": {
      "enabled": true,
      "algorithm": "kmeans",
      "n_clusters": 5,
      "features": ["cycle_time", "success_rate", "resource_utilization"]
    }
  }
}
```

### Statistical Analysis Configuration
```json
{
  "statistical_analysis": {
    "descriptive_statistics": {
      "enabled": true,
      "measures": [
        "mean",
        "median",
        "mode",
        "std_deviation",
        "variance",
        "min",
        "max",
        "quartiles"
      ]
    },
    "hypothesis_testing": {
      "enabled": true,
      "tests": [
        {
          "name": "t_test",
          "significance_level": 0.05,
          "paired": false
        },
        {
          "name": "chi_square_test",
          "significance_level": 0.05
        }
      ]
    },
    "correlation_analysis": {
      "enabled": true,
      "methods": ["pearson", "spearman"],
      "threshold": 0.5
    },
    "regression_analysis": {
      "enabled": true,
      "methods": [
        {
          "name": "linear_regression",
          "independent_vars": ["task_complexity", "resource_availability"],
          "dependent_var": "completion_time"
        }
      ]
    }
  }
}
```

## Performance Thresholds and Alerting

### Threshold Configuration
```json
{
  "thresholds": {
    "efficiency_metrics": {
      "cycle_time": {
        "optimal_range": [0, 1800],  // 0-30 minutes
        "warning_threshold": 3600,   // 1 hour
        "critical_threshold": 7200   // 2 hours
      },
      "touch_time": {
        "optimal_range": [0, 900],   // 0-15 minutes
        "warning_threshold": 1800,   // 30 minutes
        "critical_threshold": 3600   // 1 hour
      },
      "wait_time": {
        "optimal_range": [0, 1800],  // 0-30 minutes
        "warning_threshold": 7200,   // 2 hours
        "critical_threshold": 14400  // 4 hours
      }
    },
    "quality_metrics": {
      "defect_rate": {
        "optimal_range": [0, 0.05],  // 0-5%
        "warning_threshold": 0.1,    // 10%
        "critical_threshold": 0.2    // 20%
      },
      "first_pass_yield": {
        "optimal_range": [0.95, 1.0], // 95-100%
        "warning_threshold": 0.8,     // 80%
        "critical_threshold": 0.6     // 60%
      }
    },
    "productivity_metrics": {
      "output_per_unit_time": {
        "optimal_range": [5, 10],    // 5-10 units per hour
        "warning_threshold": 3,      // 3 units per hour
        "critical_threshold": 1       // 1 unit per hour
      },
      "resource_utilization": {
        "optimal_range": [0.7, 0.9], // 70-90%
        "warning_threshold": 0.5,    // 50%
        "critical_threshold": 0.3     // 30%
      }
    }
  }
}
```

### Alert Configuration
```json
{
  "alerts": {
    "alert_types": [
      {
        "name": "performance_degradation",
        "condition": "metric_value > critical_threshold",
        "severity": "critical",
        "recipients": ["admin@example.com", "manager@example.com"],
        "notification_methods": ["email", "slack"],
        "escalation_time_minutes": 30
      },
      {
        "name": "efficiency_drop",
        "condition": "efficiency_metric < warning_threshold",
        "severity": "high",
        "recipients": ["manager@example.com"],
        "notification_methods": ["email"],
        "escalation_time_minutes": 60
      },
      {
        "name": "anomaly_detected",
        "condition": "anomaly_score > threshold",
        "severity": "medium",
        "recipients": ["analyst@example.com"],
        "notification_methods": ["email", "dashboard"],
        "escalation_time_minutes": 120
      }
    ],
    "notification_channels": {
      "email": {
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "username_env_var": "SMTP_USERNAME",
        "password_env_var": "SMTP_PASSWORD",
        "sender_email": "alerts@acme.com"
      },
      "slack": {
        "webhook_url_env_var": "SLACK_WEBHOOK_URL",
        "channel": "#performance-alerts"
      },
      "dashboard": {
        "enabled": true,
        "url": "https://dashboard.acme.com/performance-alerts"
      }
    }
  }
}
```

## Report Generation Configuration

### Report Templates
```json
{
  "report_templates": {
    "executive_dashboard": {
      "name": "Executive Performance Dashboard",
      "description": "High-level performance summary for executives",
      "sections": [
        {
          "name": "kpi_summary",
          "title": "Key Performance Indicators",
          "components": ["metric_cards", "trend_charts", "traffic_lights"]
        },
        {
          "name": "performance_trends",
          "title": "Performance Trends",
          "components": ["time_series_charts", "comparison_charts"]
        },
        {
          "name": "top_issues",
          "title": "Top Performance Issues",
          "components": ["issue_list", "priority_matrix"]
        }
      ],
      "schedule": {
        "frequency": "daily",
        "time": "08:00",
        "timezone": "America/New_York"
      }
    },
    "operational_report": {
      "name": "Operational Performance Report",
      "description": "Detailed performance data for managers",
      "sections": [
        {
          "name": "detailed_metrics",
          "title": "Detailed Performance Metrics",
          "components": ["metric_tables", "detailed_charts"]
        },
        {
          "name": "process_analysis",
          "title": "Process Performance Analysis",
          "components": ["process_flow_charts", "bottleneck_analysis"]
        },
        {
          "name": "resource_utilization",
          "title": "Resource Utilization",
          "components": ["resource_charts", "allocation_tables"]
        }
      ],
      "schedule": {
        "frequency": "weekly",
        "day": "monday",
        "time": "09:00",
        "timezone": "America/New_York"
      }
    }
  }
}
```

### Visualization Configuration
```json
{
  "visualizations": {
    "chart_types": {
      "trend_chart": {
        "library": "plotly",
        "default_color": "#1f77b4",
        "width": 800,
        "height": 400
      },
      "bar_chart": {
        "library": "matplotlib",
        "default_color": "#ff7f0e",
        "width": 600,
        "height": 400
      },
      "heatmap": {
        "library": "seaborn",
        "colormap": "viridis",
        "width": 800,
        "height": 600
      },
      "scatter_plot": {
        "library": "plotly",
        "default_color": "#2ca02c",
        "width": 600,
        "height": 400
      }
    },
    "dashboard_settings": {
      "refresh_interval_seconds": 300,
      "auto_refresh": true,
      "responsive_design": true,
      "export_formats": ["png", "pdf", "excel"]
    }
  }
}
```

## Integration Configuration

### Business System Integrations
```json
{
  "integrations": {
    "erp_systems": [
      {
        "name": "sap",
        "enabled": true,
        "connection": {
          "url": "https://sap.example.com",
          "username_env_var": "SAP_USERNAME",
          "password_env_var": "SAP_PASSWORD"
        },
        "data_mapping": {
          "performance_fields": {
            "sap_completion_time": "cycle_time",
            "sap_resource_cost": "cost_per_task"
          }
        }
      }
    ],
    "crm_systems": [
      {
        "name": "salesforce",
        "enabled": true,
        "connection": {
          "instance_url": "https://acme.my.salesforce.com",
          "api_key_env_var": "SF_API_KEY"
        },
        "objects": ["Task", "Activity", "Opportunity"]
      }
    ],
    "project_management": [
      {
        "name": "jira",
        "enabled": true,
        "connection": {
          "url": "https://acme.atlassian.net",
          "username_env_var": "JIRA_USERNAME",
          "api_token_env_var": "JIRA_TOKEN"
        },
        "fields": ["timeoriginalestimate", "timespent", "status", "assignee"]
      }
    ]
  }
}
```

### Monitoring Tool Integrations
```json
{
  "monitoring_integrations": {
    "apm_tools": [
      {
        "name": "datadog",
        "enabled": true,
        "api_key_env_var": "DATADOG_API_KEY",
        "app_key_env_var": "DATADOG_APP_KEY",
        "metrics_prefix": "performance_analyzer."
      }
    ],
    "log_management": [
      {
        "name": "elasticsearch",
        "enabled": true,
        "connection": {
          "url": "https://elastic.example.com",
          "username_env_var": "ELASTIC_USERNAME",
          "password_env_var": "ELASTIC_PASSWORD"
        },
        "indices": ["performance_logs-*"]
      }
    ]
  }
}
```

## Security Configuration

### Authentication and Authorization
```json
{
  "security": {
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
    },
    "access_control": {
      "rbac_enabled": true,
      "roles": [
        {
          "name": "admin",
          "permissions": ["full_access", "configure_system", "manage_users", "view_all_data"]
        },
        {
          "name": "analyst",
          "permissions": ["run_analysis", "view_reports", "create_dashboards"]
        },
        {
          "name": "viewer",
          "permissions": ["view_reports", "view_dashboards"]
        }
      ]
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
      "performance_data": "2_years",
      "raw_logs": "1_year",
      "reports": "5_years",
      "automated_cleanup": true
    }
  }
}
```

## Performance Tuning

### Resource Management
```json
{
  "performance_tuning": {
    "data_processing": {
      "max_workers": 8,
      "chunk_size": 10000,
      "memory_limit_mb": 2048,
      "processing_timeout_minutes": 30
    },
    "analysis_engine": {
      "max_concurrent_analyses": 5,
      "analysis_timeout_minutes": 15,
      "cache_enabled": true,
      "cache_size_mb": 512
    },
    "visualization": {
      "max_points_per_chart": 10000,
      "chart_rendering_timeout_seconds": 60,
      "caching_enabled": true,
      "cache_duration_minutes": 60
    }
  }
}
```

### Caching Configuration
```json
{
  "caching": {
    "data_cache": {
      "enabled": true,
      "ttl_minutes": 60,
      "max_size_mb": 512,
      "eviction_policy": "lru"
    },
    "analysis_cache": {
      "enabled": true,
      "ttl_minutes": 120,
      "max_size_mb": 256,
      "eviction_policy": "lru"
    },
    "report_cache": {
      "enabled": true,
      "ttl_minutes": 30,
      "max_reports": 50,
      "storage_path": "/tmp/report_cache/"
    }
  }
}
```

## Scheduling Configuration

### Analysis Schedule
```json
{
  "scheduling": {
    "data_collection_schedule": {
      "frequency": "hourly",
      "time": "00:05",  // 5 minutes past each hour
      "timezone": "UTC",
      "timeout_minutes": 30
    },
    "analysis_schedule": {
      "frequency": "hourly",
      "time": "00:30",  // 30 minutes past each hour
      "timezone": "UTC",
      "timeout_minutes": 60
    },
    "report_generation_schedule": {
      "executive_dashboard": {
        "frequency": "daily",
        "time": "08:00",
        "timezone": "America/New_York"
      },
      "operational_report": {
        "frequency": "weekly",
        "day": "monday",
        "time": "09:00",
        "timezone": "America/New_York"
      }
    },
    "maintenance_schedule": {
      "cleanup_task": {
        "frequency": "daily",
        "time": "02:00",
        "timezone": "UTC"
      },
      "backup_task": {
        "frequency": "daily",
        "time": "03:00",
        "timezone": "UTC"
      }
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
      "data_collection_success": true,
      "analysis_engine_health": true,
      "report_generation_success": true,
      "system_resources": true,
      "integration_connectivity": true
    },
    "metrics_collection": {
      "enabled": true,
      "collection_interval_minutes": 5,
      "metrics": [
        "data_collection_time",
        "analysis_time",
        "report_generation_time",
        "error_rate",
        "successful_analyses",
        "active_connections"
      ]
    },
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/performance_analyzer.log",
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
        "name": "data_collection_failure",
        "condition": "data_collection_error_rate > 0.1",
        "severity": "high",
        "recipients": ["admin@example.com"],
        "notification_method": "email"
      },
      {
        "name": "analysis_engine_failure",
        "condition": "analysis_failure_rate > 0.05",
        "severity": "critical",
        "recipients": ["admin@example.com", "ops@example.com"],
        "notification_method": ["email", "slack"]
      },
      {
        "name": "performance_degradation",
        "condition": "avg_cycle_time > critical_threshold",
        "severity": "high",
        "recipients": ["manager@example.com"],
        "notification_method": "email"
      }
    ]
  }
}
```

## Sample Configuration File

Create a `performance_config.json` file with your configuration:

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
  "data_sources": [
    {
      "id": "task_db",
      "name": "Task Management Database",
      "type": "database",
      "connection": {
        "driver": "postgresql",
        "host": "tasks-db.internal",
        "port": 5432,
        "database": "task_manager",
        "username_env_var": "TASK_DB_USER",
        "password_env_var": "TASK_DB_PASS"
      },
      "queries": [
        {
          "name": "task_performance",
          "sql": "SELECT task_id, start_time, end_time, status FROM tasks WHERE created_at >= :start_date",
          "parameters": {
            "start_date": "{{last_week_start}}"
          },
          "metrics_mapping": {
            "start_time": "task_start_time",
            "end_time": "task_end_time",
            "status": "task_status"
          }
        }
      ],
      "schedule": {
        "frequency": "hourly",
        "interval": 1,
        "timezone": "UTC"
      }
    }
  ],
  "performance_metrics": {
    "task_performance": {
      "cycle_time": {
        "enabled": true,
        "thresholds": {
          "warning": 3600,
          "critical": 7200
        },
        "weight": 0.3
      },
      "success_rate": {
        "enabled": true,
        "thresholds": {
          "warning": 0.8,
          "critical": 0.6
        },
        "weight": 0.3
      }
    }
  },
  "thresholds": {
    "efficiency_metrics": {
      "cycle_time": {
        "optimal_range": [0, 1800],
        "warning_threshold": 3600,
        "critical_threshold": 7200
      }
    }
  },
  "scheduling": {
    "data_collection_schedule": {
      "frequency": "hourly",
      "time": "00:05",
      "timezone": "UTC"
    },
    "analysis_schedule": {
      "frequency": "hourly",
      "time": "00:30",
      "timezone": "UTC"
    }
  }
}
```