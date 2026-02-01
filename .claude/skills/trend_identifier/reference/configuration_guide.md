# Trend Identifier Configuration Guide

## Overview
This guide provides comprehensive configuration instructions for the Trend Identifier skill, which identifies patterns in business metrics, customer interactions, and market dynamics to uncover emerging trends and opportunities.

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
  - statsmodels (for time series analysis)
  - sqlalchemy (for database connections)
  - requests (for API calls)
  - tensorflow or pytorch (for neural networks)
  - ta-lib (for technical analysis indicators)

### Environment Variables
Set these environment variables for secure configuration:

```
TREND_IDENTIFIER_DB_PATH=/path/to/trend_data.db
TREND_IDENTIFIER_LOG_LEVEL=INFO
TREND_IDENTIFIER_CONFIG_PATH=/path/to/trend_config.json
TREND_IDENTIFIER_OUTPUT_PATH=/path/to/trend_reports/
TREND_IDENTIFIER_ALERT_EMAIL=admin@example.com
TREND_IDENTIFIER_COMPANY_NAME="Acme Corporation"
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
      "type": "api|database|file|streaming",
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
        "frequency": "minute|hourly|daily|weekly",
        "interval": 1,
        "timezone": "UTC"
      },
      "metrics": [
        {
          "name": "revenue",
          "type": "numeric",
          "unit": "dollars",
          "description": "Revenue metric for trend analysis"
        }
      ],
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
          "endpoint": "/sales",
          "method": "GET",
          "params": {
            "start_date": "{{last_month_start}}",
            "end_date": "{{last_month_end}}"
          },
          "rate_limit": {
            "requests_per_minute": 100
          },
          "metrics_extraction": [
            {
              "source_field": "revenue",
              "metric_name": "revenue",
              "metric_type": "numeric",
              "unit": "dollars"
            },
            {
              "source_field": "deal_count",
              "metric_name": "deal_count",
              "metric_type": "numeric",
              "unit": "count"
            }
          ]
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
          "name": "customer_engagement",
          "sql": "SELECT date, engagement_score FROM customer_metrics WHERE date BETWEEN :start_date AND :end_date ORDER BY date",
          "parameters": {
            "start_date": "{{last_month_start}}",
            "end_date": "{{last_month_end}}"
          },
          "metrics_mapping": {
            "engagement_score": "customer_engagement"
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
      "id": "market_data",
      "name": "Market Data File",
      "type": "file",
      "connection": {
        "file_path": "/data/market_data.csv",
        "date_column": "date",
        "delimiter": ",",
        "encoding": "utf-8"
      },
      "schedule": {
        "frequency": "daily",
        "time": "01:00",
        "timezone": "America/New_York"
      }
    }
  ]
}
```

## Trend Detection Configuration

### Trend Detection Algorithms
```json
{
  "trend_detection_algorithms": {
    "statistical_methods": {
      "enabled": true,
      "methods": [
        {
          "name": "linear_regression",
          "enabled": true,
          "min_data_points": 10,
          "confidence_level": 0.95,
          "weight": 0.2
        },
        {
          "name": "moving_average",
          "enabled": true,
          "window_sizes": [7, 14, 30],
          "weight": 0.2
        },
        {
          "name": "exponential_smoothing",
          "enabled": true,
          "smoothing_factor": 0.3,
          "weight": 0.2
        },
        {
          "name": "seasonal_decomposition",
          "enabled": true,
          "period": 7,  // Weekly seasonality
          "weight": 0.1
        }
      ]
    },
    "machine_learning_methods": {
      "enabled": true,
      "methods": [
        {
          "name": "neural_network",
          "enabled": true,
          "architecture": "lstm",
          "sequence_length": 30,
          "hidden_units": 50,
          "epochs": 100,
          "weight": 0.2
        },
        {
          "name": "random_forest",
          "enabled": true,
          "n_estimators": 100,
          "max_depth": 10,
          "weight": 0.1
        }
      ]
    },
    "signal_processing_methods": {
      "enabled": true,
      "methods": [
        {
          "name": "fourier_transform",
          "enabled": true,
          "min_frequency": 0.01,
          "max_frequency": 0.5,
          "weight": 0.1
        },
        {
          "name": "wavelet_analysis",
          "enabled": true,
          "wavelet_type": "db4",
          "decomposition_levels": 4,
          "weight": 0.1
        }
      ]
    }
  }
}
```

