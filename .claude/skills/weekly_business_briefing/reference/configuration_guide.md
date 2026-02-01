# Weekly Business Briefing Configuration Guide

## Overview
This guide provides comprehensive configuration instructions for the Weekly Business Briefing skill, which generates comprehensive CEO-style briefings summarizing key business metrics, identifying bottlenecks, providing strategic insights, and offering actionable recommendations.

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Required Python packages:
  - pandas (for data manipulation)
  - numpy (for numerical computations)
  - matplotlib (for visualization)
  - seaborn (for statistical graphics)
  - jinja2 (for templating)
  - requests (for API calls)
  - sqlalchemy (for database connections)
  - schedule (for automated scheduling)
  - openpyxl (for Excel support)
  - reportlab (for PDF generation)
  - plotly (for interactive charts)

### Environment Variables
Set these environment variables for secure configuration:

```
BRIEFING_DATA_SOURCES_PATH=/path/to/data_sources.json
BRIEFING_OUTPUT_PATH=/path/to/briefing_output/
BRIEFING_TEMPLATES_PATH=/path/to/templates/
BRIEFING_LOG_LEVEL=INFO
BRIEFING_SMTP_SERVER=smtp.example.com
BRIEFING_SMTP_PORT=587
BRIEFING_EMAIL_USER=briefings@example.com
BRIEFING_EMAIL_PASSWORD_ENV_VAR=EMAIL_APP_PASSWORD
BRIEFING_COMPANY_NAME="Acme Corporation"
```

## Data Source Configuration

### Data Sources Definition Format
Each data source is defined with the following structure:

```json
{
  "sources": [
    {
      "id": "source_unique_identifier",
      "name": "Source Name",
      "type": "api|database|file|spreadsheet|streaming",
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
        "frequency": "hourly|daily|weekly|monthly",
        "interval": 24,
        "timezone": "UTC"
      },
      "mapping": {
        "field_mappings": {
          "source_field_name": "target_field_name"
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
      "id": "finance_db",
      "name": "Financial Database",
      "type": "database",
      "connection": {
        "driver": "postgresql",  # postgresql, mysql, sqlite, mssql
        "host": "db.example.com",
        "port": 5432,
        "database": "finance",
        "username_env_var": "DB_USERNAME",
        "password_env_var": "DB_PASSWORD"
      },
      "queries": [
        {
          "name": "weekly_revenue",
          "sql": "SELECT SUM(amount) as revenue FROM transactions WHERE transaction_date BETWEEN :start_date AND :end_date",
          "parameters": {
            "start_date": "{{last_week_start}}",
            "end_date": "{{last_week_end}}"
          }
        }
      ]
    }
  ]
}
```

#### File Sources
```json
{
  "file_sources": [
    {
      "id": "sales_spreadsheet",
      "name": "Sales Spreadsheet",
      "type": "spreadsheet",
      "connection": {
        "file_path": "/data/sales.xlsx",
        "sheet_name": "Weekly Sales",
        "range": "A1:Z1000"
      },
      "schedule": {
        "frequency": "daily",
        "time": "02:00",
        "timezone": "America/New_York"
      }
    }
  ]
}
```

## Briefing Template Configuration

