# Gmail API Guide for Watcher Applications

## Authentication and Authorization

### OAuth 2.0 Setup
- **Credentials**: Create credentials in Google Cloud Console
- **Application Type**: Desktop application for local watchers
- **Scopes**:
  - `https://www.googleapis.com/auth/gmail.readonly` (read-only access)
  - `https://www.googleapis.com/auth/gmail.modify` (read and modify labels)
  - `https://www.googleapis.com/auth/gmail.settings.basic` (basic settings)
- **Client ID/Secret**: Store securely in environment variables
- **Token Storage**: Save refresh tokens securely for persistent access

### Token Management
- **Refresh Tokens**: Long-lived tokens for continuous access
- **Token Expiration**: Handle token expiration gracefully
- **Secure Storage**: Encrypt stored tokens, use OS keychain when possible
- **Revocation**: Implement token revocation for security
- **Rotation**: Refresh tokens periodically to maintain access

## API Endpoints and Methods

### Message Retrieval
- **users.messages.list**: Get list of message IDs
  - Parameters: `userId`, `q` (search query), `maxResults`, `pageToken`
  - Rate Limit: 250 requests per 100 seconds per user
  - Pagination: Use `nextPageToken` for large result sets
- **users.messages.get**: Retrieve specific message details
  - Parameters: `userId`, `id`, `format` (minimal, full, raw, metadata)
  - Metadata view: Efficient for basic properties
  - Raw format: Full message including attachments

### Thread Operations
- **users.threads.get**: Retrieve full conversation thread
  - Parameters: `userId`, `id`, `format`
  - Advantage: Single request for entire conversation
  - Use case: Complete context for processing
- **users.threads.list**: List threads matching criteria
  - Parameters: `userId`, `q`, `maxResults`, `pageToken`
  - More efficient than message-level queries

### Label Management
- **users.labels.list**: Get available labels
  - Parameters: `userId`
  - System labels: INBOX, UNREAD, SENT, etc.
  - Custom labels: User-defined categories
- **users.messages.modify**: Add/remove labels
  - Parameters: `userId`, `id`, `addLabelIds`, `removeLabelIds`
  - Use case: Mark processed messages
  - Batch operations: Efficient for multiple messages

## Search Query Syntax

### Basic Filters
- **From**: `from:user@example.com`
- **To**: `to:user@example.com`
- **Subject**: `subject:"meeting"`, `subject:(urgent OR important)`
- **Body**: `body:"important information"`
- **Date**: `after:2023-01-01`, `before:2023-12-31`, `newer_than:1d`
- **Attachments**: `has:attachment`, `filename:pdf`, `size:larger_than:1048576`

### Advanced Filters
- **Labels**: `label:inbox`, `label:unread`, `label:important`
- **Read Status**: `is:unread`, `is:read`
- **Starred**: `is:starred`, `is:unstarred`
- **Priority**: `from:priority`, `category:primary`
- **Combination**: `from:boss@example.com is:unread after:2023-06-01`

### Query Optimization
- **Specificity**: Use specific filters to reduce result set
- **Date Ranges**: Narrow time windows for efficient polling
- **Boolean Logic**: Combine conditions with AND, OR, NOT
- **Wildcards**: Use quotes for exact phrase matching
- **Performance**: Avoid overly broad queries

## Polling Strategies

### Efficient Polling
- **Incremental Sync**: Track `historyId` for changes since last poll
- **Smart Intervals**: Adjust polling frequency based on activity
- **Time Windows**: Focus on business hours or expected arrival times
- **Backoff Algorithm**: Increase interval after consecutive empty polls
- **Batch Processing**: Handle multiple messages per poll cycle

### Push Notifications (Push API)
- **Pub/Sub Setup**: Configure Google Cloud Pub/Sub for real-time updates
- **Webhook Registration**: Register endpoint for message notifications
- **Message Acknowledgment**: Acknowledge messages to prevent redelivery
- **Error Handling**: Handle webhook failures and retries
- **Fallback**: Maintain polling as backup to push notifications

## Message Processing

### Header Parsing
- **From Field**: Parse sender name and email address
- **To Field**: Extract primary recipients
- **CC Field**: Identify carbon copy recipients
- **BCC Field**: Note blind carbon copy recipients
- **Reply-To**: Determine reply destination
- **Date**: Convert to local timezone consistently

### Content Extraction
- **Plain Text**: Extract plain text content when available
- **HTML Content**: Parse HTML while preserving meaning
- **Attachments**: Identify and download attachments safely
- **Encoding**: Handle various character encodings
- **Size Limits**: Respect maximum attachment sizes

### Spam and Security Filtering
- **Phishing Detection**: Identify potential phishing attempts
- **Malware Scanning**: Scan attachments for malicious content
- **Domain Reputation**: Check sender domain reputation
- **Content Analysis**: Analyze content for suspicious patterns
- **Whitelist/Blacklist**: Maintain trusted and blocked senders

## Rate Limits and Quotas

### Understanding Quotas
- **Per User**: 250 requests per 100 seconds per user
- **Per Project**: 1,000,000 requests per day per project
- **Per IP**: Distributed across all users in project
- **Upload Quota**: 1GB per user per day for attachments

### Managing Quotas
- **Request Batching**: Combine operations when possible
- **Caching**: Cache results to reduce redundant requests
- **Exponential Backoff**: Implement retry logic for quota errors
- **Monitoring**: Track quota usage and set alerts
- **Efficient Queries**: Minimize the number of API calls

## Error Handling

### Common Errors
- **Rate Limit Exceeded**: Implement exponential backoff
- **Authentication Failure**: Refresh tokens or prompt re-authentication
- **Resource Not Found**: Handle deleted messages gracefully
- **Temporary Unavailability**: Retry with appropriate delays
- **Quota Exceeded**: Reduce request frequency or upgrade quota

### Retry Logic
- **Exponential Backoff**: Increase delay between retries
- **Jitter**: Add randomness to prevent thundering herd
- **Maximum Attempts**: Limit retry attempts to prevent infinite loops
- **Error Classification**: Distinguish between retryable and permanent errors
- **Logging**: Track errors for debugging and monitoring

## Security Best Practices

### Credential Security
- **Environment Variables**: Store credentials outside source code
- **Encryption**: Encrypt stored tokens and credentials
- **Least Privilege**: Use minimal required scopes
- **Regular Rotation**: Rotate credentials periodically
- **Access Logging**: Monitor access to credentials

### Data Privacy
- **Local Processing**: Process sensitive data locally when possible
- **Encryption in Transit**: Use HTTPS for all API communications
- **Secure Storage**: Encrypt stored email data
- **Retention Policies**: Implement data retention and deletion
- **Compliance**: Follow GDPR, CCPA, and other privacy regulations

## Performance Optimization

### Caching Strategies
- **Message Cache**: Cache recently retrieved messages
- **Label Cache**: Cache label information
- **Contact Cache**: Cache contact information
- **Query Results**: Cache frequent query results temporarily
- **Invalidation**: Implement appropriate cache invalidation

### Connection Management
- **Connection Pooling**: Reuse connections when possible
- **Keep-Alive**: Use HTTP keep-alive for multiple requests
- **Compression**: Enable gzip compression for responses
- **Timeouts**: Set appropriate connection and request timeouts
- **Monitoring**: Monitor connection performance and errors