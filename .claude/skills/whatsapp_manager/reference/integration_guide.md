# WhatsApp Integration Guide

## API Configuration

### Environment Variables
```bash
WHATSAPP_API_TOKEN=your_api_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_verify_token
WHATSAPP_APP_SECRET=your_app_secret
```

### Required Dependencies
- Python 3.8+
- Playwright for browser automation
- Requests library for API calls
- Flask for webhook handling
- SQLite3 for local data storage

## Authentication Flow

### Step 1: Get Long-Lived Token
```python
import requests

def get_long_lived_token(short_token):
    url = "https://graph.facebook.com/v17.0/oauth/access_token"
    params = {
        'grant_type': 'fb_exchange_token',
        'client_id': os.getenv('WHATSAPP_APP_ID'),
        'client_secret': os.getenv('WHATSAPP_APP_SECRET'),
        'fb_exchange_token': short_token
    }
    response = requests.get(url, params=params)
    return response.json()['access_token']
```

### Step 2: Verify Webhook
```python
def verify_webhook(request):
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token == os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN'):
        return challenge, 200
    else:
        return 'Forbidden', 403
```

## Message Handling

### Message Types Supported
- Text messages
- Image messages
- Document messages
- Location messages
- Contact messages
- Audio messages

### Rate Limits
- Messages to customers who initiated conversation: 24-hour window
- Messages to customers who haven't replied: Template messages only
- Maximum 30 messages per hour to the same customer

## Error Handling

### Common Errors
- 130429: Rate limit exceeded
- 131047: Invalid phone number
- 131048: Unsupported message type
- 132004: Message not sent within 24-hour window

### Retry Logic
- Exponential backoff for API errors
- Retry failed messages up to 3 times
- Log permanent failures for manual review

## Security Best Practices

### Data Encryption
- Encrypt sensitive customer data at rest
- Use HTTPS for all API communications
- Sanitize all input data to prevent injection

### Access Control
- Limit API token permissions to required scopes
- Rotate tokens regularly
- Monitor API usage for unusual patterns

## Webhook Event Handling

### Message Received Event
```python
def handle_message_received(data):
    message = data['entry'][0]['changes'][0]['value']['messages'][0]
    sender = message['from']
    message_text = message.get('text', {}).get('body', '')

    # Process message and generate response
    response = process_message(sender, message_text)
    send_reply(sender, response)
```

### Message Status Updates
- Sent: Message sent to WhatsApp server
- Delivered: Message delivered to recipient
- Read: Message read by recipient
- Failed: Message failed to send

## Message Templates

### Template Requirements
- Pre-approved by WhatsApp
- Limited to specific use cases
- Brand-consistent messaging
- Localized for target markets

### Template Categories
- Account Update
- Alert Update
- Auto Reply
- Billing Update
- Marketing
- OTP