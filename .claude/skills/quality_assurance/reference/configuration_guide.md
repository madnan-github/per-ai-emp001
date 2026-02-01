# Quality Assurance Configuration Guide

## Overview
This guide provides comprehensive configuration instructions for the Quality Assurance skill, which provides comprehensive testing, validation, and quality control for the Personal AI Employee system.

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Required Python packages:
  - pytest (for testing framework)
  - coverage (for test coverage)
  - pylint (for code analysis)
  - flake8 (for code linting)
  - mypy (for static type checking)
  - bandit (for security testing)
  - selenium (for UI testing)
  - requests (for API testing)

### Environment Variables
Set these environment variables for secure configuration:

```
QUALITY_ASSURANCE_DATABASE_PATH=/data/test_results.db
QUALITY_ASSURANCE_LOG_LEVEL=INFO
QUALITY_ASSURANCE_TEST_TIMEOUT_SECONDS=300
QUALITY_ASSURANCE_MAX_CONCURRENT_TESTS=10
QUALITY_ASSURANCE_REPORTS_PATH=/reports/test_results/
QUALITY_ASSURANCE_COVERAGE_THRESHOLD=80
QUALITY_ASSURANCE_QUALITY_GATE_THRESHOLD=90
QUALITY_ASSURANCE_PERFORMANCE_THRESHOLD_MS=1000
```

## Quality Assurance Configuration

### Basic QA Settings
```json
{
  "qa": {
    "default_test_timeout_seconds": 300,
    "max_concurrent_tests": 10,
    "test_results_retention_days": 90,
    "enable_parallel_testing": true,
    "fail_fast": false
  }
}
```

### Test Type Configurations
```json
{
  "test_types": {
    "unit": {
      "enabled": true,
      "framework": "pytest",
      "coverage_enabled": true,
      "coverage_threshold_percent": 85,
      "mocking_enabled": true,
      "test_patterns": ["test_*.py", "*_test.py"],
      "execution_order": "sequential"
    },
    "integration": {
      "enabled": true,
      "framework": "pytest",
      "mock_external_services": false,
      "test_patterns": ["integration_test_*.py", "*_integration_test.py"],
      "execution_order": "sequential"
    },
    "system": {
      "enabled": true,
      "framework": "pytest",
      "end_to_end_tests": true,
      "test_patterns": ["system_test_*.py", "*_system_test.py"],
      "execution_order": "sequential"
    },
    "performance": {
      "enabled": true,
      "framework": "custom",
      "load_testing_tool": "locust",
      "stress_testing_enabled": true,
      "benchmark_targets": {
        "response_time_ms": 1000,
        "throughput_tps": 100,
        "error_rate_percent": 1
      }
    },
    "security": {
      "enabled": true,
      "framework": "bandit",
      "static_analysis": true,
      "dynamic_analysis": false,
      "vulnerability_scanning": true,
      "security_check_patterns": ["security_test_*.py", "*_security_test.py"]
    },
    "regression": {
      "enabled": true,
      "framework": "pytest",
      "smoke_tests_only": false,
      "full_regression_suite": true,
      "test_patterns": ["regression_test_*.py", "*_regression_test.py"]
    }
  }
}
```

## Quality Standards Configuration

### Code Quality Standards
```json
{
  "code_quality": {
    "linting": {
      "tool": "flake8",
      "max_line_length": 120,
      "ignore_errors": ["E501", "W503"],
      "enable_pydocstyle": true,
      "pydocstyle_convention": "google"
    },
    "static_analysis": {
      "tool": "pylint",
      "min_public_score": 8.0,
      "enable_mypy": true,
      "mypy_strict": false,
      "type_checking_level": "basic"
    },
    "complexity_analysis": {
      "tool": "radon",
      "cyclomatic_complexity_threshold": 10,
      "maintainability_index_threshold": 20,
      "max_functions_per_module": 20
    },
    "security_analysis": {
      "tool": "bandit",
      "skip_tests": ["B101", "B102"],
      "confidence_threshold": "medium",
      "severity_threshold": "medium"
    }
  }
}
```

