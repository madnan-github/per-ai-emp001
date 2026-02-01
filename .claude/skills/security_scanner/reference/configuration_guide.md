# Security Scanner Configuration Guide

## Overview
This guide provides comprehensive configuration instructions for the Security Scanner skill, which provides comprehensive security scanning and vulnerability assessment for the Personal AI Employee system.

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Required Python packages:
  - nmap (for network scanning)
  - requests (for API calls)
  - beautifulsoup4 (for web scraping)
  - cryptography (for security operations)
  - validators (for input validation)
  - pyyaml (for configuration parsing)
  - schedule (for scheduling)

### Environment Variables
Set these environment variables for secure configuration:

```
SECURITY_SCANNER_DATABASE_PATH=/data/vulnerabilities.db
SECURITY_SCANNER_LOG_LEVEL=INFO
SECURITY_SCANNER_SCAN_TIMEOUT_SECONDS=3600
SECURITY_SCANNER_MAX_CONCURRENT_SCANS=5
SECURITY_SCANNER_REPORTS_PATH=/reports/security/
SECURITY_SCANNER_THREAT_FEED_URL=https://feeds.example.com/threats
SECURITY_SCANNER_CREDENTIALS_PATH=/secure/scanner_credentials.json
SECURITY_SCANNER_VULNERABILITY_DB_PATH=/data/nvd_vulnerabilities.json
```

## Security Scanning Configuration

### Basic Scanning Settings
```json
{
  "scanning": {
    "default_scan_depth": "standard",
    "timeout_seconds": 3600,
    "max_concurrent_scans": 5,
    "scan_results_retention_days": 90,
    "enable_safe_scanning": true,
    "exclude_sensitive_directories": ["/etc/shadow", "/etc/passwd", "/proc/*"]
  }
}
```

### Scan Type Configurations
```json
{
  "scan_types": {
    "vulnerability": {
      "enabled": true,
      "nvd_feed_url": "https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-modified.json.gz",
      "update_frequency_hours": 2,
      "cvss_thresholds": {
        "low": {"min": 0.1, "max": 3.9},
        "medium": {"min": 4.0, "max": 6.9},
        "high": {"min": 7.0, "max": 8.9},
        "critical": {"min": 9.0, "max": 10.0}
      }
    },
    "configuration": {
      "enabled": true,
      "baseline_configs": {
        "ssh": {
          "recommended_settings": {
            "protocol": 2,
            "password_authentication": "no",
            "pubkey_authentication": "yes"
          }
        },
        "apache": {
          "recommended_settings": {
            "server_tokens": "Prod",
            "server_signature": "Off"
          }
        }
      }
    },
    "file_integrity": {
      "enabled": true,
      "watch_directories": ["/etc/", "/bin/", "/sbin/", "/usr/bin/", "/usr/sbin/"],
      "monitor_extensions": [".exe", ".dll", ".so", ".sh", ".bat", ".cmd"],
      "baseline_snapshot_interval_hours": 24
    },
    "network": {
      "enabled": true,
      "ports_to_scan": "top_1000",
      "host_discovery_enabled": true,
      "os_detection_enabled": true,
      "service_detection_enabled": true,
      "safe_scan_modes": true
    },
    "compliance": {
      "enabled": true,
      "standards_supported": ["nist", "iso27001", "sox", "gdpr", "hipaa"],
      "audit_frequency_days": 7,
      "compliance_threshold_percent": 95
    }
  }
}
```

## Compliance Configuration

### NIST Cybersecurity Framework
```json
{
  "compliance": {
    "nist_framework": {
      "identify": {
        "asset_inventory": {
          "enabled": true,
          "scan_frequency": "daily",
          "asset_categories": ["hardware", "software", "data", "people", "services"]
        },
        "risk_assessment": {
          "enabled": true,
          "methodology": "semi_quantitative",
          "assessment_frequency": "quarterly",
          "risk_tolerance": 0.2
        },
        "governance": {
          "enabled": true,
          "policy_compliance": true,
          "role_clarity": true,
          "budget_alignment": true
        }
      },
      "protect": {
        "access_control": {
          "enabled": true,
          "principle_of_least_privilege": true,
          "separation_of_duties": true,
          "account_management": true
        },
        "awareness_training": {
          "enabled": true,
          "phishing_simulation": true,
          "security_awareness": true,
          "role_based_training": true
        },
        "data_security": {
          "enabled": true,
          "classification_scheme": "defined",
          "handling_requirements": "documented",
          "protection_processes": "implemented"
        }
      }
    }
  }
}
```

