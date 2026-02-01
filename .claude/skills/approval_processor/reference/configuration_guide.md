# Approval Processor Configuration Guide

## Overview
This document provides comprehensive configuration options for the Approval Processor skill, covering workflow definitions, approval chains, thresholds, and integration settings.

## Global Configuration

### Main Configuration File Structure
```yaml
approval_processor:
  # Server settings
  server:
    enabled: true
    host: "localhost"
    port: 8082
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
    path: "./approvals.db"
    retention_days: 365
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

## Approval Chain Configuration

### Financial Approval Chains
```yaml
approval_chains:
  financial:
    payment_approvals:
      enabled: true
      thresholds:
        - amount: 0
          level: 1
          approvers:
            - role: "direct_supervisor"
              required_approvals: 1
          deadline: "PT24H"  # 24 hours

        - amount: 500
          level: 2
          approvers:
            - role: "department_manager"
              required_approvals: 1
          deadline: "PT48H"  # 48 hours

        - amount: 5000
          level: 3
          approvers:
            - role: "director"
              required_approvals: 1
            - role: "finance_lead"
              required_approvals: 1
          required_approvals: 2  # Both must approve
          deadline: "PT168H"  # 1 week

        - amount: 25000
          level: 4
          approvers:
            - role: "vp"
              required_approvals: 1
          deadline: "PT336H"  # 2 weeks

    expense_approvals:
      enabled: true
      thresholds:
        - amount: 0
          level: 1
          approvers:
            - role: "manager"
              required_approvals: 1
          deadline: "PT168H"  # 1 week

        - amount: 1000
          level: 2
          approvers:
            - role: "department_head"
              required_approvals: 1
          deadline: "PT336H"  # 2 weeks

    purchase_approvals:
      enabled: true
      thresholds:
        - amount: 0
          level: 1
          approvers:
            - role: "procurement_coordinator"
              required_approvals: 1
          deadline: "PT24H"

        - amount: 10000
          level: 2
          approvers:
            - role: "department_manager"
              required_approvals: 1
          deadline: "PT168H"

        - amount: 50000
          level: 3
          approvers:
            - role: "chief_procurement_officer"
              required_approvals: 1
          deadline: "PT672H"  # 4 weeks
```

### Communication Approval Chains
```yaml
approval_chains:
  communication:
    external_communications:
      enabled: true
      sensitivity_levels:
        - level: "public"
          approvers:
            - role: "marketing_coordinator"
          required_approvals: 1
          deadline: "PT24H"
          auto_approved: true  # For low-risk public content

        - level: "internal"
          approvers:
            - role: "team_lead"
          required_approvals: 1
          deadline: "PT48H"

        - level: "confidential"
          approvers:
            - role: "department_head"
            - role: "legal_counsel"
          required_approvals: 2  # Both must approve
          deadline: "PT168H"

        - level: "restricted"
          approvers:
            - role: "executive"
            - role: "legal_counsel"
            - role: "compliance_officer"
          required_approvals: 3  # All must approve
          deadline: "PT336H"

    press_releases:
      enabled: true
      approvers:
        - role: "communications_director"
        - role: "legal_counsel"
        - role: "ceo"
      required_approvals: 3
      deadline: "PT168H"
```

### Operational Approval Chains
```yaml
approval_chains:
  operational:
    system_changes:
      enabled: true
      change_types:
        - type: "minor_update"
          approvers:
            - role: "technical_lead"
          required_approvals: 1
          deadline: "PT24H"

        - type: "major_update"
          approvers:
            - role: "devops_manager"
            - role: "security_officer"
          required_approvals: 2
          deadline: "PT168H"

        - type: "infrastructure_change"
          approvers:
            - role: "infrastructure_architect"
            - role: "security_officer"
            - role: "operations_director"
          required_approvals: 3
          deadline: "PT336H"

    access_requests:
      enabled: true
      access_levels:
        - level: "standard"
          approvers:
            - role: "manager"
          required_approvals: 1
          deadline: "PT24H"

        - level: "elevated"
          approvers:
            - role: "manager"
            - role: "security_officer"
          required_approvals: 2
          deadline: "PT48H"

        - level: "admin"
          approvers:
            - role: "director"
            - role: "security_officer"
            - role: "it_governance"
          required_approvals: 3
          deadline: "PT168H"
