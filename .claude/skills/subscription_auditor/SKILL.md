# Subscription Auditor Skill

## Purpose and Use Cases
The Subscription Auditor skill enables the AI employee to monitor business subscriptions, identify unused services, and suggest optimizations. This skill helps reduce costs by identifying redundant or underutilized subscriptions while ensuring critical services remain active.

## Input Parameters and Expected Formats
- `service_types`: Array of service categories to audit ('cloud', 'software', 'utilities', 'tools')
- `audit_frequency`: How often to audit ('daily', 'weekly', 'monthly')
- `usage_threshold`: Minimum usage percentage to consider subscription active
- `cost_threshold`: Minimum monthly cost to prioritize for review
- `business_critical`: List of services deemed essential regardless of usage
- `department_filter`: Optional department to focus audit on

## Processing Logic and Decision Trees
1. **Discovery Process**:
   - Scan company accounts for active subscriptions
   - Gather usage data from service APIs
   - Collect cost information from billing records

2. **Analysis Process**:
   - Compare usage against defined thresholds
   - Identify subscriptions with low utilization
   - Check for overlapping services performing same function

3. **Recommendation Process**:
   - Prioritize recommendations by cost savings potential
   - Flag business-critical services that shouldn't be canceled
   - Suggest alternative services if appropriate

4. **Approval Process**:
   - Route high-value cancellation recommendations to /Pending_Approval/
   - Auto-cancel subscriptions below certain value threshold
   - Notify stakeholders of recommended changes

## Output Formats and File Structures
- Creates subscription audits in /Reports/subscriptions_[date].md
- Generates approval requests in /Pending_Approval/subscription_[timestamp].md for high-value cancellations
- Updates Dashboard.md with subscription cost metrics
- Maintains subscription database in /Data/subscriptions.db

## Error Handling Procedures
- Retry failed API calls to service providers with exponential backoff
- Queue audit tasks for manual review if authentication fails
- Alert if critical service shows zero usage (possible outage)
- Log access errors to /Logs/subscription_audit_errors.log

## Security Considerations
- Store subscription API credentials securely in environment variables
- Implement approval workflow for all cancellation recommendations
- Maintain audit trail of all subscription changes
- Encrypt sensitive billing information in storage

## Integration Points with Other System Components
- Integrates with Approval Processor for cancellation recommendations
- Connects with Expense Tracker to identify subscription costs
- Updates Dashboard Updater with cost optimization metrics
- Creates action files in /Needs_Action for service migrations