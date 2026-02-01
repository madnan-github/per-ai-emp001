# WhatsApp Manager Skill

## Purpose and Use Cases
The WhatsApp Manager skill enables the AI employee to monitor WhatsApp for specific keywords, respond appropriately to predefined triggers, and escalate urgent matters to human operators. This skill facilitates automated customer communication while maintaining appropriate oversight for sensitive conversations.

## Input Parameters and Expected Formats
- `action`: Type of operation ('monitor', 'respond', 'escalate', 'search')
- `keywords`: Array of keywords to monitor for in messages
- `contact`: Specific contact or group to interact with
- `message`: Message content to send or search for
- `response_template`: Template name to use for responses
- `priority_threshold`: Minimum priority level to trigger escalation ('low', 'medium', 'high', 'critical')

## Processing Logic and Decision Trees
1. **Monitor Operation**:
   - Continuously watch WhatsApp Web for new messages
   - Apply keyword filters to identify relevant conversations
   - Categorize messages by urgency and topic

2. **Response Operation**:
   - Match incoming message to appropriate response template
   - Personalize response based on contact history
   - Send response if confidence level is high enough

3. **Escalation Operation**:
   - Flag messages containing escalation keywords
   - Create action file in /Pending_Approval/ for human review
   - Notify human operator via preferred channel

4. **Search Operation**:
   - Search chat history for specific terms or contacts
   - Retrieve relevant conversation context
   - Summarize findings for decision making

## Output Formats and File Structures
- Creates WhatsApp activity logs in /Logs/whatsapp_activity_[date].log
- Generates escalation requests in /Pending_Approval/whatsapp_[timestamp].md
- Updates Dashboard.md with communication metrics
- Maintains contact interaction history in /Data/contacts/

## Error Handling Procedures
- Retry failed message sends with exponential backoff
- Log authentication failures to /Logs/auth_failures.log
- Switch to alternative communication channel if WhatsApp unavailable
- Send alert if WhatsApp Web session expires

## Security Considerations
- Store WhatsApp authentication tokens securely in environment variables
- Encrypt sensitive conversation data
- Implement rate limiting to avoid being flagged by WhatsApp
- Require approval for business-critical communications

## Integration Points with Other System Components
- Triggers communication logger for all WhatsApp interactions
- Creates action files in /Needs_Action for follow-up tasks
- Integrates with Approval Processor for sensitive communications
- Updates Dashboard Updater with communication metrics