```

## Auto-Approval Rules

### Auto-Approval Configuration
```yaml
auto_approval_rules:
  enabled: true
  rules:
    - name: "small_payments"
      description: "Automatically approve small payments"
      conditions:
        - field: "approval_type"
          operator: "="
          value: "financial"
        - field: "category"
          operator: "="
          value: "payment"
        - field: "amount"
          operator: "<="
          value: 100.00
        - field: "vendor_risk_score"
          operator: "<"
          value: 0.5
      action: "auto_approve"
      reason: "Low value, low risk payment"

    - name: "regular_subscriptions"
      description: "Automatically approve known subscription renewals"
      conditions:
        - field: "category"
          operator: "="
          value: "subscription"
        - field: "is_recurring"
          operator: "="
          value: true
        - field: "vendor_trusted"
          operator: "="
          value: true
        - field: "amount_variance"
          operator: "<="
          value: 0.1  # 10% variance allowed
      action: "auto_approve"
      reason: "Regular, trusted subscription renewal"

    - name: "internal_transfers"
      description: "Automatically approve internal fund transfers"
      conditions:
        - field: "category"
          operator: "="
          value: "internal_transfer"
        - field: "within_company"
          operator: "="
          value: true
      action: "auto_approve"
      reason: "Internal company transfer"

  exceptions:
    - name: "fraudulent_vendor"
      description: "Block auto-approval for known fraudulent vendors"
      conditions:
        - field: "vendor_id"
          operator: "in"
          value: ["vendor-123", "vendor-456"]
      action: "block_auto_approval"
      reason: "Known fraudulent vendor"
```

## Escalation Rules

### Time-Based Escalation
```yaml
escalation_rules:
  time_based:
    enabled: true
    rules:
      - name: "first_reminder"
        description: "Send first reminder at 50% of deadline"
        conditions:
          - field: "progress"
            operator: "<="
            value: 0.5  # 50% of deadline passed
          - field: "status"
            operator: "="
            value: "pending"
        action: "send_reminder"
        delay: "PT0S"  # Immediate

      - name: "second_reminder"
        description: "Send second reminder at 80% of deadline"
        conditions:
          - field: "progress"
            operator: "<="
            value: 0.8  # 80% of deadline passed
          - field: "status"
            operator: "="
            value: "pending"
        action: "send_reminder"
        delay: "PT0S"

      - name: "escalate_approver"
        description: "Escalate to backup approver after deadline"
        conditions:
          - field: "progress"
            operator: ">"
            value: 1.0  # Deadline exceeded
          - field: "status"
            operator: "="
            value: "pending"
        action: "escalate_to_backup"
        delay: "PT0S"

      - name: "management_notification"
        description: "Notify management after secondary deadline"
        conditions:
          - field: "progress"
            operator: ">"
            value: 2.0  # 2x deadline exceeded
          - field: "status"
            operator: "="
            value: "pending"
        action: "notify_management"
        delay: "PT0S"

  exception_based:
    enabled: true
    rules:
      - name: "approver_unavailable"
        description: "Transfer to backup when approver is unavailable"
        conditions:
          - field: "approver_status"
            operator: "="
            value: "on_leave"
        action: "transfer_to_backup"
        delay: "PT0S"

      - name: "conflict_of_interest"
        description: "Transfer when conflict of interest detected"
        conditions:
          - field: "requestor_id"
            operator: "="
            value: "$current.approver_id"
          - field: "relationship"
            operator: "in"
            value: ["family_member", "close_associate"]
        action: "transfer_to_alternate"
        delay: "PT0S"
