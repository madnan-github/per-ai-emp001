# Weekly Business Briefing Skill

## Purpose and Use Cases
The Weekly Business Briefing skill generates CEO-style briefings with revenue, bottlenecks, and suggestions for business improvement. This skill provides comprehensive executive summaries that synthesize information from multiple business systems into actionable insights.

## Input Parameters and Expected Formats
- `reporting_period`: Time period for the briefing ('weekly', 'bi_weekly', 'monthly')
- `executive_level`: Target audience ('c_suite', 'department_head', 'manager')
- `key_metrics`: Array of specific metrics to highlight
- `comparison_period`: Period for comparison ('previous_week', 'previous_month', 'same_period_last_year')
- `focus_areas`: Business areas to emphasize in the briefing
- `sensitivity_filter`: Filter for information sensitivity level
- `visualization_preference`: Preferred visualization types ('charts', 'tables', 'narrative')

## Processing Logic and Decision Trees
1. **Data Aggregation**:
   - Collect key metrics from all business systems
   - Validate data accuracy and completeness
   - Calculate period-over-period changes

2. **Analysis Process**:
   - Identify significant changes and trends
   - Analyze bottlenecks and performance gaps
   - Assess achievement against targets

3. **Insight Generation**:
   - Synthesize data into meaningful insights
   - Identify root causes for performance changes
   - Generate actionable recommendations

4. **Briefing Assembly**:
   - Organize information by business priority
   - Create executive summary with key highlights
   - Format for target audience

## Output Formats and File Structures
- Creates executive briefings in /Reports/briefing_[period]_[date].md
- Generates supporting data in /Data/briefing_data_[date].csv
- Creates dashboard summaries in /Dashboards/briefing_[date].md
- Updates Dashboard.md with briefing highlights

## Error Handling Procedures
- Retry failed data collection if sources temporarily unavailable
- Generate partial briefings if some metrics unavailable
- Alert if significant data quality issues detected
- Log briefing generation errors to /Logs/briefing_errors.log

## Security Considerations
- Implement role-based access controls for briefing content
- Encrypt sensitive business information in reports
- Maintain audit trail of briefing generation and distribution
- Secure executive-level briefings with enhanced access controls

## Integration Points with Other System Components
- Pulls data from all business systems (Revenue Reporter, Project Tracker, etc.)
- Updates Dashboard Updater with briefing metrics
- Connects with Communication Logger for distribution tracking
- Creates action files in /Needs_Action for recommendations