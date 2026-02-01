# Gmail Watcher Skill

## Purpose and Use Cases
The Gmail Watcher skill enables the AI employee to monitor Gmail for important messages, flag urgent items, and trigger appropriate responses. This skill provides continuous email monitoring while identifying critical communications that require immediate attention or action.

## Input Parameters and Expected Formats
- `watch_folders`: Array of Gmail folders to monitor ('inbox', 'important', 'unread')
- `keywords`: Array of keywords to trigger alerts for
- `sender_filters`: Array of sender addresses or domains to prioritize
- `importance_threshold`: Minimum importance level to flag ('low', 'medium', 'high', 'critical')
- `notification_channels`: Array of channels for alerts ('dashboard', 'email', 'slack', 'sms')
- `business_hours`: Time window for normal processing vs urgent handling
- `escalation_rules`: Conditions for escalating to human operator

## Processing Logic and Decision Trees
1. **Monitoring Process**:
   - Continuously poll Gmail API for new messages
   - Apply filters based on sender, subject, and content
   - Categorize messages by urgency and importance

2. **Classification Process**:
   - Identify urgent messages requiring immediate attention
   - Flag important messages for processing
   - Route routine messages for batch processing

3. **Action Process**:
   - Create action files in /Needs_Action for important emails
   - Trigger automated responses for recognized patterns
   - Escalate critical messages to /Pending_Approval/

4. **Notification Process**:
   - Send alerts through specified channels
   - Update dashboard with urgent items
   - Log all triggered actions

## Output Formats and File Structures
- Creates watcher logs in /Logs/gmail_watcher_[date].log
- Generates action files in /Needs_Action for important emails
- Creates escalation requests in /Pending_Approval/gmail_[timestamp].md
- Updates Dashboard.md with email status and alerts

## Error Handling Procedures
- Retry failed API connections with exponential backoff
- Switch to backup monitoring method if primary fails
- Alert if Gmail API quota exceeded
- Log authentication failures to /Logs/gmail_auth_failures.log

## Security Considerations
- Store Gmail API credentials securely in environment variables
- Encrypt sensitive email content in logs
- Implement rate limiting to respect API quotas
- Maintain audit trail of all email interactions

## Integration Points with Other System Components
- Creates action files in /Needs_Action for Email Handler skill
- Updates Dashboard Updater with email alerts
- Integrates with Approval Processor for critical emails
- Connects with Communication Logger for audit trail