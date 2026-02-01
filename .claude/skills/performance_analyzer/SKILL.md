# Performance Analyzer Skill

## Purpose and Use Cases
The Performance Analyzer skill analyzes task completion times and identifies inefficiencies in business operations. This skill provides data-driven insights into productivity, resource utilization, and process optimization opportunities across all business activities.

## Input Parameters and Expected Formats
- `analysis_scope`: Scope of analysis ('individual_task', 'process_workflow', 'department', 'organization')
- `time_period`: Time range for analysis (start and end dates)
- `performance_metrics`: Array of metrics to analyze ('cycle_time', 'throughput', 'quality', 'resource_utilization')
- `benchmark_reference`: Baseline for comparison ('historical_average', 'industry_standard', 'target_metric')
- `efficiency_thresholds`: Thresholds for identifying inefficiencies
- `resource_allocation`: Information about resource distribution
- `process_constraints`: Known limitations affecting performance

## Processing Logic and Decision Trees
1. **Data Collection**:
   - Gather performance data from relevant systems
   - Validate data accuracy and completeness
   - Normalize metrics for comparison

2. **Performance Analysis**:
   - Calculate key performance indicators
   - Compare against benchmarks and targets
   - Identify outliers and anomalies

3. **Efficiency Assessment**:
   - Analyze resource utilization patterns
   - Identify bottlenecks and delays
   - Calculate efficiency ratios

4. **Recommendation Process**:
   - Generate optimization recommendations
   - Prioritize improvements by impact potential
   - Estimate resource requirements for improvements

## Output Formats and File Structures
- Creates performance reports in /Reports/performance_[scope]_[date].md
- Maintains performance metrics in /Data/performance.db
- Generates optimization recommendations in /Recommendations/performance_[date].md
- Updates Dashboard.md with performance metrics and trends

## Error Handling Procedures
- Retry failed metric calculations if data sources unavailable
- Generate partial analyses if some metrics unavailable
- Alert if significant performance degradation detected
- Log analysis errors to /Logs/performance_analysis_errors.log

## Security Considerations
- Implement access controls for sensitive performance data
- Encrypt confidential performance information
- Maintain audit trail of all analysis activities
- Secure performance benchmark data

## Integration Points with Other System Components
- Pulls data from Task Scheduler and Project Tracker
- Updates Dashboard Updater with performance metrics
- Connects with Process Optimization components
- Creates action files in /Needs_Action for improvements