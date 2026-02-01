# Notification Aggregator Configuration Guide

## Overview
This document provides comprehensive configuration options for the Notification Aggregator skill, covering source setup, filtering rules, delivery methods, and security settings.

## Global Configuration

### Main Configuration File Structure
```yaml
notification_aggregator:
  # Server settings
  server:
    host: "localhost"
    port: 8080
    ssl_enabled: false
    max_connections: 1000

  # Processing settings
  processing:
    batch_size: 100
    batch_interval: 5000  # milliseconds
    max_workers: 10
    queue_size: 10000

  # Storage settings
  storage:
    type: "sqlite"  # sqlite, postgresql, mongodb
    path: "./notifications.db"
    retention_days: 30
    backup_enabled: true
    backup_schedule: "0 2 * * *"  # Daily at 2 AM

  # Security settings
  security:
    enable_authentication: true
    enable_encryption: true
    audit_logging: true
    rate_limiting:
      requests_per_minute: 1000
      burst_size: 2000
```

## Notification Source Configuration

### Email Integration
```yaml
sources:
  email:
    enabled: true
    providers:
      - type: "gmail"
        credentials_file: "/path/to/gmail_credentials.json"
        check_interval: 60  # seconds
        filters:
          - field: "from"
            operator: "contains"
            value: "@company.com"
          - field: "subject"
            operator: "regex"
            value: "(urgent|critical|alert)"

      - type: "outlook"
        client_id: "your_client_id"
        client_secret: "your_client_secret"
        tenant_id: "your_tenant_id"
        scopes:
          - "Mail.Read"
          - "Mail.Read.Shared"
        folders:
          - "Inbox"
          - "Urgent"
```

### Slack Integration
```yaml
sources:
  slack:
    enabled: true
    bot_token: "xoxb-your-bot-token"
    app_token: "xapp-your-app-token"
    channels:
      include:
        - "#general"
        - "#alerts"
        - "#incidents"
      exclude:
        - "#random"
        - "#watercooler"

    event_filters:
      - type: "message"
        subtype: "bot_message"
        action: "ignore"
      - type: "reaction_added"
        emoji: "alert"
        action: "promote_to_critical"

    real_time:
      enabled: true
      socket_mode: false
      webhooks_enabled: true
```

### System Monitoring Integration
```yaml
sources:
  monitoring:
    prometheus:
      enabled: true
      url: "http://prometheus:9090"
      query_interval: 30  # seconds
      alert_rules:
        - name: "high_cpu_usage"
          query: "avg(rate(cpu_usage_seconds_total[5m])) > 0.8"
          severity: "high"
        - name: "disk_space_low"
          query: "(node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes > 0.9"
          severity: "critical"

    datadog:
      enabled: true
      api_key: "your_datadog_api_key"
      app_key: "your_datadog_app_key"
      monitors:
        tags:
          - "environment:production"
          - "service:api"

    elk_stack:
      enabled: true
      elasticsearch_url: "http://elasticsearch:9200"
      kibana_url: "http://kibana:5601"
      indices:
        - "logs-*"
        - "alerts-*"
      queries:
        security_alerts: |
          {
            "query": {
              "bool": {
                "must": [
                  {"term": {"level": "critical"}},
                  {"range": {"@timestamp": {"gte": "now-5m"}}}
                ]
              }
            }
          }
```

## Filtering and Classification Rules

### Severity Mapping
```yaml
classification:
  severity_mapping:
    critical:
      sources:
        - prometheus: "alertstate=critical"
        - datadog: "priority=P1"
        - email: "subject=(CRITICAL|URGENT|OUTAGE)"
      conditions:
        - field: "metric_value"
          operator: ">"
          threshold: 0.95
        - field: "response_time"
          operator: ">"
          threshold: 5000

    high:
      sources:
        - prometheus: "alertstate=warning"
        - datadog: "priority=P2"
        - email: "subject=(WARNING|ISSUE|PROBLEM)"
      conditions:
        - field: "metric_value"
          operator: ">"
          threshold: 0.80

    medium:
      sources:
        - email: "subject=(UPDATE|NOTICE|INFO)"
        - slack: "message contains @here"
      conditions:
        - field: "business_impact"
          operator: "in"
          values: ["medium", "low"]

    low:
      sources:
        - system_logs: "info level"
        - backup_systems: "successful completion"
```

### Content-Based Filtering
```yaml
filters:
  blacklists:
    keywords:
      - "test"
      - "testing"
      - "development"
      - "demo"
      - "sample"

    senders:
      - "noreply@test.com"
      - "system@example.com"
      - "/.*-alerts@.*/"  # Regex patterns supported

    patterns:
      - regex: ".*heartbeat.*"
        description: "System heartbeat notifications"
      - regex: "Daily.*report.*successful"
        description: "Routine success reports"

  whitelists:
    critical_sources:
      - "security@company.com"
      - "monitoring@infrastructure.com"
      - "finance@company.com"

    priority_channels:
      - "#critical-alerts"
      - "#security-incidents"
      - "#production-outages"

  temporal_filters:
    quiet_hours:
      enabled: true
      start_time: "22:00"  # 10 PM
      end_time: "07:00"    # 7 AM
      days: ["Saturday", "Sunday"]

    business_hours:
      start_time: "09:00"  # 9 AM
      end_time: "18:00"    # 6 PM
      days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
```

