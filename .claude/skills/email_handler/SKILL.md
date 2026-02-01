# Email Handler Skill

## Purpose and Use Cases
The Email Handler skill enables the AI employee to read, categorize, respond to, and draft emails based on priority and predefined rules. This skill allows for autonomous email management while maintaining human oversight for sensitive communications.

## Input Parameters and Expected Formats
- `action`: Type of email operation ('read', 'categorize', 'respond', 'draft', 'send')
- `priority`: Priority level ('low', 'medium', 'high', 'critical')
- `sender`: Email address of sender (for filtering)
- `subject`: Subject line for new emails or search criteria
- `body`: Email content for responses or drafts
- `attachments`: Array of file paths to attach (optional)
- `folder`: Gmail folder to operate on (e.g., 'inbox', 'sent', 'drafts')

## Processing Logic and Decision Trees
1. **Read Operation**:
   - Fetch unread emails from specified folder
   - Apply filters based on sender, subject, or priority
   - Categorize emails based on predefined rules in Company_Handbook.md

2. **Categorize Operation**:
   - Match email content against business rules
   - Assign categories: 'needs_response', 'informational', 'spam', 'urgent'
   - Flag emails requiring human approval

3. **Response Operation**:
   - Use templates from /reference/email_templates/
   - Apply personalization based on sender relationship
   - Route high-priority emails to /Pending_Approval/

4. **Draft Operation**:
   - Generate drafts based on context and requirements
   - Save to drafts folder for review
   - Create approval request if content is sensitive

## Output Formats and File Structures
- Creates email activity logs in /Logs/email_activity_[date].log
- Generates approval requests in /Pending_Approval/email_[timestamp].md
- Updates Dashboard.md with email statistics
- Saves drafts to Gmail drafts folder

## Error Handling Procedures
- Retry failed operations with exponential backoff
- Log authentication failures to /Logs/auth_failures.log
- Fallback to manual processing if API limits reached
- Send alert if email service unavailable for >30 minutes

## Security Considerations
- All email credentials stored in environment variables
- Sensitive content requires approval before sending
- Comprehensive audit trail for all email actions
- Rate limiting to prevent API abuse

## Integration Points with Other System Components
- Triggers Gmail Watcher when urgent emails detected
- Updates Dashboard Updater with email metrics
- Creates action files in /Needs_Action for follow-up tasks
- Integrates with Approval Processor for sensitive communications