### ISO 27001 Controls
```json
{
  "compliance": {
    "iso_27001": {
      "control_groups": {
        "information_security_policies": {
          "controls": ["A.5.1", "A.5.2", "A.5.3"],
          "assessment_frequency": "annual",
          "evidence_requirements": ["policy_document", "approval_records"]
        },
        "asset_management": {
          "controls": ["A.6.1", "A.6.2", "A.7.1"],
          "assessment_frequency": "semi_annual",
          "evidence_requirements": ["asset_register", "classification_document"]
        },
        "human_resource_security": {
          "controls": ["A.7.1", "A.7.2", "A.7.3"],
          "assessment_frequency": "annual",
          "evidence_requirements": ["screening_records", "nda_signatures"]
        }
      }
    }
  }
}
```

## Threat Intelligence Configuration

### Threat Feed Integration
```json
{
  "threat_intelligence": {
    "enabled": true,
    "feeds": [
      {
        "name": "vendor_threat_feed",
        "url": "https://threats.vendor.com/feed",
        "format": "json",
        "polling_interval_minutes": 60,
        "api_key_env_var": "THREAT_FEED_API_KEY"
      },
      {
        "name": "open_threat_feed",
        "url": "https://open.threat.feed.io/data",
        "format": "csv",
        "polling_interval_minutes": 120
      }
    ],
    "indicators": {
      "ip_addresses": {
        "enabled": true,
        "severity_threshold": "medium",
        "lookup_timeout_seconds": 10
      },
      "domains": {
        "enabled": true,
        "severity_threshold": "medium",
        "lookup_timeout_seconds": 10
      },
      "urls": {
        "enabled": true,
        "severity_threshold": "high",
        "lookup_timeout_seconds": 15
      },
      "file_hashes": {
        "enabled": true,
        "severity_threshold": "high",
        "lookup_timeout_seconds": 10
      }
    }
  }
}
```

## Vulnerability Management Configuration

### Vulnerability Database
```json
{
  "vulnerability_management": {
    "database": {
      "type": "sqlite",
      "path": "/data/vulnerabilities.db",
      "retention_days": 365,
      "update_frequency_hours": 2
    },
    "severity_thresholds": {
      "low": {"min": 0.1, "max": 3.9},
      "medium": {"min": 4.0, "max": 6.9},
      "high": {"min": 7.0, "max": 8.9},
      "critical": {"min": 9.0, "max": 10.0}
    },
    "remediation_timeframes": {
      "critical": "24_hours",
      "high": "7_days",
      "medium": "30_days",
      "low": "90_days"
    }
  }
}
```