## Aggregation and Correlation Rules

### Event Correlation
```yaml
correlation:
  rules:
    infrastructure_outage:
      name: "Infrastructure Outage Detection"
      description: "Detect when multiple systems fail simultaneously"
      conditions:
        - field: "category"
          operator: "="
          value: "system"
        - field: "severity"
          operator: ">="
          value: "high"
        - field: "timestamp"
          window: "5m"  # 5 minute window
      grouping:
        fields: ["source_type", "location"]
        threshold: 3  # At least 3 events in window
      actions:
        - type: "group"
          name: "potential_infrastructure_issue"

    security_breach:
      name: "Security Breach Detection"
      description: "Detect coordinated security events"
      conditions:
        - field: "category"
          operator: "="
          value: "security"
        - field: "severity"
          operator: ">="
          value: "medium"
        - field: "timestamp"
          window: "10m"
      grouping:
        fields: ["user_id", "ip_address", "affected_resource"]
        threshold: 2
      actions:
        - type: "escalate"
        - type: "notify_security_team"

    deployment_issue:
      name: "Deployment Issue Detection"
      description: "Group related deployment failures"
      conditions:
        - field: "title"
          operator: "regex"
          value: "(deploy|release|build).*fail"
        - field: "timestamp"
          window: "15m"
      grouping:
        fields: ["deployment_id", "application_name"]
      actions:
        - type: "suppress_individual_notifications"
        - type: "create_summary_ticket"
```

### Suppression Rules
```yaml
suppression:
  rules:
    redundant_alerts:
      name: "Redundant Alert Suppression"
      description: "Suppress repeated alerts for same issue"
      conditions:
        - field: "fingerprint"
          operator: "="
          compare_with: "recent_notifications"
        - field: "timestamp"
          operator: "<"
          compare_with: "last_occurrence + 5m"
      suppression_duration: "10m"

    maintenance_window:
      name: "Maintenance Window Suppression"
      description: "Suppress notifications during planned maintenance"
      conditions:
        - field: "timestamp"
          operator: "between"
          value: ["2023-12-01T02:00:00Z", "2023-12-01T04:00:00Z"]
        - field: "category"
          operator: "="
          value: "system"
      exceptions:
        - severity: "critical"
        - category: "security"

    storm_suppression:
      name: "Alert Storm Suppression"
      description: "Reduce notification volume during alert storms"
      conditions:
        - field: "category"
          operator: "="
          value: "monitoring"
        - field: "volume"
          operator: ">"
          threshold: 100  # More than 100 alerts in timeframe
        - field: "timeframe"
          value: "1m"  # Per minute
      actions:
        - type: "reduce_frequency"
          factor: 5  # Only show 1 in 5 alerts
        - type: "create_digest"
          interval: "5m"
```

## Notification Delivery Configuration

### Delivery Channels
```yaml
delivery:
  channels:
    email:
      enabled: true
      smtp_server: "smtp.company.com"
      smtp_port: 587
      username: "notifications@company.com"
      password_env_var: "SMTP_PASSWORD"
      from_address: "AI Employee <notifications@company.com>"
      templates:
        critical: "templates/critical_alert.html"
        high: "templates/high_alert.html"
        medium: "templates/medium_alert.html"
        low: "templates/low_alert.html"

    sms:
      enabled: false
      provider: "twilio"
      account_sid: "your_account_sid"
      auth_token_env_var: "TWILIO_AUTH_TOKEN"
      from_number: "+1234567890"
      recipients:
        - "+1987654321"  # Primary on-call
        - "+1555123456"  # Secondary on-call

    push:
      firebase:
        enabled: true
        service_account_file: "/path/to/firebase_service_account.json"
        topic_prefix: "notifications_"

      apns:
        enabled: true
        bundle_id: "com.company.aiep"
        key_id: "your_key_id"
        team_id: "your_team_id"
        key_file: "/path/to/apns_auth_key.p8"

    chat:
      slack:
        webhook_urls:
          critical: "https://hooks.slack.com/services/critical-channel-webhook"
          high: "https://hooks.slack.com/services/alerts-channel-webhook"
          medium: "https://hooks.slack.com/services/general-channel-webhook"

      teams:
        webhook_urls:
          critical: "https://outlook.office.com/webhook/..."
          high: "https://outlook.office.com/webhook/..."
```

