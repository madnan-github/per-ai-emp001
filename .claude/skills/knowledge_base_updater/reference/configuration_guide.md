# Knowledge Base Updater Configuration Guide

## Overview
This guide provides comprehensive configuration instructions for the Knowledge Base Updater skill, which provides automated updating and maintenance of the knowledge base for the Personal AI Employee system.

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Required Python packages:
  - beautifulsoup4 (for web scraping)
  - requests (for HTTP requests)
  - PyPDF2 (for PDF processing)
  - python-docx (for Word documents)
  - lxml (for XML processing)
  - whoosh (for search indexing)
  - spacy (for NLP processing)
  - schedule (for scheduling)

### Environment Variables
Set these environment variables for secure configuration:

```
KNOWLEDGE_BASE_UPDATER_DATABASE_PATH=/data/knowledge_graph.db
KNOWLEDGE_BASE_UPDATER_LOG_LEVEL=INFO
KNOWLEDGE_BASE_UPDATER_SOURCE_CONNECTION_TIMEOUT=30
KNOWLEDGE_BASE_UPDATER_QUALITY_THRESHOLD=75
KNOWLEDGE_BASE_UPDATER_UPDATE_BATCH_SIZE=100
KNOWLEDGE_BASE_UPDATER_MAX_CONTENT_SIZE_KB=10240
KNOWLEDGE_BASE_UPDATER_INDEX_PATH=/indexes/knowledge_index/
KNOWLEDGE_BASE_UPDATER_NLP_MODEL=en_core_web_sm
```

## Knowledge Base Configuration

### Basic Settings
```json
{
  "knowledge_base": {
    "storage_path": "/knowledge_base/",
    "index_path": "/indexes/",
    "backup_path": "/backups/knowledge/",
    "max_size_mb": 1024,
    "retention_days": 90,
    "compression_enabled": true
  }
}
```

### Source Configuration
```json
{
  "sources": {
    "web_pages": {
      "enabled": true,
      "allowed_domains": ["*.example.com", "docs.example.com"],
      "max_depth": 3,
      "rate_limit_requests_per_minute": 10,
      "user_agent": "Knowledge-Updater/1.0"
    },
    "documents": {
      "enabled": true,
      "supported_formats": [".pdf", ".docx", ".txt", ".md", ".html"],
      "max_file_size_mb": 10,
      "storage_path": "/incoming_documents/"
    },
    "apis": {
      "enabled": true,
      "rate_limit_requests_per_minute": 60,
      "timeout_seconds": 30,
      "retry_attempts": 3
    },
    "databases": {
      "enabled": true,
      "supported_types": ["sqlite", "postgresql", "mysql"],
      "max_connections": 10,
      "connection_timeout_seconds": 30
    }
  }
}
```

## Content Processing Configuration

### Parsing Settings
```json
{
  "parsing": {
    "pdf": {
      "extract_images": false,
      "extract_tables": true,
      "encoding": "utf-8"
    },
    "word": {
      "extract_tables": true,
      "preserve_formatting": false,
      "encoding": "utf-8"
    },
    "html": {
      "remove_tags": ["script", "style", "nav", "aside"],
      "extract_links": true,
      "encoding": "utf-8"
    },
    "text": {
      "encoding": "utf-8",
      "line_separator": "\n"
    }
  }
}
```

### Natural Language Processing
```json
{
  "nlp": {
    "model": "en_core_web_sm",
    "named_entity_recognition": true,
    "part_of_speech_tagging": true,
    "dependency_parsing": true,
    "language_detection": true,
    "text_summarization": {
      "enabled": true,
      "method": "extractive",
      "summary_ratio": 0.3
    }
  }
}
```

## Quality Assessment Configuration

### Validation Rules
```json
{
  "validation": {
    "content_quality": {
      "minimum_word_count": 50,
      "maximum_word_count": 10000,
      "minimum_readability_score": 30,
      "required_entities": [],
      "forbidden_entities": ["malware", "virus", "scam"]
    },
    "source_credibility": {
      "whitelist_domains": ["gov", "edu", "org", "example.com"],
      "blacklist_domains": ["spam", "scam", "fake-news"],
      "authority_score_threshold": 0.7,
      "historical_accuracy_weight": 0.3
    },
    "fact_checking": {
      "enabled": true,
      "providers": ["snopes", "politifact"],
      "cross_reference_sources": 3,
      "confidence_threshold": 0.8
    }
  }
}
```

