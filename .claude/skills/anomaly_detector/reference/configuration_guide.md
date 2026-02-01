# Anomaly Detector Configuration Guide

## Overview
This document provides comprehensive configuration options for the Anomaly Detector skill, covering detection algorithms, data sources, thresholds, and integration settings.

## Global Configuration

### Main Configuration File Structure
```yaml
anomaly_detector:
  # Service settings
  server:
    enabled: true
    host: "localhost"
    port: 8081
    ssl_enabled: false
    max_connections: 100

  # Processing settings
  processing:
    batch_size: 1000
    batch_interval: 30000  # milliseconds
    max_workers: 8
    queue_size: 5000
    timeout: 60000  # milliseconds

  # Storage settings
  storage:
    type: "sqlite"  # sqlite, postgresql, mongodb
    path: "./anomalies.db"
    retention_days: 90
    backup_enabled: true
    backup_schedule: "0 3 * * *"  # Daily at 3 AM

  # Model settings
  models:
    isolation_forest:
      enabled: true
      contamination: 0.1
      max_samples: 256
      max_features: 1.0
      bootstrap: false

    z_score:
      enabled: true
      threshold: 3.0
      use_modified_z_score: false
      mad_threshold: 3.5

    lof:
      enabled: true
      n_neighbors: 20
      algorithm: "auto"  # auto, ball_tree, kd_tree, brute
      leaf_size: 30
      metric: "minkowski"
      p: 2
      novelty: true

    time_series:
      enabled: true
      method: "seasonal_decomposition"
      seasonal_period: 7  # days for weekly seasonality
      alpha: 0.05  # significance level

  # Security settings
  security:
    enable_authentication: true
    enable_encryption: true
    audit_logging: true
    rate_limiting:
      requests_per_minute: 100
      burst_size: 200
```

## Data Source Configuration

### Financial Data Sources
```yaml
data_sources:
  financial:
    enabled: true
    providers:
      - type: "database"
        name: "transactions_db"
        connection_string: "postgresql://user:pass@localhost/finance"
        query: |
          SELECT
            transaction_id,
            amount,
            account_id,
            transaction_date,
            merchant_category,
            currency
          FROM transactions
          WHERE transaction_date > NOW() - INTERVAL '30 days'
        schedule: "*/15 * * * *"  # Every 15 minutes

      - type: "api"
        name: "banking_api"
        base_url: "https://api.bank.com"
        auth:
          type: "oauth2"
          client_id: "your_client_id"
          client_secret_env_var: "BANKING_API_SECRET"
        endpoints:
          - path: "/accounts/{account_id}/transactions"
            method: "GET"
            params:
              limit: 1000
              sort: "desc"
        schedule: "*/30 * * * *"  # Every 30 minutes

      - type: "file"
        name: "daily_reports"
        path: "/path/to/daily/finance/reports/"
        pattern: "finance_daily_*.csv"
        schedule: "0 2 * * *"  # Daily at 2 AM
```

### System Metrics Sources
```yaml
data_sources:
  system_metrics:
    enabled: true
    providers:
      - type: "prometheus"
        name: "infrastructure_monitoring"
        url: "http://prometheus:9090"
        queries:
          cpu_usage: |
            avg by(instance) (
              100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
            )
          memory_usage: |
            (node_memory_MemTotal_bytes - node_memory_MemFree_bytes) / node_memory_MemTotal_bytes * 100
          disk_io: |
            irate(node_disk_io_time_seconds_total[5m])
          network_traffic: |
            sum by(instance) (irate(node_network_receive_bytes_total[5m]))
        schedule: "*/5 * * * *"  # Every 5 minutes

      - type: "log_files"
        name: "system_logs"
        paths:
          - "/var/log/application.log"
          - "/var/log/system.log"
        patterns:
          error_pattern: "ERROR|FATAL|EXCEPTION"
          warning_pattern: "WARNING|WARN"
        schedule: "*/1 * * * *"  # Every minute

      - type: "api"
        name: "cloud_monitoring"
        base_url: "https://monitoring.googleapis.com"
        auth:
          type: "service_account"
          key_file: "/path/to/service-account-key.json"
        endpoints:
          - path: "/v3/projects/{project_id}/timeSeries"
            method: "GET"
            params:
              filter: "metric.type=\"compute.googleapis.com/instance/cpu/utilization\""
              interval_endTime: "now"
              interval_startTime: "now-1h"
        schedule: "*/10 * * * *"  # Every 10 minutes
```