### Risk Scoring
```json
{
  "risk_assessment": {
    "cvss_v3_vector_strings": [
      "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",  // Critical
      "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",  // Critical
      "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:L/A:H",  // High
      "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",  // High
      "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:L"   // Medium
    ],
    "qualitative_scoring": {
      "probability_levels": {
        "frequent": 5,
        "likely": 4,
        "occasional": 3,
        "unlikely": 2,
        "rare": 1
      },
      "impact_levels": {
        "catastrophic": 5,
        "major": 4,
        "moderate": 3,
        "minor": 2,
        "negligible": 1
      }
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
        "scans_executed",
        "vulnerabilities_found",
        "compliance_score",
        "threat_indicators",
        "system_performance"
      ]
    },
    "health_checks": {
      "scanner_health": true,
      "database_connectivity": true,
      "threat_feed_connectivity": true,
      "scan_engine_health": true
    },
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/security_scanner.log",
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
        "name": "critical_vulnerability_found",
        "condition": "vulnerability.severity == 'critical'",
        "severity": "critical",
        "recipients": ["admin@example.com", "security@example.com"],
        "notification_method": ["email", "sms", "dashboard"]
      },
      {
        "name": "compliance_failure",
        "condition": "compliance.score < 0.8",
        "severity": "high",
        "recipients": ["admin@example.com", "compliance-officer@example.com"],
        "notification_method": ["email", "slack"]
      },
      {
        "name": "scanner_performance_issue",
        "condition": "scanner_response_time > 300",
        "severity": "medium",
        "recipients": ["admin@example.com"],
        "notification_method": ["email"]
      },
      {
        "name": "threat_indicator_detected",
        "condition": "threat.confidence > 0.8",
        "severity": "high",
        "recipients": ["admin@example.com", "security@example.com"],
        "notification_method": ["email", "sms"]
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
        "sender_email": "security-scanner@acme.com"
      },
      "slack": {
        "enabled": true,
        "webhook_url_env_var": "SLACK_WEBHOOK_URL",
        "channel": "#security-alerts"
      },
      "dashboard": {
        "enabled": true,
        "url": "https://dashboard.acme.com/security"
      }
    },
    "event_triggers": [
      {
        "name": "scan_completed",
        "condition": "scan.status == 'completed'",
        "recipients": ["security-team@example.com"],
        "channels": ["email", "dashboard"]
      },
      {
        "name": "vulnerability_report",
        "condition": "vulnerability.count > 0",
        "recipients": ["admin@example.com", "security@example.com"],
        "channels": ["email", "slack"]
      },
      {
        "name": "compliance_audit",
        "condition": "compliance.audit_due == true",
        "recipients": ["compliance-officer@example.com"],
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
      "cpu_percentage": 30,
      "memory_percentage": 25,
      "disk_io_percentage": 20,
      "network_bandwidth_limit_mbps": 50
    },
    "scan_optimization": {
      "max_scan_processes": 3,
      "scan_batch_size": 100,
      "concurrent_asset_scans": 10,
      "scan_timeout_seconds": 3600
    },
    "caching": {
      "enabled": true,
      "scan_results_ttl_seconds": 3600,
      "vulnerability_cache_ttl_seconds": 7200,
      "max_cache_entries": 10000
    }
  }
}
```

## Integration Configuration

### External System Integration
```json
{
  "integrations": {
    "siem": [
      {
        "name": "splunk",
        "enabled": true,
        "hec_url": "https://splunk.example.com:8088/services/collector",
        "hec_token_env_var": "SPLUNK_HEC_TOKEN",
        "index": "security_events"
      }
    ],
    "ticketing_systems": [
      {
        "name": "servicenow",
        "enabled": true,
        "instance_url": "https://acme.service-now.com",
        "username_env_var": "SERVICENOW_USERNAME",
        "password_env_var": "SERVICENOW_PASSWORD",
        "table_name": "incident"
      }
    ],
    "monitoring_tools": [
      {
        "name": "prometheus",
        "enabled": true,
        "endpoint": "http://prometheus:9090",
        "push_gateway": "http://pushgateway:9091"
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
    "port": 8087,
    "ssl": {
      "enabled": true,
      "cert_path": "/secure/server.crt",
      "key_path": "/secure/server.key"
    },
    "authentication": {
      "enabled": true,
      "method": "api_key",
      "api_key_env_var": "SCANNER_API_KEY"
    },
    "rate_limiting": {
      "enabled": true,
      "requests_per_minute": 100,
      "burst_capacity": 200
    }
  }
}
```

## Sample Configuration File

Create a `scanner_config.json` file with your configuration:

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
    "default_scan_depth": "standard",
    "max_concurrent_scans": 5
  },
  "scanning": {
    "default_scan_depth": "standard",
    "timeout_seconds": 3600,
    "max_concurrent_scans": 5
  },
  "scan_types": {
    "vulnerability": {
      "enabled": true,
      "update_frequency_hours": 2
    },
    "configuration": {
      "enabled": true
    },
    "file_integrity": {
      "enabled": true,
      "watch_directories": ["/etc/", "/bin/"]
    },
    "network": {
      "enabled": true,
      "ports_to_scan": "top_1000"
    },
    "compliance": {
      "enabled": true,
      "standards_supported": ["nist", "iso27001"]
    }
  },
  "threat_intelligence": {
    "enabled": true,
    "feeds": [
      {
        "name": "vendor_threat_feed",
        "url": "https://threats.vendor.com/feed",
        "polling_interval_minutes": 60
      }
    ]
  },
  "vulnerability_management": {
    "database": {
      "path": "/data/vulnerabilities.db",
      "retention_days": 365
    },
    "severity_thresholds": {
      "critical": {"min": 9.0, "max": 10.0}
    }
  },
  "monitoring": {
    "enabled": true,
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/security_scanner.log"
    }
  }
}
```