### Template Structure
```json
{
  "templates": {
    "ceo_briefing": {
      "name": "CEO Weekly Briefing",
      "description": "Comprehensive briefing for CEO with all key metrics",
      "sections": [
        {
          "name": "executive_summary",
          "title": "Executive Summary",
          "order": 1,
          "required": true,
          "components": ["kpi_summary", "highlight_metrics", "trend_analysis"]
        },
        {
          "name": "financial_performance",
          "title": "Financial Performance",
          "order": 2,
          "required": true,
          "components": ["revenue_analysis", "expense_tracking", "profit_margins"]
        },
        {
          "name": "operational_metrics",
          "title": "Operational Metrics",
          "order": 3,
          "required": true,
          "components": ["productivity_measures", "quality_indicators", "timeline_adherence"]
        },
        {
          "name": "market_analysis",
          "title": "Market Analysis",
          "order": 4,
          "required": false,
          "components": ["competitive_position", "customer_insights", "industry_trends"]
        },
        {
          "name": "recommendations",
          "title": "Strategic Recommendations",
          "order": 5,
          "required": true,
          "components": ["action_items", "opportunities", "risk_mitigation"]
        }
      ],
      "visualization_settings": {
        "chart_types": ["bar", "line", "pie", "scatter"],
        "color_scheme": "corporate",
        "dimensions": {
          "width": 800,
          "height": 600
        }
      },
      "formatting_options": {
        "font_family": "Arial",
        "font_size": 12,
        "theme": "professional"
      }
    },
    "department_head_briefing": {
      "name": "Department Head Briefing",
      "description": "Focused briefing for department heads",
      "sections": [
        {
          "name": "department_overview",
          "title": "Department Overview",
          "order": 1,
          "required": true,
          "components": ["dept_kpis", "team_performance", "budget_utilization"]
        },
        {
          "name": "project_status",
          "title": "Project Status",
          "order": 2,
          "required": true,
          "components": ["ongoing_projects", "milestone_achievements", "resource_allocation"]
        },
        {
          "name": "challenges_opportunities",
          "title": "Challenges & Opportunities",
          "order": 3,
          "required": true,
          "components": ["current_challenges", "improvement_areas", "growth_opportunities"]
        }
      ]
    }
  }
}
```

### Component Definitions
```json
{
  "components": {
    "kpi_summary": {
      "type": "metric_grid",
      "title": "Key Performance Indicators",
      "data_source": "kpi_metrics",
      "layout": {
        "rows": 2,
        "columns": 3
      },
      "metrics": [
        {
          "name": "revenue_growth",
          "title": "Revenue Growth",
          "calculation": "percentage_change",
          "format": "percent",
          "thresholds": {
            "positive": 0.05,
            "negative": -0.05
          }
        },
        {
          "name": "customer_acquisition",
          "title": "Customer Acquisition",
          "calculation": "count_new_customers",
          "format": "number",
          "thresholds": {
            "target": 50
          }
        }
      ]
    },
    "trend_analysis": {
      "type": "time_series_chart",
      "title": "Trend Analysis",
      "data_source": "historical_metrics",
      "chart_type": "line",
      "time_period": "last_12_months",
      "metrics": [
        {
          "name": "monthly_revenue",
          "title": "Monthly Revenue",
          "color": "#1f77b4"
        },
        {
          "name": "monthly_expenses",
          "title": "Monthly Expenses",
          "color": "#ff7f0e"
        }
      ]
    }
  }
}
```

## Data Processing Configuration

### Data Transformation Rules
```json
{
  "data_processing": {
    "transformations": [
      {
        "name": "normalize_currency",
        "type": "currency_conversion",
        "source_currency": "USD",
        "target_currency": "EUR",
        "conversion_rate_source": "api_exchange_rates"
      },
      {
        "name": "aggregate_by_department",
        "type": "group_by",
        "group_by_field": "department",
        "aggregations": [
          {
            "field": "revenue",
            "function": "sum"
          },
          {
            "field": "expenses",
            "function": "sum"
          },
          {
            "field": "employee_count",
            "function": "count"
          }
        ]
      },
      {
        "name": "calculate_ratios",
        "type": "derived_metrics",
        "calculations": [
          {
            "name": "profit_margin",
            "formula": "(revenue - expenses) / revenue * 100",
            "depends_on": ["revenue", "expenses"]
          },
          {
            "name": "revenue_per_employee",
            "formula": "revenue / employee_count",
            "depends_on": ["revenue", "employee_count"]
          }
        ]
      }
    ],
    "data_quality": {
      "validation_rules": [
        {
          "field": "revenue",
          "condition": "gte",
          "value": 0,
          "severity": "error"
        },
        {
          "field": "date",
          "condition": "not_null",
          "severity": "warning"
        }
      ],
      "outlier_detection": {
        "enabled": true,
        "method": "iqr|z_score",
        "threshold": 3
      }
    }
  }
}
```

