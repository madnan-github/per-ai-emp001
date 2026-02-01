# Communication Router Skill

## Purpose and Use Cases
The Communication Router skill provides intelligent routing and management of communication flows for the Personal AI Employee system. It handles incoming and outgoing messages, routes them to appropriate destinations based on content, context, and rules, and manages various communication channels including email, SMS, chat, and API endpoints. This skill ensures efficient and contextually appropriate communication handling.

## Input Parameters and Expected Formats
- `message_id`: Unique identifier for the message (string)
- `source_channel`: Origin of the message ('email', 'sms', 'chat', 'api', 'internal')
- `destination_channel`: Target for routing ('email', 'sms', 'chat', 'api', 'skill')
- `message_content`: The actual message content (string)
- `message_type`: Type of message ('text', 'image', 'document', 'structured_data')
- `priority`: Message priority level ('low', 'normal', 'high', 'urgent')
- `routing_rules`: Rules for determining destination (list of dictionaries)
- `context`: Additional context for routing decisions (dictionary)
- `metadata`: Message metadata and headers (dictionary)
- `delivery_options`: Delivery preferences and requirements (dictionary)

## Processing Logic and Decision Trees
1. **Message Reception**:
   - Receive messages from various channels
   - Parse and validate message content
   - Extract metadata and context information
   - Determine message type and priority

2. **Content Analysis**:
   - Analyze message content for routing keywords
   - Identify message intent and purpose
   - Extract entities and important information
   - Apply natural language processing if needed

3. **Routing Decision**:
   - Evaluate routing rules against message attributes
   - Consider priority and urgency levels
   - Check recipient availability and preferences
   - Select appropriate destination channel

4. **Message Transformation**:
   - Format message for destination channel
   - Apply channel-specific transformations
   - Add necessary headers and metadata
   - Encrypt or secure sensitive content

5. **Delivery Management**:
   - Deliver message to selected destination
   - Track delivery status and confirmations
   - Handle delivery failures and retries
   - Update message status and logs

## Output Formats and File Structures
- Routes messages to appropriate channels based on rules
- Updates message logs in /Logs/communication_[date].log
- Maintains routing registry in /Data/routing_registry.db
- Generates communication reports in /Reports/communication_[date].md
- Updates Dashboard.md with communication metrics
- Creates delivery receipts in /Receipts/

## Error Handling Procedures
- Retry failed message deliveries according to delivery options
- Alert if routing rules cause delivery failures
- Implement circuit breaker for overloaded communication channels
- Log communication errors to /Logs/communication_errors.log
- Route critical communication failures to /Pending_Approval/ for manual intervention

## Security Considerations
- Validate and sanitize all message content to prevent injection
- Implement permission checks for message routing
- Maintain detailed audit trail of all communications
- Encrypt sensitive message content during routing
- Protect against spam and abuse through rate limiting

## Integration Points with Other System Components
- Integrates with all other skills for message routing
- Connects with Error Handler for communication-related errors
- Updates Dashboard Updater with communication metrics
- Creates audit logs for Communication Logger
- Coordinates with Scheduler for timed communications