```

## Notification Configuration

### Notification Templates
```yaml
notifications:
  templates:
    approval_request:
      subject: "Action Required: Approval Request #{{ request.id }}"
      email_html: |
        <h2>Approval Request #{{ request.id }}</h2>
        <p><strong>Requestor:</strong> {{ request.requestor.name }} ({{ request.requestor.department }})</p>
        <p><strong>Category:</strong> {{ request.category }}</p>
        <p><strong>Amount:</strong> {{ request.currency }} {{ request.amount }}</p>
        <p><strong>Description:</strong> {{ request.description }}</p>
        <p><strong>Justification:</strong> {{ request.justification }}</p>
        <div style="margin-top: 20px;">
          <a href="{{ approval_url }}/approve/{{ request.id }}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Approve</a>
          <a href="{{ approval_url }}/reject/{{ request.id }}" style="background-color: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Reject</a>
          <a href="{{ approval_url }}/details/{{ request.id }}" style="background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">View Details</a>
        </div>
      email_text: |
        Approval Request #{{ request.id }}

        Requestor: {{ request.requestor.name }} ({{ request.requestor.department }})
        Category: {{ request.category }}
        Amount: {{ request.currency }} {{ request.amount }}
        Description: {{ request.description }}
        Justification: {{ request.justification }}

        Approve: {{ approval_url }}/approve/{{ request.id }}
        Reject: {{ approval_url }}/reject/{{ request.id }}
        Details: {{ approval_url }}/details/{{ request.id }}

    approval_reminder:
      subject: "Reminder: Pending Approval Request #{{ request.id }}"
      email_html: |
        <h2>Pending Approval Request #{{ request.id }}</h2>
        <p>This approval request is approaching its deadline.</p>
        <p><strong>Requestor:</strong> {{ request.requestor.name }}</p>
        <p><strong>Amount:</strong> {{ request.currency }} {{ request.amount }}</p>
        <p><strong>Due:</strong> {{ request.due_date | date('short') }}</p>
        <div style="margin-top: 20px;">
          <a href="{{ approval_url }}/details/{{ request.id }}" style="background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">View Request</a>
        </div>

    approval_complete:
      subject: "Approval Complete: Request #{{ request.id }} - {{ action }}"
      email_html: |
        <h2>Approval Complete</h2>
        <p>Request #{{ request.id }} has been {{ action }}.</p>
        <p><strong>Approver:</strong> {{ approver.name }}</p>
        <p><strong>Decision:</strong> {{ action | upper }}</p>
        {% if comments %}
        <p><strong>Comments:</strong> {{ comments }}</p>
        {% endif %}
```

### Notification Channels
```yaml
notifications:
  channels:
    email:
      enabled: true
      smtp_server: "smtp.company.com"
      smtp_port: 587
      username: "approvals@company.com"
      password_env_var: "SMTP_PASSWORD"
      from_address: "Approval System <approvals@company.com>"
      recipients:
        requestor_notifications: true
        manager_notifications: true
        cc_on_approvals: ["finance@company.com"]

    slack:
      enabled: true
      webhook_urls:
        approval_requests: "https://hooks.slack.com/services/approval-requests-channel"
        critical_approvals: "https://hooks.slack.com/services/critical-approvals-channel"
        approval_completions: "https://hooks.slack.com/services/approval-completions-channel"
      templates:
        approval_request: |
          :bell: *New Approval Request* (ID: {{ request.id }})
          Requestor: {{ request.requestor.name }}
          Category: {{ request.category }}
          Amount: {{ request.currency }} {{ request.amount }}
          Description: {{ request.description }}
          <{{ approval_url }}/details/{{ request.id }}|View Details>

    microsoft_teams:
      enabled: true
      webhook_urls:
        approval_requests: "https://outlook.office.com/webhook/..."
      card_template: |
        {
          "type": "AdaptiveCard",
          "@type": "MessageCard",
          "title": "New Approval Request",
          "sections": [
            {
              "facts": [
                {"name": "ID", "value": "{{ request.id }}"},
                {"name": "Requestor", "value": "{{ request.requestor.name }}"},
                {"name": "Category", "value": "{{ request.category }}"},
                {"name": "Amount", "value": "{{ request.currency }} {{ request.amount }}"},
                {"name": "Description", "value": "{{ request.description }}"}
              ]
            }
          ],
          "potentialAction": [
            {
              "@type": "OpenUri",
              "name": "View Details",
              "targets": [{"os": "default", "uri": "{{ approval_url }}/details/{{ request.id }}"}]
            }
          ]
        }
