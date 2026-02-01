# Status Reporter Skill

## Purpose and Use Cases
The Status Reporter skill enables the AI employee to generate regular status reports and briefings for stakeholders. This skill provides consistent, comprehensive updates on business operations, project progress, and key metrics while maintaining standardized reporting formats.

## Input Parameters and Expected Formats
- `report_type`: Type of report ('daily', 'weekly', 'monthly', 'executive', 'ad_hoc')
- `recipients`: List of recipient identifiers for the report
- `metrics`: Array of specific metrics to include
- `time_period`: Time period covered by the report (start and end dates)
- `granularity`: Level of detail ('summary', 'detailed', 'executive')
- `focus_areas`: Specific areas to emphasize in the report
- `alert_thresholds`: Thresholds for highlighting concerns

## Processing Logic and Decision Trees
1. **Data Collection**:
   - Gather metrics from various system components
   - Validate data completeness and accuracy
   - Compile information from different sources

2. **Analysis Process**:
   - Calculate key performance indicators
   - Identify trends and significant changes
   - Compare against targets and benchmarks

3. **Formatting Process**:
   - Apply appropriate template based on report type
   - Highlight important findings and concerns
   - Organize information logically

4. **Distribution Process**:
   - Format report for specified recipients
   - Deliver via appropriate channels
   - Track report delivery and engagement

## Output Formats and File Structures
- Creates status reports in /Reports/status_[type]_[date].md
- Generates executive summaries in /Reports/exec_summary_[date].md
- Creates distribution logs in /Logs/report_delivery_[date].log
- Updates Dashboard.md with latest status metrics

## Error Handling Procedures
- Retry failed report generation if data sources unavailable
- Generate partial reports if some metrics unavailable
- Alert if report delivery fails
- Log generation errors to /Logs/status_report_errors.log

## Security Considerations
- Implement role-based access controls for different report types
- Encrypt sensitive information in reports
- Maintain audit trail of report generation and distribution
- Secure delivery channels for confidential reports

## Integration Points with Other System Components
- Pulls data from all other system components (Project Tracker, Revenue Reporter, etc.)
- Updates Dashboard Updater with status metrics
- Connects with Communication Logger for delivery tracking
- Creates action files in /Needs_Action for issues requiring attention