### Test Quality Standards
```json
{
  "test_quality": {
    "coverage": {
      "tool": "coverage.py",
      "minimum_threshold_percent": 80,
      "branch_coverage_required": true,
      "report_format": ["html", "xml", "term"],
      "excluded_files": ["*/tests/*", "*/migrations/*", "*/venv/*"]
    },
    "effectiveness": {
      "mutation_testing_enabled": false,
      "mutation_testing_tool": "mutmut",
      "mutation_score_threshold": 60
    },
    "reliability": {
      "flaky_test_detection": true,
      "retry_flaky_tests": 2,
      "max_acceptable_failure_rate": 0.05
    }
  }
}
```

## Quality Gates Configuration

### Quality Gate Criteria
```json
{
  "quality_gates": {
    "entry_criteria": {
      "code_quality_score": 8.0,
      "test_coverage_percent": 80,
      "critical_defects": 0,
      "security_vulnerabilities": 0,
      "build_status": "success"
    },
    "exit_criteria": {
      "test_pass_rate_percent": 95,
      "performance_threshold_met": true,
      "security_scan_passed": true,
      "no_blocker_defects": true
    },
    "deployment_criteria": {
      "all_quality_gates_passed": true,
      "documentation_complete": true,
      "regression_tests_passed": true,
      "performance_benchmarks_met": true
    }
  }
}
```

## Defect Management Configuration

### Defect Tracking
```json
{
  "defect_management": {
    "tracking_system": "jira",
    "jira": {
      "server_url": "https://acme.jira.com",
      "project_key": "QA",
      "username_env_var": "JIRA_USERNAME",
      "api_token_env_var": "JIRA_API_TOKEN",
      "issue_type": "Bug"
    },
    "defect_severity": {
      "blocker": {"criteria": ["security_vulnerability", "system_crash"], "priority": "highest"},
      "critical": {"criteria": ["data_loss", "major_functionality_broken"], "priority": "high"},
      "major": {"criteria": ["minor_functionality_impacted"], "priority": "medium"},
      "minor": {"criteria": ["cosmetic_issues", "documentation_errors"], "priority": "low"}
    },
    "defect_workflow": {
      "new": ["open", "triage"],
      "triage": ["confirmed", "not_a_bug", "duplicate"],
      "confirmed": ["in_progress", "ready_for_dev"],
      "in_progress": ["in_review", "resolved"],
      "in_review": ["approved", "rejected"],
      "resolved": ["verified", "closed"],
      "verified": ["closed"]
    }
  }
}
```

## Performance Testing Configuration

