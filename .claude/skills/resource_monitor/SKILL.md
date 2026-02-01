# Resource Monitor Skill

## Purpose and Use Cases
The Resource Monitor skill provides continuous monitoring and management of system resources for the Personal AI Employee system. It tracks CPU, memory, disk, network, and other resource utilization, provides alerts when thresholds are exceeded, and enables proactive resource management to maintain system performance and availability.

## Input Parameters and Expected Formats
- `metric_type`: Type of resource metric ('cpu', 'memory', 'disk', 'network', 'process', 'temperature')
- `resource_id`: Identifier for the specific resource being monitored (string)
- `threshold_value`: Threshold value for alerts (numeric)
- `comparison_operator`: How to compare ('gt', 'lt', 'eq', 'gte', 'lte')
- `monitoring_interval`: How often to check (seconds, integer)
- `alert_recipients`: Who to notify when threshold exceeded (list of email addresses)
- `aggregation_window`: Time window for metric aggregation (seconds, integer)
- `tags`: Additional metadata for resource identification (dictionary)

## Processing Logic and Decision Trees
1. **Resource Discovery**:
   - Identify system resources to monitor
   - Discover running processes and services
   - Detect resource dependencies and relationships
   - Catalog resource capabilities

2. **Continuous Monitoring**:
   - Collect resource metrics at specified intervals
   - Aggregate metrics over configured windows
   - Calculate derived metrics (rates, percentages, trends)
   - Store historical metric data

3. **Threshold Detection**:
   - Compare metrics against configured thresholds
   - Identify sustained threshold violations
   - Correlate related resource usage patterns
   - Classify alert severity levels

4. **Alert Management**:
   - Generate alerts for threshold violations
   - Deduplicate redundant alerts
   - Route alerts to appropriate recipients
   - Track alert resolution status

5. **Resource Optimization**:
   - Analyze resource usage patterns
   - Identify optimization opportunities
   - Recommend resource allocation adjustments
   - Automate resource scaling decisions

## Output Formats and File Structures
- Writes resource metrics to /Data/resource_metrics.db
- Generates alert notifications in /Alerts/alert_[timestamp].txt
- Creates monitoring reports in /Reports/resource_usage_[date].md
- Updates Dashboard.md with resource utilization metrics
- Logs monitoring activity in /Logs/resource_monitor_[date].log

## Error Handling Procedures
- Retry failed metric collection operations
- Alert when monitoring service is unavailable
- Implement circuit breaker for overloaded monitors
- Log monitoring errors to /Logs/monitoring_errors.log
- Route critical monitoring failures to /Pending_Approval/ for manual intervention

## Security Considerations
- Sanitize all metric data to prevent injection
- Implement access controls for monitoring data
- Maintain detailed audit trail of all monitoring activities
- Encrypt sensitive metric data at rest
- Secure monitoring configuration and credentials

## Integration Points with Other System Components
- Integrates with all other skills for resource monitoring
- Connects with Error Handler for monitoring-related errors
- Updates Dashboard Updater with resource metrics
- Creates audit logs for Communication Logger
- Coordinates with Scheduler for resource-intensive tasks