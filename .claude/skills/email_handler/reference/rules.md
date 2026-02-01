# Email Processing Rules

## Categorization Rules

### Business Category
- From: business domains (.com, .org, .biz)
- Contains: business terms, contract language, proposal content
- Exclude: newsletters, social media notifications

### Personal Category
- From: personal domains (.gmail.com, .yahoo.com, .hotmail.com)
- Contains: casual language, personal references
- Exclude: business solicitations

### Marketing Category
- From: marketing addresses (newsletter, promotions, offers)
- Contains: promotional language, discount codes, opt-out links
- Exclude: transactional emails

### Transactional Category
- From: verified business services (banks, utilities, subscriptions)
- Contains: receipts, confirmations, billing information
- Exclude: promotional content

## Response Automation Rules

### Immediate Response (Under 2 hours)
- Appointment confirmations
- Order acknowledgments
- Payment receipts
- System notifications

### Delayed Response (Same day)
- Business inquiries
- Customer support requests
- Partnership proposals

### Manual Review Required
- Legal notices
- Complaints
- Negative feedback
- Unusual requests

## Escalation Rules

### Automatic Escalation
- Emails marked as "URGENT" or "CRITICAL"
- Legal department involvement
- Financial discrepancies > $1000
- Security incidents

### Conditional Escalation
- VIP client requests
- Contract negotiations
- Media inquiries
- Government correspondence

## Security and Compliance Rules

### Required Approval
- Sending attachments > 10MB
- Forwarding external emails
- Sharing confidential information
- Responding to suspicious senders

### Content Filtering
- Block emails with known malware signatures
- Quarantine emails with suspicious links
- Flag emails containing sensitive keywords
- Scan attachments for viruses