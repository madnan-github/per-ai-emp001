# Revenue Reporter Skill

## Purpose and Use Cases
The Revenue Reporter skill enables the AI employee to calculate and report weekly/monthly revenue and financial summaries. This skill provides automated financial reporting while maintaining accuracy and consistency in business metrics presentation.

## Input Parameters and Expected Formats
- `period`: Reporting period ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')
- `start_date`: Start date in ISO 8601 format
- `end_date`: End date in ISO 8601 format
- `currency`: Currency code for reporting ('USD', 'EUR', 'GBP', etc.)
- `breakdown`: Level of detail ('summary', 'by_customer', 'by_product', 'by_region')
- `comparison_period`: Optional previous period for comparison

## Processing Logic and Decision Trees
1. **Data Collection**:
   - Gather revenue data from invoices, payments, and transactions
   - Verify data completeness and accuracy
   - Exclude pending or disputed amounts

2. **Calculation Process**:
   - Calculate total revenue for the period
   - Compute growth rates compared to previous periods
   - Segment revenue by requested breakdown criteria

3. **Analysis Process**:
   - Identify top-performing products/customers
   - Highlight significant changes or trends
   - Flag anomalies for review

4. **Report Generation**:
   - Format data according to company standards
   - Generate visual charts if requested
   - Create executive summary with key insights

## Output Formats and File Structures
- Creates revenue reports in /Reports/revenue_[period]_[date].md
- Generates CSV exports in /Exports/revenue_[period]_[date].csv
- Updates Dashboard.md with current revenue metrics
- Maintains historical data in /Data/revenue_history.db

## Error Handling Procedures
- Retry failed data queries with exponential backoff
- Generate partial reports if some data sources unavailable
- Alert if revenue figures deviate significantly from expectations
- Log calculation errors to /Logs/revenue_errors.log

## Security Considerations
- Restrict access to revenue data based on role permissions
- Encrypt sensitive financial information in reports
- Maintain audit trail of all revenue calculations
- Secure deletion of temporary report files

## Integration Points with Other System Components
- Pulls data from Invoice Generator and Bank Transaction Monitor
- Updates Dashboard Updater with revenue metrics
- Alerts Anomaly Detector for unusual revenue patterns
- Provides data to Weekly Business Briefing skill