### Trend Classification Settings
```json
{
  "trend_classification": {
    "trend_types": {
      "upward": {
        "slope_threshold": 0.01,  // Minimum positive slope
        "strength_threshold": 0.5,  // Correlation coefficient for strong trend
        "validation_window": 7  // Days to validate trend
      },
      "downward": {
        "slope_threshold": -0.01,  // Maximum negative slope
        "strength_threshold": -0.5,  // Correlation coefficient for strong trend
        "validation_window": 7  // Days to validate trend
      },
      "horizontal": {
        "slope_range": [-0.005, 0.005],  // Slope range for horizontal trend
        "strength_threshold": 0.3  // Correlation coefficient for weak trend
      }
    },
    "trend_durations": {
      "short_term": {
        "min_duration": 3,
        "max_duration": 30,
        "unit": "days"
      },
      "medium_term": {
        "min_duration": 31,
        "max_duration": 180,
        "unit": "days"
      },
      "long_term": {
        "min_duration": 181,
        "max_duration": 730,
        "unit": "days"
      }
    },
    "trend_strength": {
      "strong": {
        "min_correlation": 0.7,
        "min_confidence": 0.8
      },
      "moderate": {
        "min_correlation": 0.4,
        "max_correlation": 0.69,
        "min_confidence": 0.6
      },
      "weak": {
        "min_correlation": 0.1,
        "max_correlation": 0.39,
        "min_confidence": 0.4
      }
    }
  }
}
```

### Time Series Analysis Configuration
```json
{
  "time_series_analysis": {
    "stationarity_tests": {
      "adfuller": {
        "enabled": true,
        "significance_level": 0.05
      },
      "kpss": {
        "enabled": true,
        "significance_level": 0.05
      }
    },
    "seasonal_decomposition": {
      "enabled": true,
      "model": "multiplicative",  // additive or multiplicative
      "period": 7  // Default period for weekly seasonality
    },
    "arima_modeling": {
      "enabled": true,
      "max_p": 5,
      "max_d": 2,
      "max_q": 5,
      "information_criterion": "aic"  // aic, bic, or aicc
    },
    "forecasting": {
      "enabled": true,
      "horizon": 30,  // Days to forecast
      "confidence_intervals": true,
      "confidence_level": 0.95
    }
  }
}
```

## Pattern Recognition Configuration

### Pattern Detection Settings
```json
{
  "pattern_recognition": {
    "shape_detection": {
      "enabled": true,
      "patterns": [
        {
          "name": "v_shape",
          "definition": "decreasing followed by increasing",
          "minimum_depth": 0.1,  // Minimum change in percentage
          "maximum_width": 30,   // Maximum days for pattern
          "minimum_correlation": 0.8
        },
        {
          "name": "u_shape",
          "definition": "gradual decrease then gradual increase",
          "minimum_depth": 0.05,
          "maximum_width": 60,
          "minimum_correlation": 0.7
        },
        {
          "name": "sigmoid",
          "definition": "s-curve pattern",
          "minimum_correlation": 0.8
        }
      ]
    },
    "change_point_detection": {
      "enabled": true,
      "method": "binary_segmentation",  // binary_segmentation, pelt, or window
      "penalty": 10,  // Penalty for adding change points
      "min_segment_length": 5  // Minimum points in each segment
    },
    "anomaly_detection": {
      "enabled": true,
      "methods": [
        {
          "name": "isolation_forest",
          "contamination": 0.1,
          "n_estimators": 100
        },
        {
          "name": "z_score",
          "threshold": 3,
          "window_size": 30
        },
        {
          "name": "iqr_method",
          "factor": 1.5,
          "window_size": 30
        }
      ]
    }
  }
}
```

### Correlation Analysis Settings
```json
{
  "correlation_analysis": {
    "cross_correlation": {
      "enabled": true,
      "max_lag": 30,  // Maximum lag to test
      "significance_level": 0.05
    },
    "partial_correlation": {
      "enabled": true,
      "control_variables": ["seasonality", "trend"]
    },
    "mutual_information": {
      "enabled": true,
      "n_neighbors": 3
    }
  }
}
```

## Trend Validation Configuration

### Statistical Validation
```json
{
  "statistical_validation": {
    "confidence_intervals": {
      "enabled": true,
      "method": "bootstrap",  // bootstrap, t-distribution, or normal
      "confidence_level": 0.95,
      "n_iterations": 1000
    },
    "hypothesis_testing": {
      "trend_significance": {
        "test": "t_test_slope",
        "significance_level": 0.05,
        "alternative": "two-sided"  // two-sided, greater, or less
      }
    },
    "cross_validation": {
      "method": "time_series_split",
      "n_splits": 5,
      "test_size": 0.2
    }
  }
}
```

