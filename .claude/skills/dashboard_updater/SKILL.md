# Dashboard Updater Skill

## Purpose and Use Cases
The Dashboard Updater skill maintains real-time dashboard with key business metrics. This skill aggregates data from all system components to provide a centralized, up-to-date view of business operations, performance indicators, and critical alerts for effective management oversight.

## Input Parameters and Expected Formats
- `dashboard_type`: Type of dashboard to update ('executive', 'operational', 'financial', 'project')
- `refresh_interval`: Frequency of dashboard updates ('real_time', 'minute', 'hour', 'day')
- `metric_categories`: Array of metric categories to include
- `data_sources`: List of system components to collect data from
- `visualization_types`: Preferred chart and graph types for metrics
- `alert_thresholds`: Thresholds for highlighting critical metrics
- `access_permissions`: User permissions for dashboard access

## Processing Logic and Decision Trees
1. **Data Collection**:
   - Gather metrics from all connected system components
   - Validate data freshness and accuracy
   - Aggregate data by required time periods

2. **Metric Calculation**:
   - Calculate derived metrics and KPIs
   - Apply business logic for composite indicators
   - Perform trend calculations if required

3. **Dashboard Assembly**:
   - Format data according to dashboard template
   - Apply visual styling and conditional formatting
   - Insert real-time data into dashboard structure

4. **Update Process**:
   - Update dashboard file atomically
   - Maintain historical data snapshots
   - Notify subscribers of significant changes

## Output Formats and File Structures
- Updates Dashboard.md with current metrics
- Creates dashboard snapshots in /Dashboards/history_[timestamp].md
- Maintains dashboard configuration in /Config/dashboard_config.json
- Generates dashboard change logs in /Logs/dashboard_updates_[date].log

## Error Handling Procedures
- Retry failed data collection from system components
- Display cached data if real-time data unavailable
- Alert if dashboard update fails repeatedly
- Log update failures to /Logs/dashboard_errors.log

## Security Considerations
- Implement role-based access controls for dashboard content
- Encrypt sensitive metrics in dashboard files
- Maintain audit trail of dashboard access and updates
- Secure dashboard configuration and data sources

## Integration Points with Other System Components
- Pulls data from all system components (Revenue Reporter, Project Tracker, etc.)
- Integrates with Communication Logger for dashboard notifications
- Updates Dashboard.md with all system metrics
- Creates action files in /Needs_Action for dashboard alerts