### Business Operations Sources
```yaml
data_sources:
  business_operations:
    enabled: true
    providers:
      - type: "crm_system"
        name: "salesforce"
        instance_url: "https://your-org.salesforce.com"
        auth:
          type: "oauth2"
          client_id: "your_connected_app_id"
          client_secret_env_var: "SALESFORCE_CLIENT_SECRET"
          refresh_token_env_var: "SALESFORCE_REFRESH_TOKEN"
        objects:
          - name: "Opportunity"
            fields: ["Amount", "CloseDate", "StageName", "Probability"]
            where: "LastModifiedDate > YESTERDAY"
        schedule: "*/15 * * * *"  # Every 15 minutes

      - type: "hr_system"
        name: "workday"
        tenant: "your-tenant"
        auth:
          type: "oauth2"
          client_id: "your_client_id"
          client_secret_env_var: "WORKDAY_CLIENT_SECRET"
        endpoints:
          - path: "/ccx/service/customreport2/your-tenant/employee-activity-report"
            method: "GET"
        schedule: "0 6 * * 1-5"  # Weekdays at 6 AM

      - type: "inventory_system"
        name: "erp_system"
        base_url: "https://erp.company.com/api"
        auth:
          type: "basic"
          username: "api_user"
          password_env_var: "ERP_API_PASSWORD"
        endpoints:
          - path: "/inventory/levels"
            method: "GET"
            params:
              include_zero_stock: true
        schedule: "0 */6 * * *"  # Every 6 hours
```

## Detection Algorithm Configuration

### Statistical Detection
```yaml
detection_algorithms:
  statistical:
    z_score:
      enabled: true
      threshold: 3.0
      min_sample_size: 30
      use_modified_z_score: false
      mad_threshold: 3.5
      fields_to_monitor:
        - name: "transaction_amount"
          threshold: 4.0  # Higher threshold for transaction amounts
          baseline_period: "30d"  # 30 days baseline
        - name: "cpu_usage_percent"
          threshold: 2.5  # Lower threshold for system metrics
          baseline_period: "7d"   # 7 days baseline
        - name: "response_time_ms"
          threshold: 3.0
          baseline_period: "14d"  # 14 days baseline

    grubbs_test:
      enabled: true
      significance_level: 0.05
      iterations: 1
      min_sample_size: 5
      fields_to_monitor:
        - name: "monthly_sales"
          significance_level: 0.01  # Stricter for business metrics
          min_sample_size: 10

    iqr_method:
      enabled: true
      multiplier: 1.5
      fields_to_monitor:
        - name: "daily_active_users"
          multiplier: 2.0  # More lenient for user metrics
        - name: "api_request_rate"
          multiplier: 1.5
```

### Machine Learning Detection
```yaml
detection_algorithms:
  machine_learning:
    isolation_forest:
      enabled: true
      contamination: 0.1
      max_samples: 256
      max_features: 1.0
      bootstrap: false
      n_estimators: 100
      max_depth: 10
      fields_to_monitor:
        - name: "financial_transactions"
          contamination: 0.05  # Stricter for financial data
          max_samples: 0.8
          n_estimators: 200
        - name: "system_metrics"
          contamination: 0.15  # More lenient for system metrics
          max_samples: 256

    local_outlier_factor:
      enabled: true
      n_neighbors: 20
      algorithm: "auto"
      leaf_size: 30
      metric: "minkowski"
      p: 2
      novelty: true
      fields_to_monitor:
        - name: "user_behavior"
          n_neighbors: 50  # More neighbors for behavior analysis
          novelty: true
        - name: "network_traffic"
          n_neighbors: 15
          novelty: true

    one_class_svm:
      enabled: true
      kernel: "rbf"
      degree: 3
      gamma: "scale"  # scale, auto, or float
      nu: 0.1
      cache_size: 200  # MB
      fields_to_monitor:
        - name: "access_patterns"
          nu: 0.05  # Stricter for security-related patterns
          gamma: "scale"
```