### Business Validation
```json
{
  "business_validation": {
    "domain_expert_review": {
      "enabled": true,
      "experts": ["expert1@example.com", "expert2@example.com"],
      "review_threshold": 0.8  // Trends with confidence above this get expert review
    },
    "historical_precedence": {
      "enabled": true,
      "comparison_window": 365,  // Compare with similar patterns in last year
      "similarity_threshold": 0.7
    },
    "logical_consistency": {
      "enabled": true,
      "checks": [
        {
          "name": "non_negative",
          "metric_patterns": ["revenue", "count"],
          "enabled": true
        },
        {
          "name": "bounded",
          "metric_patterns": ["percentage", "ratio"],
          "bounds": [0, 1],
          "enabled": true
        }
      ]
    }
  }
}
```

## Trend Forecasting Configuration

### Forecasting Parameters
```json
{
  "forecasting": {
    "short_term": {
      "horizon": 7,  // 1 week
      "methods": [
        {
          "name": "exponential_smoothing",
          "enabled": true,
          "smoothing_level": 0.3,
          "smoothing_trend": 0.1,
          "smoothing_seasonal": 0.1
        },
        {
          "name": "arima",
          "enabled": true,
          "order": [1, 1, 1]
        }
      ],
      "confidence_level": 0.90
    },
    "medium_term": {
      "horizon": 30,  // 1 month
      "methods": [
        {
          "name": "sarima",
          "enabled": true,
          "order": [1, 1, 1],
          "seasonal_order": [1, 1, 1, 7]
        },
        {
          "name": "neural_network",
          "enabled": true,
          "architecture": "lstm",
          "sequence_length": 30,
          "hidden_units": 50
        }
      ],
      "confidence_level": 0.95
    },
    "long_term": {
      "horizon": 90,  // 3 months
      "methods": [
        {
          "name": "prophet",
          "enabled": true,
          "seasonality_mode": "multiplicative",
          "changepoint_prior_scale": 0.05
        },
        {
          "name": "ensemble",
          "enabled": true,
          "base_models": ["arima", "exponential_smoothing", "neural_network"],
          "meta_model": "random_forest"
        }
      ],
      "confidence_level": 0.98
    }
  }
}
```

## Alert Configuration

### Alert Thresholds and Triggers
```json
{
  "alerts": {
    "trend_emergence": {
      "enabled": true,
      "conditions": [
        {
          "metric": "any",
          "condition": "trend_strength >= strong AND confidence >= 0.8",
          "severity": "high",
          "recipients": ["trend_analyst@example.com", "manager@example.com"]
        }
      ]
    },
    "trend_acceleration": {
      "enabled": true,
      "conditions": [
        {
          "metric": "revenue",
          "condition": "slope_difference > 0.05 AND trend_direction == upward",
          "severity": "medium",
          "recipients": ["finance@example.com"]
        },
        {
          "metric": "customer_satisfaction",
          "condition": "slope_difference < -0.05 AND trend_direction == downward",
          "severity": "high",
          "recipients": ["cxo@example.com"]
        }
      ]
    },
    "trend_reversal": {
      "enabled": true,
      "conditions": [
        {
          "metric": "any",
          "condition": "previous_trend_direction != current_trend_direction AND confidence >= 0.7",
          "severity": "high",
          "recipients": ["strategy@example.com"]
        }
      ]
    },
    "anomaly_detection": {
      "enabled": true,
      "conditions": [
        {
          "metric": "any",
          "condition": "anomaly_score > threshold",
          "severity": "medium",
          "recipients": ["analyst@example.com"]
        }
      ]
    }
  },
  "notification_channels": {
    "email": {
      "smtp_server": "smtp.example.com",
      "smtp_port": 587,
      "username_env_var": "SMTP_USERNAME",
      "password_env_var": "SMTP_PASSWORD",
      "sender_email": "trends@acme.com"
    },
    "slack": {
      "webhook_url_env_var": "SLACK_WEBHOOK_URL",
      "channel": "#trend-alerts"
    },
    "dashboard": {
      "enabled": true,
      "url": "https://dashboard.acme.com/trend-alerts"
    }
  }
}
```

## Visualization Configuration