### Quality Thresholds
```json
{
  "quality_thresholds": {
    "overall_score": 75,
    "accuracy": 80,
    "relevance": 70,
    "timeliness": 60,
    "completeness": 75
  }
}
```

## Integration Configuration

### Knowledge Graph Settings
```json
{
  "knowledge_graph": {
    "enabled": true,
    "storage_type": "graph_database",  // graph_database, triple_store, or in_memory
    "graph_database": {
      "type": "neo4j",  // neo4j, amazon_neptune, or arango
      "url": "bolt://localhost:7687",
      "username_env_var": "GRAPH_DB_USERNAME",
      "password_env_var": "GRAPH_DB_PASSWORD"
    },
    "entity_types": [
      "person", "organization", "location", "concept", "event", "product"
    ],
    "relationship_types": [
      "is-a", "part-of", "located-in", "works-for", "caused-by"
    ]
  }
}
```

### Search Index Configuration
```json
{
  "search_index": {
    "engine": "whoosh",  // whoosh, elasticsearch, or opensearch
    "whoosh": {
      "path": "/indexes/knowledge_whoosh/",
      "stored_fields": ["content", "title", "tags", "entities"],
      "indexed_fields": ["content", "title", "tags", "entities"]
    },
    "elasticsearch": {
      "hosts": ["http://localhost:9200"],
      "index_name": "knowledge_base",
      "username_env_var": "ES_USERNAME",
      "password_env_var": "ES_PASSWORD"
    },
    "optimization": {
      "merge_segments": true,
      "optimize_frequency": "daily",
      "ram_buffer_size_mb": 128
    }
  }
}
```

## Update Strategy Configuration

### Update Frequency
```json
{
  "update_frequency": {
    "real_time": {
      "enabled": false,
      "max_processing_time_seconds": 10
    },
    "frequent": {
      "enabled": true,
      "interval_minutes": 15,
      "batch_size": 10
    },
    "daily": {
      "enabled": true,
      "time": "02:00",
      "timezone": "UTC",
      "batch_size": 100
    },
    "weekly": {
      "enabled": true,
      "day": "sunday",
      "time": "03:00",
      "timezone": "UTC",
      "batch_size": 1000
    }
  }
}
```

### Integration Strategies
```json
{
  "integration_strategies": {
    "append": {
      "enabled": true,
      "duplicate_detection": true,
      "similarity_threshold": 0.9
    },
    "merge": {
      "enabled": true,
      "conflict_resolution": "newer_wins",
      "merging_algorithm": "semantic_similarity"
    },
    "replace": {
      "enabled": true,
      "validation_required": true,
      "backup_before_replace": true
    },
    "enrich": {
      "enabled": true,
      "entity_extraction": true,
      "relationship_mapping": true,
      "context_enrichment": true
    }
  }
}
```

## Security and Privacy Configuration

### Content Security
```json
{
  "security": {
    "content_scanning": {
      "enabled": true,
      "malware_scanner": "clamav",
      "scan_attachments": true,
      "quarantine_suspicious": true
    },
    "injection_prevention": {
      "enabled": true,
      "sanitization_level": "aggressive",
      "allowed_tags": ["p", "br", "strong", "em", "ul", "ol", "li"],
      "allowed_attributes": ["href", "title"]
    },
    "privacy_protection": {
      "enabled": true,
      "pii_detection": {
        "enabled": true,
        "detected_types": ["ssn", "credit_card", "email", "phone"],
        "action": "mask"
      },
      "data_minimization": {
        "enabled": true,
        "retention_policy": "automated"
      }
    }
  }
}
```