```

## User and Role Management

### Role Definitions
```yaml
roles:
  definitions:
    - name: "requestor"
      permissions:
        - "submit_request"
        - "view_own_requests"
        - "cancel_own_requests"

    - name: "approver"
      permissions:
        - "view_requests"
        - "approve_requests"
        - "reject_requests"
        - "request_info"

    - name: "manager"
      permissions:
        - "view_team_requests"
        - "approve_team_requests"
        - "escalate_requests"
        - "view_reports"

    - name: "administrator"
      permissions:
        - "manage_approvals"
        - "configure_rules"
        - "view_all_requests"
        - "override_approvals"
        - "manage_users"
        - "view_audit_logs"

    - name: "auditor"
      permissions:
        - "view_all_requests"
        - "view_audit_logs"
        - "generate_reports"
        - "export_data"

  assignments:
    # Static role assignments
    static_assignments:
      - user_id: "user-001"
        roles: ["manager", "approver"]
        departments: ["engineering", "product"]

      - user_id: "user-002"
        roles: ["administrator"]

      - user_id: "user-003"
        roles: ["auditor"]

    # Dynamic role assignments based on attributes
    dynamic_assignments:
      - role: "approver"
        conditions:
          - field: "job_title"
            operator: "contains"
            value: "Manager"
          - field: "department_budget_authority"
            operator: "="
            value: true

      - role: "financial_approver"
        conditions:
          - field: "department"
            operator: "in"
            value: ["finance", "accounting"]
          - field: "budget_approval_rights"
            operator: ">="
            value: 10000
```

### Hierarchy Configuration
```yaml
hierarchy:
  enabled: true
  sources:
    - type: "ldap"
      base_dn: "ou=people,dc=company,dc=com"
      manager_attribute: "manager"
      department_attribute: "department"

    - type: "hr_system"
      api_endpoint: "https://hr-api.company.com/v1/employees"
      auth:
        type: "oauth2"
        client_id: "hr_api_client"
        client_secret_env_var: "HR_API_SECRET"
      mapping:
        employee_id: "id"
        manager_id: "managerId"
        department: "department"
        job_title: "jobTitle"

  overrides:
    - employee_id: "emp-12345"
      manager_id: "emp-67890"  # Override reported manager
      effective_date: "2023-01-01"
      expiration_date: "2023-12-31"

    - department: "special_project"
      approval_delegate: "emp-abc123"  # Designate special approver
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
        scopes:
          - "openid"
          - "email"
          - "profile"

      - type: "saml"
        idp_metadata_url: "https://company.okta.com/app/company-approval/idp/metadata"
        sp_entity_id: "approval-system"
        acs_url: "https://approval.company.com/auth/callback"

      - type: "api_key"
        header: "X-API-Key"
        keys:
          - id: "integration_service"
            secret_env_var: "INTEGRATION_API_KEY"
            permissions: ["submit_request", "view_status"]

  authorization:
    rbac_enabled: true
    default_role: "requestor"

    permission_mapping:
      submit_request: ["requestor", "manager", "administrator"]
      view_own_requests: ["requestor", "approver", "manager", "administrator", "auditor"]
      approve_requests: ["approver", "manager", "administrator"]
      reject_requests: ["approver", "manager", "administrator"]
      override_approvals: ["administrator"]
      view_audit_logs: ["administrator", "auditor"]
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
      approved_requests: "7y"      # 7 years for compliance
      rejected_requests: "3y"      # 3 years for audit
      cancelled_requests: "1y"     # 1 year
      system_logs: "2y"            # 2 years
      default: "7y"                # 7 years for everything else