### Time Series Detection
```yaml
detection_algorithms:
  time_series:
    seasonal_decomposition:
      enabled: true
      model: "additive"  # additive or multiplicative
      seasonal_period: 7  # days for weekly seasonality
      anomaly_threshold: 2.0  # standard deviations
      fields_to_monitor:
        - name: "daily_sales"
          seasonal_period: 7
          anomaly_threshold: 1.5  # More sensitive for business metrics
        - name: "website_traffic"
          seasonal_period: 7
          anomaly_threshold: 2.0
        - name: "hourly_logins"
          seasonal_period: 24  # Hourly seasonality
          anomaly_threshold: 1.8

    arima:
      enabled: true
      order: [1, 1, 1]  # (p, d, q) parameters
      seasonal_order: [1, 1, 1, 7]  # (P, D, Q, s) parameters
      fields_to_monitor:
        - name: "revenue_forecast"
          order: [2, 1, 2]
          seasonal_order: [1, 1, 1, 12]  # Monthly seasonality
        - name: "inventory_demand"
          order: [1, 1, 1]
          seasonal_order: [1, 1, 1, 4]  # Quarterly seasonality

    changepoint_detection:
      enabled: true
      method: "bayesian"  # bayesian, windowed, or regression
      window_size: 10
      threshold: 0.01
      fields_to_monitor:
        - name: "performance_metrics"
          window_size: 7
          threshold: 0.05
        - name: "error_rates"
          window_size: 5
          threshold: 0.01
```

## Business Rules Configuration

### Custom Business Rules
```yaml
business_rules:
  enabled: true
  rules:
    - name: "suspicious_transaction"
      description: "Detect unusually large transactions"
      conditions:
        - field: "amount"
          operator: ">"
          value: 10000
          compared_to: "historical_average * 5"
        - field: "merchant_category"
          operator: "in"
          value: ["gambling", "adult", "foreign_exchange"]
      severity: "high"
      action: "flag_for_review"

    - name: "unusual_activity_hours"
      description: "Detect system access during unusual hours"
      conditions:
        - field: "hour_of_day"
          operator: "not_in_range"
          value: [8, 18]  # Business hours
        - field: "day_of_week"
          operator: "not_in"
          value: [1, 2, 3, 4, 5]  # Not weekdays
      severity: "medium"
      action: "log_warning"

    - name: "inventory_discrepancy"
      description: "Detect significant differences between recorded and expected inventory"
      conditions:
        - field: "actual_vs_expected_diff"
          operator: ">"
          value: 0.1  # 10% difference
      severity: "high"
      action: "create_work_order"

    - name: "performance_degradation"
      description: "Detect significant performance degradation"
      conditions:
        - field: "response_time_percentile_95th"
          operator: ">"
          value: 2000  # 2 seconds
          compared_to: "historical_baseline * 1.5"
      severity: "medium"
      action: "scale_resources"

  compound_rules:
    - name: "potential_security_breach"
      description: "Multiple indicators suggesting security breach"
      conditions:
        - rule_ref: "unusual_activity_hours"
        - field: "failed_login_attempts"
          operator: ">"
          value: 10
          within_timeframe: "1h"
        - field: "data_export_volume"
          operator: ">"
          value: 100000000  # 100MB
          within_timeframe: "1h"
      severity: "critical"
      action: "lock_account_and_notify"
```

## Alerting and Notification Configuration