### Chart and Visualization Settings
```json
{
  "visualizations": {
    "chart_types": {
      "time_series": {
        "library": "plotly",
        "default_color": "#1f77b4",
        "width": 1000,
        "height": 600,
        "show_confidence_intervals": true,
        "show_trend_lines": true
      },
      "heat_map": {
        "library": "seaborn",
        "colormap": "RdYlGn",
        "width": 800,
        "height": 600
      },
      "scatter_plot": {
        "library": "matplotlib",
        "default_color": "#ff7f0e",
        "width": 800,
        "height": 600,
        "show_correlation_line": true
      }
    },
    "interactive_features": {
      "zoom_enabled": true,
      "pan_enabled": true,
      "tooltip_enabled": true,
      "annotation_enabled": true,
      "export_formats": ["png", "svg", "pdf"]
    },
    "dashboard_settings": {
      "refresh_interval_seconds": 300,
      "auto_refresh": true,
      "responsive_design": true
    }
  }
}
```

### Report Generation Settings
```json
{
  "reports": {
    "executive_summary": {
      "enabled": true,
      "sections": [
        {
          "name": "top_trends",
          "title": "Top 5 Identified Trends",
          "count": 5,
          "include_visualization": true
        },
        {
          "name": "significant_changes",
          "title": "Recent Significant Changes",
          "timeframe": "last_7_days",
          "include_visualization": true
        },
        {
          "name": "predictions",
          "title": "Upcoming Trend Predictions",
          "horizon": 30,
          "include_visualization": true
        }
      ],
      "schedule": {
        "frequency": "daily",
        "time": "08:00",
        "timezone": "America/New_York"
      }
    },
    "detailed_analysis": {
      "enabled": true,
      "sections": [
        {
          "name": "metric_breakdown",
          "title": "Trend Analysis by Metric",
          "include_statistics": true,
          "include_visualization": true
        },
        {
          "name": "pattern_analysis",
          "title": "Pattern Recognition Results",
          "include_examples": true
        },
        {
          "name": "forecasting_results",
          "title": "Forecasting Model Results",
          "include_accuracy_metrics": true
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

## Integration Configuration

### Business System Integrations
```json
{
  "integrations": {
    "crm_systems": [
      {
        "name": "salesforce",
        "enabled": true,
        "connection": {
          "instance_url": "https://acme.my.salesforce.com",
          "api_key_env_var": "SF_API_KEY"
        },
        "objects": ["Opportunity", "Account", "Contact"],
        "trend_fields": [
          {
            "sf_field": "Amount",
            "trend_metric": "revenue"
          },
          {
            "sf_field": "CloseDate",
            "trend_metric": "closing_trend"
          }
        ]
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
        "metrics": ["sessions", "users", "bounceRate", "engagementRate"],
        "dimensions": ["date", "deviceCategory", "country"]
      }
    ],
    "financial_systems": [
      {
        "name": "quickbooks",
        "enabled": true,
        "connection": {
          "company_id": "QB_COMPANY_ID",
          "api_key_env_var": "QB_API_KEY"
        },
        "entities": ["invoices", "payments", "customers"],
        "trend_metrics": ["revenue", "collections", "ar_aging"]
      }
    ]
  }
}
```

### External Data Integrations
```json
{
  "external_data": {
    "market_research": [
      {
        "name": "industry_reports",
        "enabled": true,
        "provider": "ibisworld",
        "api_key_env_var": "IBISWORLD_API_KEY",
        "categories": ["technology", "finance", "healthcare"]
      }
    ],
    "economic_indicators": [
      {
        "name": "fred_economic_data",
        "enabled": true,
        "api_key_env_var": "FRED_API_KEY",
        "indicators": ["GDP", "unemployment_rate", "consumer_price_index"]
      }
    ],
    "social_media": [
      {
        "name":": "twitter_api",
        "enabled": true,
        "api_key_env_var": "TWITTER_API_KEY",
        "secret_env_var": "TWITTER_API_SECRET",
        "keywords": ["acme_corporation", "acme_brand"]
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
          "permissions": ["run_analysis", "view_reports", "create_dashboards", "view_trends"]
        },
        {
          "name": "viewer",
          "permissions": ["view_reports", "view_dashboards", "view_public_trends"]
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
      "trend_data": "2_years",
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
      "memory_limit_mb": 4096,
      "processing_timeout_minutes": 60
    },
    "algorithm_performance": {
      "trend_detection_timeout_minutes": 30,
      "forecasting_timeout_minutes": 15,
      "pattern_recognition_timeout_minutes": 20
    },
    "caching": {
      "results_cache_enabled": true,
      "results_cache_ttl_minutes": 120,
      "model_cache_enabled": true,
      "model_cache_ttl_hours": 24
    }
  }
}
```

### Model Optimization
```json
{
  "model_optimization": {
    "hyperparameter_tuning": {
      "enabled": true,
      "method": "bayesian_optimization",
      "n_trials": 50,
      "cv_folds": 5
    },
    "feature_selection": {
      "enabled": true,
      "method": "recursive_elimination",
      "estimator": "random_forest",
      "cv_folds": 5
    },
    "ensemble_methods": {
      "enabled": true,
      "method": "stacking",
      "base_models": ["linear_regression", "random_forest", "svm"],
      "meta_model": "logistic_regression"
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
    "trend_detection_schedule": {
      "frequency": "hourly",
      "time": "00:30",  // 30 minutes past each hour
      "timezone": "UTC",
      "timeout_minutes": 60
    },
    "report_generation_schedule": {
      "executive_summary": {
        "frequency": "daily",
        "time": "08:00",
        "timezone": "America/New_York"
      },
      "detailed_analysis": {
        "frequency": "weekly",
        "day": "monday",
        "time": "09:00",
        "timezone": "America/New_York"
      }
    },
    "model_retraining_schedule": {
      "frequency": "weekly",
      "day": "sunday",
      "time": "02:00",
      "timezone": "UTC"
    },
    "maintenance_schedule": {
      "cleanup_task": {
        "frequency": "daily",
        "time": "03:00",
        "timezone": "UTC"
      },
      "backup_task": {
        "frequency": "daily",
        "time": "04:00",
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
      "trend_detection_engine_health": true,
      "report_generation_success": true,
      "system_resources": true,
      "integration_connectivity": true
    },
    "metrics_collection": {
      "enabled": true,
      "collection_interval_minutes": 5,
      "metrics": [
        "data_collection_time",
        "trend_detection_time",
        "report_generation_time",
        "error_rate",
        "successful_detections",
        "active_connections",
        "model_accuracy"
      ]
    },
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/trend_identifier.log",
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
  "system_alerts": {
    "alert_triggers": [
      {
        "name": "data_collection_failure",
        "condition": "data_collection_error_rate > 0.1",
        "severity": "high",
        "recipients": ["admin@example.com"],
        "notification_method": "email"
      },
      {
        "name": "trend_detection_failure",
        "condition": "detection_failure_rate > 0.05",
        "severity": "critical",
        "recipients": ["admin@example.com", "ops@example.com"],
        "notification_method": ["email", "slack"]
      },
      {
        "name": "high_trend_significance",
        "condition": "trend_strength >= strong AND confidence >= 0.9",
        "severity": "info",
        "recipients": ["strategy@example.com"],
        "notification_method": "email"
      }
    ]
  }
}
```

## Sample Configuration File

Create a `trend_config.json` file with your configuration:

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
      "id": "sales_db",
      "name": "Sales Database",
      "type": "database",
      "connection": {
        "driver": "postgresql",
        "host": "sales-db.internal",
        "port": 5432,
        "database": "sales_data",
        "username_env_var": "SALES_DB_USER",
        "password_env_var": "SALES_DB_PASS"
      },
      "queries": [
        {
          "name": "daily_revenue",
          "sql": "SELECT date, revenue FROM daily_revenue WHERE date BETWEEN :start_date AND :end_date ORDER BY date",
          "parameters": {
            "start_date": "{{last_month_start}}",
            "end_date": "{{last_month_end}}"
          },
          "metrics_mapping": {
            "revenue": "revenue"
          }
        }
      ],
      "schedule": {
        "frequency": "daily",
        "time": "01:00",
        "timezone": "UTC"
      }
    }
  ],
  "trend_detection_algorithms": {
    "statistical_methods": {
      "enabled": true,
      "methods": [
        {
          "name": "linear_regression",
          "enabled": true,
          "min_data_points": 10,
          "confidence_level": 0.95,
          "weight": 0.3
        },
        {
          "name": "moving_average",
          "enabled": true,
          "window_sizes": [7, 14],
          "weight": 0.3
        }
      ]
    }
  },
  "trend_classification": {
    "trend_types": {
      "upward": {
        "slope_threshold": 0.01,
        "strength_threshold": 0.5,
        "validation_window": 7
      }
    }
  },
  "scheduling": {
    "data_collection_schedule": {
      "frequency": "daily",
      "time": "01:00",
      "timezone": "UTC"
    },
    "trend_detection_schedule": {
      "frequency": "daily",
      "time": "02:00",
      "timezone": "UTC"
    }
  }
}
```