### Data Filtering and Segmentation
```json
{
  "filtering": {
    "date_filters": {
      "default_period": "last_week",
      "supported_periods": ["last_week", "last_month", "last_quarter", "ytd", "rolling_12_months"],
      "custom_date_ranges": true
    },
    "dimension_filters": [
      {
        "name": "department",
        "values": ["sales", "marketing", "operations", "finance", "hr"],
        "default_selection": ["all"]
      },
      {
        "name": "region",
        "values": ["north_america", "europe", "asia_pacific", "latin_america"],
        "default_selection": ["all"]
      }
    ],
    "metric_filters": {
      "top_n": 10,
      "threshold": {
        "revenue": 10000,
        "margin": 0.1
      }
    }
  }
}
```

## Distribution Configuration

### Recipient Management
```json
{
  "distribution": {
    "recipients": [
      {
        "id": "ceo_001",
        "name": "CEO",
        "email": "ceo@example.com",
        "template": "ceo_briefing",
        "delivery_method": "email",
        "delivery_schedule": "weekly",
        "delivery_day": "monday",
        "delivery_time": "08:00",
        "timezone": "America/New_York",
        "attachments": ["pdf", "excel"]
      },
      {
        "id": "dept_head_sales",
        "name": "Sales Director",
        "email": "sales.director@example.com",
        "template": "department_head_briefing",
        "delivery_method": "email",
        "delivery_schedule": "weekly",
        "delivery_day": "monday",
        "delivery_time": "09:00",
        "timezone": "America/New_York",
        "department_filter": "sales"
      }
    ],
    "delivery_methods": {
      "email": {
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "username_env_var": "SMTP_USERNAME",
        "password_env_var": "SMTP_PASSWORD",
        "use_tls": true,
        "sender_email": "briefings@acme.com",
        "subject_template": "[Weekly Briefing] Business Summary for Week Ending {{date}}"
      },
      "dashboard": {
        "enabled": true,
        "url": "https://dashboard.acme.com/briefings",
        "auto_publish": true
      }
    }
  }
}
```

### Output Format Configuration
```json
{
  "output_formats": {
    "pdf": {
      "enabled": true,
      "template": "briefing_pdf_template.html",
      "page_size": "A4",
      "orientation": "portrait",
      "margins": {
        "top": 20,
        "bottom": 20,
        "left": 15,
        "right": 15
      },
      "include_charts": true,
      "include_tables": true
    },
    "excel": {
      "enabled": true,
      "sheets": [
        {
          "name": "summary",
          "include_components": ["kpi_summary", "trend_analysis"]
        },
        {
          "name": "detailed_data",
          "include_components": ["raw_data", "supporting_metrics"]
        }
      ],
      "include_charts": true
    },
    "html": {
      "enabled": true,
      "template": "interactive_briefing.html",
      "include_interactive_elements": true,
      "refresh_interval_minutes": 60
    }
  }
}
```

## Scheduling Configuration