```

## Integration Configuration

### ERP/Financial System Integration
```yaml
integrations:
  erp_systems:
    sap:
      enabled: true
      api_base_url: "https://sap.company.com/sap/opu/odata"
      auth:
        type: "basic"
        username: "sap_integration"
        password_env_var: "SAP_PASSWORD"
      endpoints:
        purchase_orders: "/sap/opu/odata/sap/API_PURCHASEORDER_SRV/PurchaseOrder"
        payments: "/sap/opu/odata/sap/API_OUTBOUND_PAYMENT_SRV/OutboundPayment"
        cost_centers: "/sap/opu/odata/sap/API_COST_CENTER_2_SRV/CostCenter"

    netsuite:
      enabled: true
      account_id: "ACCT1234567"
      auth:
        type: "token_passport"
        consumer_key: "netsuite_consumer_key"
        consumer_secret_env_var: "NETSUITE_CONSUMER_SECRET"
        token_id: "netsuite_token_id"
        token_secret_env_var: "NETSUITE_TOKEN_SECRET"
      endpoints:
        transactions: "/services/rest/record/v1/transactions"
        vendors: "/services/rest/record/v1/vendors"

  accounting_software:
    quickbooks:
      enabled: true
      realm_id: "qb_realm_id"
      auth:
        type: "oauth2"
        client_id: "qb_client_id"
        client_secret_env_var: "QB_CLIENT_SECRET"
      endpoints:
        invoices: "/v3/company/{{ realm_id }}/invoice"
        bills: "/v3/company/{{ realm_id }}/bill"
        vendors: "/v3/company/{{ realm_id }}/vendor"
```

### Identity Management Integration
```yaml
integrations:
  identity_management:
    active_directory:
      enabled: true
      server: "ldaps://ad.company.com:636"
      base_dn: "DC=company,DC=com"
      bind_dn: "CN=service-account,CN=Users,DC=company,DC=com"
      bind_password_env_var: "AD_BIND_PASSWORD"
      user_search_filter: "(objectClass=user)"
      group_search_filter: "(objectClass=group)"
      attribute_mapping:
        user_id: "sAMAccountName"
        email: "mail"
        full_name: "displayName"
        department: "department"
        manager: "manager"
        job_title: "title"

    okta:
      enabled: true
      org_url: "https://company.okta.com"
      auth:
        type: "api_token"
        token_env_var: "OKTA_API_TOKEN"
      endpoints:
        users: "/api/v1/users"
        groups: "/api/v1/groups"
        apps: "/api/v1/apps"
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

    approval_backlog:
      threshold: 100  # pending approvals
      action: "alert_administrators"

    system_errors:
      threshold: 10  # per minute
      action: "escalate_to_support"

  health_checks:
    endpoints:
      - name: "database_connection"
        type: "sql_ping"
        connection_string: "sqlite:///approvals.db"
        timeout: 5

      - name: "external_api_health"
        type: "http_get"
        url: "https://api.statuspage.io/v1/pages"
        timeout: 10

  audit_logging:
    enabled: true
    level: "full"  # none, basic, full
    include:
      - "request_submission"
      - "approval_decisions"
      - "access_logs"
      - "configuration_changes"
      - "user_authentication"

    exclude:
      - "health_checks"
      - "status_queries"
```

### Compliance Reporting
```yaml
reports:
  compliance:
    sox_reporting:
      enabled: true
      controls:
        - name: "proper_approval_authority"
          description: "Ensuring only authorized individuals can approve requests"
          frequency: "monthly"
          recipients: ["compliance@company.com", "sox@company.com"]

        - name: "adequate_documentation"
          description: "Verifying all approval decisions are properly documented"
          frequency: "monthly"
          recipients: ["compliance@company.com"]

    scheduled_reports:
      - name: "monthly_approval_summary"
        schedule: "0 1 1 * *"  # 1st of month at 1 AM
        template: "monthly_summary.j2"
        recipients: ["finance@company.com", "executives@company.com"]
        filters:
          date_range: "previous_month"
          status: ["approved", "rejected"]

      - name: "quarterly_compliance_audit"
        schedule: "0 2 1 1,4,7,10 *"  # 1st of Jan/Apr/Jul/Oct at 2 AM
        template: "compliance_audit.j2"
        recipients: ["compliance@company.com", "external_auditors@external.com"]
        filters:
          date_range: "previous_quarter"
          include_details: true
```