### Alert Thresholds
```yaml
alerts:
  thresholds:
    # Severity-based thresholds
    critical:
      min_confidence: 0.95
      min_magnitude: 3.0
      persistence_periods: 1
      notification_immediate: true

    high:
      min_confidence: 0.80
      min_magnitude: 2.0
      persistence_periods: 2
      notification_delay: 5  # minutes

    medium:
      min_confidence: 0.60
      min_magnitude: 1.5
      persistence_periods: 3
      notification_delay: 15  # minutes

    low:
      min_confidence: 0.40
      min_magnitude: 1.0
      persistence_periods: 5
      notification_delay: 60  # minutes

  suppression:
    rules:
      - name: "similar_anomalies"
        description: "Suppress similar anomalies within time window"
        conditions:
          - field: "anomaly_type"
            operator: "="
            value: "$current.anomaly_type"
          - field: "entity_id"
            operator: "="
            value: "$current.entity_id"
        time_window: "30m"
        action: "suppress"

      - name: "maintenance_window"
        description: "Suppress alerts during maintenance"
        conditions:
          - field: "timestamp"
            operator: "in_range"
            value: ["2023-12-01T02:00:00Z", "2023-12-01T04:00:00Z"]
          - field: "severity"
            operator: "<="
            value: "medium"
        action: "suppress"
```

### Notification Channels
```yaml
notifications:
  channels:
    email:
      enabled: true
      smtp_server: "smtp.company.com"
      smtp_port: 587
      username: "anomaly-detector@company.com"
      password_env_var: "SMTP_PASSWORD"
      from_address: "Anomaly Detector <anomaly-detector@company.com>"
      recipients:
        critical: ["security@company.com", "cto@company.com"]
        high: ["ops-team@company.com", "manager@company.com"]
        medium: ["team-lead@company.com"]
        low: ["audit-log@company.com"]

    slack:
      enabled: true
      webhook_urls:
        critical: "https://hooks.slack.com/services/critical-anomalies-channel"
        high: "https://hooks.slack.com/services/alerts-channel"
        medium: "https://hooks.slack.com/services/general-notifications-channel"
      templates:
        critical: |
          :warning: *CRITICAL ANOMALY DETECTED*
          Type: {{ anomaly_type }}
          Entity: {{ entity_id }}
          Confidence: {{ confidence_score }}
          Magnitude: {{ magnitude }}
          Details: {{ description }}

    pagerduty:
      enabled: false
      integration_key_env_var: "PAGERDUTY_INTEGRATION_KEY"
      service_id: "your-service-id"
      escalation_policy: "critical-issues"

    webhook:
      enabled: true
      endpoints:
        - url: "https://internal-api.company.com/anomalies/webhook"
          headers:
            Authorization: "Bearer ${ANOMALY_WEBHOOK_TOKEN}"
            Content-Type: "application/json"
          timeout: 10000  # milliseconds
```

## Performance and Resource Configuration

### Resource Limits
```yaml
performance:
  limits:
    memory:
      max_heap_size: "4GB"
      gc_threshold: "80%"  # Percentage of heap before forced GC

    cpu:
      max_threads: 16
      thread_pool_size: 8
      cpu_quota: "80%"  # Maximum CPU usage percentage

    storage:
      max_database_size: "10GB"
      cleanup_threshold: "80%"  # Clean up when 80% full
      retention_policies:
        anomalies: "90d"
        alerts: "365d"
        logs: "30d"

  caching:
    enabled: true
    type: "redis"
    host: "localhost"
    port: 6379
    ttl: 3600  # 1 hour

    patterns:
      - key: "model_predictions"
        ttl: 900  # 15 minutes
      - key: "baseline_calculations"
        ttl: 7200  # 2 hours
      - key: "feature_cache"
        ttl: 1800  # 30 minutes

  rate_limits:
    data_ingestion: 10000  # per minute
    anomaly_detection: 5000  # per minute
    notifications: 100  # per minute
    api_requests: 1000  # per minute
```

## Model Management Configuration