### Access Control
```json
{
  "access_control": {
    "rbac_enabled": true,
    "roles": [
      {
        "name": "knowledge_admin",
        "permissions": [
          "update_knowledge",
          "manage_sources",
          "configure_system",
          "view_all_content"
        ]
      },
      {
        "name": "knowledge_editor",
        "permissions": [
          "suggest_updates",
          "tag_content",
          "flag_issues"
        ]
      },
      {
        "name": "knowledge_reader",
        "permissions": [
          "search_knowledge",
          "view_content"
        ]
      }
    ]
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
        "content_ingested",
        "quality_scores",
        "update_success_rate",
        "search_performance",
        "system_resources"
      ]
    },
    "health_checks": {
      "knowledge_base_connectivity": true,
      "source_connectivity": true,
      "search_index_health": true,
      "nlp_service_health": true
    },
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/knowledge_base_updater.log",
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
        "name": "low_quality_content",
        "condition": "average_quality_score < 70",
        "severity": "high",
        "recipients": ["admin@example.com", "knowledge-team@example.com"],
        "notification_method": ["email", "slack"]
      },
      {
        "name": "source_failure",
        "condition": "source_error_rate > 0.1",
        "severity": "medium",
        "recipients": ["admin@example.com"],
        "notification_method": ["email"]
      },
      {
        "name": "knowledge_base_full",
        "condition": "storage_utilization > 0.9",
        "severity": "critical",
        "recipients": ["admin@example.com", "ops@example.com"],
        "notification_method": ["email", "sms"]
      },
      {
        "name": "security_violation",
        "condition": "security_incidents > 0",
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
        "sender_email": "knowledge@acme.com"
      },
      "slack": {
        "enabled": true,
        "webhook_url_env_var": "SLACK_WEBHOOK_URL",
        "channel": "#knowledge-updates"
      },
      "dashboard": {
        "enabled": true,
        "url": "https://dashboard.acme.com/knowledge"
      }
    },
    "event_triggers": [
      {
        "name": "content_updated",
        "condition": "update_status == 'success'",
        "recipients": ["knowledge-team@example.com"],
        "channels": ["email", "dashboard"]
      },
      {
        "name": "update_failed",
        "condition": "update_status == 'failed'",
        "recipients": ["admin@example.com"],
        "channels": ["email", "slack"]
      },
      {
        "name": "quality_issue",
        "condition": "quality_score < threshold",
        "recipients": ["quality-team@example.com"],
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
      "cpu_percentage": 70,
      "memory_percentage": 50,
      "disk_io_percentage": 60,
      "network_bandwidth_limit_mbps": 100
    },
    "threading": {
      "parsing_threads": 4,
      "validation_threads": 2,
      "indexing_threads": 3
    },
    "caching": {
      "enabled": true,
      "backend": "redis",
      "ttl_seconds": 3600,
      "max_entries": 10000
    }
  }
}
```

## Integration Configuration

### External System Integration
```json
{
  "integrations": {
    "nlp_services": [
      {
        "name": "spacy",
        "enabled": true,
        "model": "en_core_web_sm"
      },
      {
        "name": "openai",
        "enabled": false,
        "api_key_env_var": "OPENAI_API_KEY",
        "model": "text-embedding-ada-002"
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
    "port": 8086,
    "ssl": {
      "enabled": true,
      "cert_path": "/secure/server.crt",
      "key_path": "/secure/server.key"
    },
    "authentication": {
      "enabled": true,
      "method": "api_key",
      "api_key_env_var": "KNOWLEDGE_API_KEY"
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

Create a `knowledge_config.json` file with your configuration:

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
    "quality_threshold": 75,
    "max_content_size_kb": 10240
  },
  "knowledge_base": {
    "storage_path": "/knowledge_base/",
    "index_path": "/indexes/",
    "max_size_mb": 1024
  },
  "sources": {
    "web_pages": {
      "enabled": true,
      "allowed_domains": ["*.example.com"],
      "rate_limit_requests_per_minute": 10
    },
    "documents": {
      "enabled": true,
      "supported_formats": [".pdf", ".docx", ".txt", ".md"]
    }
  },
  "validation": {
    "content_quality": {
      "minimum_word_count": 50,
      "maximum_word_count": 10000
    },
    "source_credibility": {
      "whitelist_domains": ["gov", "edu", "org"],
      "authority_score_threshold": 0.7
    }
  },
  "search_index": {
    "engine": "whoosh",
    "whoosh": {
      "path": "/indexes/knowledge_whoosh/"
    }
  },
  "update_frequency": {
    "daily": {
      "enabled": true,
      "time": "02:00",
      "batch_size": 100
    }
  },
  "monitoring": {
    "enabled": true,
    "logging": {
      "level": "INFO",
      "file_path": "/var/log/knowledge_base_updater.log"
    }
  }
}
```