### Performance Benchmarks
```json
{
  "performance_testing": {
    "load_testing": {
      "enabled": true,
      "tool": "locust",
      "max_users": 1000,
      "spawn_rate": 10,
      "test_duration_minutes": 10,
      "target_hosts": ["https://api.example.com"]
    },
    "benchmarks": {
      "response_time_ms": {
        "p95": 500,
        "p99": 1000,
        "average": 200
      },
      "throughput_tps": {
        "minimum": 100,
        "target": 500,
        "maximum": 1000
      },
      "error_rate_percent": {
        "maximum": 1,
        "warning": 0.5
      },
      "resource_utilization": {
        "cpu_percent": 80,
        "memory_percent": 85,
        "disk_io_percent": 90
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
        "tests_executed",
        "test_pass_rate",
        "defect_density",
        "code_coverage",
        "performance_metrics"
      ]
    },
    "health_checks": {
      "test_infrastructure": true,
      "database_connectivity": true,
      "reporting_system": true,
      "quality_gate_status": true
    },
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/quality_assurance.log",
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
        "name": "quality_gate_failure",
        "condition": "quality_gate.status == 'failed'",
        "severity": "high",
        "recipients": ["admin@example.com", "qa-team@example.com"],
        "notification_method": ["email", "slack"]
      },
      {
        "name": "test_failure_rate_high",
        "condition": "test_failure_rate > 0.1",
        "severity": "medium",
        "recipients": ["admin@example.com", "dev-team@example.com"],
        "notification_method": ["email"]
      },
      {
        "name": "performance_degradation",
        "condition": "response_time.average > 1000",
        "severity": "high",
        "recipients": ["admin@example.com", "performance-team@example.com"],
        "notification_method": ["email", "slack"]
      },
      {
        "name": "security_vulnerability_found",
        "condition": "security_scan.vulnerabilities > 0",
        "severity": "critical",
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
        "sender_email": "qa@acme.com"
      },
      "slack": {
        "enabled": true,
        "webhook_url_env_var": "SLACK_WEBHOOK_URL",
        "channel": "#qa-reports"
      },
      "dashboard": {
        "enabled": true,
        "url": "https://dashboard.acme.com/quality"
      }
    },
    "event_triggers": [
      {
        "name": "test_completion",
        "condition": "test.status == 'completed'",
        "recipients": ["qa-team@example.com"],
        "channels": ["email", "dashboard"]
      },
      {
        "name": "defect_created",
        "condition": "defect.status == 'new'",
        "recipients": ["dev-team@example.com"],
        "channels": ["email", "jira"]
      },
      {
        "name": "quality_gate_passed",
        "condition": "quality_gate.status == 'passed'",
        "recipients": ["release-team@example.com"],
        "channels": ["email", "dashboard"]
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
    "testing_optimization": {
      "max_parallel_tests": 10,
      "test_batch_size": 50,
      "test_result_buffer_size": 1000,
      "test_timeout_seconds": 300
    },
    "caching": {
      "enabled": true,
      "test_results_ttl_seconds": 3600,
      "test_artifacts_ttl_seconds": 7200,
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
    "ci_cd": [
      {
        "name": "jenkins",
        "enabled": true,
        "server_url": "https://jenkins.example.com",
        "job_name": "quality-gate-check",
        "username_env_var": "JENKINS_USERNAME",
        "api_token_env_var": "JENKINS_API_TOKEN"
      }
    ],
    "bug_tracking": [
      {
        "name": "jira",
        "enabled": true,
        "server_url": "https://acme.jira.com",
        "project_key": "QA",
        "username_env_var": "JIRA_USERNAME",
        "api_token_env_var": "JIRA_API_TOKEN"
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
    "port": 8088,
    "ssl": {
      "enabled": true,
      "cert_path": "/secure/server.crt",
      "key_path": "/secure/server.key"
    },
    "authentication": {
      "enabled": true,
      "method": "api_key",
      "api_key_env_var": "QA_API_KEY"
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

Create a `qa_config.json` file with your configuration:

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
    "default_test_timeout_seconds": 300,
    "max_concurrent_tests": 10
  },
  "qa": {
    "default_test_timeout_seconds": 300,
    "max_concurrent_tests": 10
  },
  "test_types": {
    "unit": {
      "enabled": true,
      "coverage_threshold_percent": 85
    },
    "integration": {
      "enabled": true
    },
    "performance": {
      "enabled": true,
      "benchmark_targets": {
        "response_time_ms": 1000,
        "throughput_tps": 100
      }
    },
    "security": {
      "enabled": true
    }
  },
  "code_quality": {
    "linting": {
      "tool": "flake8",
      "max_line_length": 120
    },
    "static_analysis": {
      "tool": "pylint",
      "min_public_score": 8.0
    }
  },
  "test_quality": {
    "coverage": {
      "minimum_threshold_percent": 80,
      "branch_coverage_required": true
    }
  },
  "quality_gates": {
    "entry_criteria": {
      "code_quality_score": 8.0,
      "test_coverage_percent": 80
    },
    "exit_criteria": {
      "test_pass_rate_percent": 95
    }
  },
  "monitoring": {
    "enabled": true,
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/quality_assurance.log"
    }
  }
}
```