### Model Training and Updates
```yaml
models:
  training:
    schedule: "0 2 * * 1"  # Weekly on Mondays at 2 AM
    baseline_period: "30d"  # Use 30 days of data for baseline
    retrain_threshold: 0.1  # Retrain if performance drops by 10%

    validation:
      split_ratio: 0.2  # 20% for validation
      metrics:
        - "precision"
        - "recall"
        - "f1_score"
        - "false_positive_rate"
      alert_thresholds:
        precision_drop: 0.05  # Alert if precision drops by 5%
        recall_drop: 0.10     # Alert if recall drops by 10%

  drift_detection:
    enabled: true
    method: "ks_test"  # Kolmogorov-Smirnov test
    threshold: 0.05
    check_interval: "1h"
    action: "retrain_model"

  ensemble:
    enabled: true
    voting_method: "weighted"  # majority, weighted, or probability
    weights:
      isolation_forest: 0.4
      z_score: 0.3
      lof: 0.2
      time_series: 0.1
    diversity_threshold: 0.5  # Minimum diversity between models
```

## Security Configuration

### Authentication and Authorization
```yaml
security:
  authentication:
    methods:
      - type: "oauth2"
        provider: "google"
        client_id: "your_client_id"
        client_secret_env_var: "GOOGLE_CLIENT_SECRET"

      - type: "api_key"
        header: "X-API-Key"
        keys:
          - id: "monitoring_system"
            secret_env_var: "MONITORING_API_KEY"
            permissions: ["read_anomalies", "acknowledge_alerts"]

          - id: "admin_user"
            secret_env_var: "ADMIN_API_KEY"
            permissions: ["read_anomalies", "acknowledge_alerts", "configure_rules", "manage_models"]

  authorization:
    roles:
      viewer:
        permissions: ["read_anomalies"]
      analyst:
        permissions: ["read_anomalies", "acknowledge_alerts", "view_reports"]
      administrator:
        permissions: ["read_anomalies", "acknowledge_alerts", "configure_rules", "manage_models", "view_reports"]
      auditor:
        permissions: ["read_anomalies", "view_reports", "export_data"]

    rbac_enabled: true
    default_role: "viewer"
```

### Data Privacy and Encryption
```yaml
privacy:
  encryption:
    at_rest: true
    algorithm: "AES-256-GCM"
    key_rotation_interval: "30d"
    key_storage:
      type: "hashicorp_vault"
      address: "https://vault.company.com"
      token_env_var: "VAULT_TOKEN"

  data_masking:
    enabled: true
    fields:
      - name: "account_number"
        mask_pattern: "XXXX-XXXX-####-####"
      - name: "ssn"
        mask_pattern: "XXX-XX-####"
      - name: "credit_card"
        mask_pattern: "****-****-****-####"

  pii_detection:
    enabled: true
    patterns:
      - name: "credit_card"
        regex: "\\b(?:4[0-9]{12}(?:[0-9]{3})?|[25][1-7][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13}|3[0-9]{14}|(?:2131|1800|35\\d{3})\\d{11})\\b"
        action: "mask_partially"

      - name: "email"
        regex: "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b"
        action: "mask_partially"

  retention:
    policies:
      critical_anomalies: "7y"    # 7 years
      high_anomalies: "2y"       # 2 years
      medium_anomalies: "1y"     # 1 year
      low_anomalies: "90d"       # 90 days
      default: "30d"             # 30 days
```

## Monitoring and Observability

### Internal Monitoring
```yaml
monitoring:
  metrics:
    enabled: true
    collection_interval: 30  # seconds
    backends:
      - type: "prometheus"
        endpoint: "/metrics"
      - type: "datadog"
        api_key_env_var: "DATADOG_API_KEY"

  internal_alerts:
    high_memory_usage:
      threshold: 80  # percent
      action: "trigger_gc"

    processing_backlog:
      threshold: 1000  # queued items
      action: "scale_up_workers"

    detection_accuracy_drop:
      threshold: 0.1  # 10% drop
      action: "alert_administrators"

  health_checks:
    endpoints:
      - name: "database_connection"
        type: "sql_ping"
        connection_string: "sqlite:///anomalies.db"
        timeout: 5

      - name: "model_availability"
        type: "prediction_test"
        model_name: "isolation_forest"
        test_data: [1.0, 2.0, 3.0]
        timeout: 10
```