### Digest Scheduling
```yaml
digests:
  schedules:
    - name: "morning_summary"
      cron: "0 8 * * 1-5"  # Every weekday at 8 AM
      timezone: "America/New_York"
      recipients:
        - "managers@company.com"
        - "executives@company.com"
      content:
        include_categories: ["business", "system", "financial"]
        include_severities: ["high", "medium", "low"]
        exclude_sources: ["system_logs"]
        format: "detailed"

    - name: "evening_summary"
      cron: "0 18 * * 1-5"  # Every weekday at 6 PM
      timezone: "America/New_York"
      recipients:
        - "ops-team@company.com"
      content:
        include_categories: ["system", "monitoring"]
        include_severities: ["medium", "low"]
        format: "summary"

    - name: "weekly_review"
      cron: "0 9 * * 1"  # Every Monday at 9 AM
      timezone: "America/New_York"
      recipients:
        - "leadership@company.com"
      content:
        include_categories: ["all"]
        include_severities: ["all"]
        include_metrics: true
        format: "executive_summary"
```

## Advanced Processing Rules

### Business Hours Configuration
```yaml
business_rules:
  hours:
    default:
      start: "09:00"
      end: "17:00"
      timezone: "America/New_York"
      days: [1, 2, 3, 4, 5]  # Monday to Friday

    exceptions:
      - name: "maintenance_window"
        start_date: "2023-12-01"
        end_date: "2023-12-02"
        hours:
          start: "02:00"
          end: "04:00"

      - name: "holiday_schedule"
        dates: ["2023-12-25", "2024-01-01"]
        hours: []
        description: "Closed on holidays"

  escalation_levels:
    - level: 1
      roles: ["primary_oncall"]
      timeout: "15m"
      notification_methods: ["sms", "push"]

    - level: 2
      roles: ["secondary_oncall", "manager"]
      timeout: "30m"
      notification_methods: ["sms", "phone_call"]

    - level: 3
      roles: ["director", "cto"]
      timeout: "1h"
      notification_methods: ["sms", "phone_call", "email"]
```

### Custom Processing Scripts
```yaml
custom_processing:
  scripts:
    - name: "financial_alert_enrichment"
      type: "python"
      path: "./scripts/financial_enrichment.py"
      triggers:
        - category: "financial"
        - severity: "high"
      inputs:
        - "notification_payload"
        - "current_portfolio_value"
        - "market_conditions"

    - name: "security_context_enrichment"
      type: "javascript"
      path: "./scripts/security_enrichment.js"
      triggers:
        - category: "security"
        - severity: ">=medium"
      inputs:
        - "notification_payload"
        - "user_access_logs"
        - "threat_intelligence_feeds"
```

## Performance Tuning

### Queue and Buffer Configuration
```yaml
performance:
  queues:
    input_queue:
      size: 5000
      timeout: 30s
      retry_attempts: 3

    processing_queue:
      size: 2000
      workers: 8
      timeout: 60s

    delivery_queue:
      size: 1000
      retry_attempts: 5
      backoff_multiplier: 2

  caching:
    enabled: true
    type: "redis"
    host: "localhost"
    port: 6379
    ttl: 3600  # 1 hour

    patterns:
      - key: "notification_fingerprints"
        ttl: 1800  # 30 minutes
      - key: "user_preferences"
        ttl: 7200  # 2 hours
      - key: "correlation_groups"
        ttl: 300   # 5 minutes

  rate_limits:
    per_source:
      default: 100  # per minute
      critical: 200  # per minute
    per_user: 50    # per minute
    global: 1000    # per minute
```

## Monitoring and Alerting Configuration

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

    processing_delay:
      threshold: 30  # seconds
      action: "scale_up_workers"

    delivery_failures:
      threshold: 5  # per minute
      action: "switch_backup_channel"

  health_checks:
    endpoints:
      - name: "database_connection"
        type: "sql_ping"
        connection_string: "sqlite:///notifications.db"
        timeout: 5

      - name: "external_api_health"
        type: "http_get"
        url: "https://api.statuspage.io/v1/pages"
        timeout: 10
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
          - id: "mobile_app"
            secret_env_var: "MOBILE_APP_API_KEY"
            permissions: ["read", "acknowledge"]

          - id: "monitoring_system"
            secret_env_var: "MONITORING_API_KEY"
            permissions: ["create", "read"]

  authorization:
    roles:
      user:
        permissions: ["read_own", "acknowledge_own"]
      administrator:
        permissions: ["read_all", "acknowledge_all", "configure_filters"]
      auditor:
        permissions: ["read_all", "generate_reports"]

    rbac_enabled: true
    default_role: "user"
```

### Encryption and Privacy
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

  pii_detection:
    enabled: true
    patterns:
      - name: "credit_card"
        regex: "\\b(?:4[0-9]{12}(?:[0-9]{3})?|[25][1-7][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13}|3[0-9]{14}|(?:2131|1800|35\\d{3})\\d{11})\\b"
        action: "mask_partially"

      - name: "ssn"
        regex: "\\b\\d{3}-\\d{2}-\\d{4}\\b"
        action: "mask_completely"

  retention:
    policies:
      critical: "7y"      # 7 years
      high: "2y"         # 2 years
      medium: "1y"       # 1 year
      low: "90d"         # 90 days
      default: "30d"     # 30 days
```