# Expense Tracker Skill

## Purpose and Use Cases
The Expense Tracker skill enables the AI employee to monitor and categorize business expenses, flag unusual spending patterns, and generate expense reports. This skill provides automated expense management while maintaining compliance with company spending policies.

## Input Parameters and Expected Formats
- `amount`: Expense amount as decimal number
- `currency`: Currency code ('USD', 'EUR', 'GBP', etc.)
- `category`: Expense category ('travel', 'meals', 'office', 'software', 'marketing')
- `vendor`: Vendor or merchant name
- `receipt_image`: Path to receipt image file (optional)
- `description`: Description of expense
- `date`: Date of expense in ISO 8601 format
- `payment_method`: Method of payment ('credit_card', 'debit', 'cash', 'bank_transfer')
- `project_code`: Associated project code for allocation

## Processing Logic and Decision Trees
1. **Expense Validation**:
   - Verify expense amount is within reasonable range
   - Check receipt presence if required by policy
   - Validate category against approved list

2. **Categorization Process**:
   - Auto-categorize based on vendor and description
   - Apply business rules for category assignment
   - Flag unusual categories for review

3. **Policy Compliance**:
   - Check expense against spending limits
   - Validate approval requirements
   - Flag policy violations for approval

4. **Reporting Process**:
   - Aggregate expenses by category and period
   - Generate monthly expense reports
   - Alert for budget overruns

## Output Formats and File Structures
- Records expenses in /Data/expenses.db
- Creates monthly expense reports in /Reports/expenses_[month].md
- Generates approval requests in /Pending_Approval/expense_[timestamp].md for policy violations
- Updates Dashboard.md with expense metrics and trends

## Error Handling Procedures
- Retry failed database writes with exponential backoff
- Queue expenses for manual review if validation fails
- Alert if receipt required but not provided
- Log policy violations to /Logs/expenses_violations.log

## Security Considerations
- Encrypt sensitive financial data in storage
- Implement approval workflow for policy exceptions
- Maintain audit trail of all expense entries
- Secure access to expense data based on roles

## Integration Points with Other System Components
- Integrates with Approval Processor for policy violations
- Connects with Bank Transaction Monitor to reconcile expenses
- Updates Dashboard Updater with spending metrics
- Creates action files in /Needs_Action for budget reviews