### Briefing Generation Schedule
```json
{
  "scheduling": {
    "generation_schedule": {
      "frequency": "weekly",
      "day_of_week": "sunday",  # Day when data collection begins
      "time": "23:00",
      "timezone": "UTC",
      "retry_attempts": 3,
      "retry_delay_minutes": 30
    },
    "data_collection_schedule": {
      "pre_generation_offset_hours": 2,  # Collect data 2 hours before generation
      "timeout_minutes": 60,
      "concurrent_data_fetching": true,
      "max_concurrent_sources": 5
    },
    "delivery_schedule": {
      "post_generation_offset_hours": 1,  # Deliver 1 hour after generation
      "delivery_window_start": "06:00",
      "delivery_window_end": "18:00",
      "batch_delivery_size": 10,
      "delivery_retry_attempts": 3
    }
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
          "permissions": ["generate_briefings", "configure_system", "manage_users", "view_all_data"]
        },
        {
          "name": "executive",
          "permissions": ["view_executive_briefings", "view_company_data"]
        },
        {
          "name": "manager",
          "permissions": ["view_department_briefings", "view_own_department_data"]
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
      "briefing_documents": "7_years",
      "raw_data": "5_years",
      "logs": "2_years",
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
    "visualization": {
      "max_points_per_chart": 1000,
      "chart_rendering_timeout_seconds": 60,
      "caching_enabled": true,
      "cache_duration_minutes": 60
    },
    "report_generation": {
      "max_report_size_mb": 10,
      "generation_timeout_minutes": 15,
      "parallel_generation": true,
      "max_parallel_reports": 5
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
    "template_cache": {
      "enabled": true,
      "ttl_minutes": 1440,  # 24 hours
      "max_templates": 50
    },
    "chart_cache": {
      "enabled": true,
      "ttl_minutes": 120,
      "max_charts": 100,
      "storage_path": "/tmp/chart_cache/"
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
      "data_source_connectivity": true,
      "briefing_generation_success": true,
      "delivery_success_rate": true,
      "system_resources": true
    },
    "metrics_collection": {
      "enabled": true,
      "collection_interval_minutes": 5,
      "metrics": [
        "data_collection_time",
        "processing_time",
        "generation_time",
        "delivery_time",
        "error_rate",
        "successful_deliveries"
      ]
    },
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/briefing_generator.log",
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
        "name": "briefing_generation_failure",
        "condition": "generation_failure_rate > 0.05",
        "severity": "critical",
        "recipients": ["admin@example.com", "ceo@example.com"],
        "notification_method": ["email", "slack"]
      },
      {
        "name": "delivery_failure",
        "condition": "delivery_failure_rate > 0.1",
        "severity": "medium",
        "recipients": ["admin@example.com"],
        "notification_method": "email"
      }
    ],
    "notification_channels": {
      "email": {
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "sender_email": "alerts@acme.com",
        "recipients": ["admin@example.com"]
      },
      "slack": {
        "webhook_url_env_var": "SLACK_WEBHOOK_URL",
        "channel": "#briefing-alerts"
      }
    }
  }
}
```

## Sample Configuration File

Create a `briefing_config.json` file with your configuration:

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
      "id": "finance_db",
      "name": "Financial Database",
      "type": "database",
      "connection": {
        "driver": "postgresql",
        "host": "finance-db.internal",
        "port": 5432,
        "database": "financials",
        "username_env_var": "FINANCE_DB_USER",
        "password_env_var": "FINANCE_DB_PASS"
      },
      "queries": [
        {
          "name": "weekly_revenue",
          "sql": "SELECT SUM(amount) as revenue FROM transactions WHERE transaction_date BETWEEN :start_date AND :end_date",
          "parameters": {
            "start_date": "{{last_week_start}}",
            "end_date": "{{last_week_end}}"
          }
        }
      ],
      "schedule": {
        "frequency": "daily",
        "time": "02:00",
        "timezone": "America/New_York"
      }
    }
  ],
  "templates": {
    "ceo_briefing": {
      "name": "CEO Weekly Briefing",
      "description": "Comprehensive briefing for CEO with all key metrics",
      "sections": [
        {
          "name": "executive_summary",
          "title": "Executive Summary",
          "order": 1,
          "required": true,
          "components": ["kpi_summary", "highlight_metrics"]
        }
      ]
    }
  },
  "distribution": {
    "recipients": [
      {
        "id": "ceo_001",
        "name": "CEO",
        "email": "ceo@acme.com",
        "template": "ceo_briefing",
        "delivery_method": "email",
        "delivery_schedule": "weekly",
        "delivery_day": "monday",
        "delivery_time": "08:00",
        "timezone": "America/New_York"
      }
    ]
  },
  "scheduling": {
    "generation_schedule": {
      "frequency": "weekly",
      "day_of_week": "sunday",
      "time": "23:00",
      "timezone": "UTC"
    }
  }
}
```