# Invoice Validation Rules

## Pre-Generation Validation

### Client Information Validation
- **Client Existence Check**: Verify client exists in the client database
- **Complete Address Required**: Validate that all address fields are filled
- **Valid Email Format**: Check email format for delivery purposes
- **Tax ID Validation**: Verify tax ID/EIN format if required
- **Credit Limit Check**: Ensure invoice amount doesn't exceed client credit limit

### Invoice Data Validation
- **Unique Invoice Number**: Verify invoice number is unique and sequential
- **Date Validation**: Invoice date must be current or past (no future dates)
- **Due Date Validation**: Due date must be after invoice date
- **Positive Amounts**: All amounts must be positive numbers
- **Required Descriptions**: All items must have a description

## Calculation Validation

### Mathematical Accuracy
- **Subtotal Calculation**: Sum of all item amounts
- **Tax Calculation**: Correct tax rate applied to taxable items
- **Discount Application**: Proper discount calculation and application
- **Total Validation**: Subtotal + Tax - Discount = Total
- **Currency Consistency**: All amounts in same currency

### Tax Validation
- **Tax Rate Verification**: Correct tax rate for client location
- **Taxable Item Identification**: Properly marked taxable vs non-taxable
- **Tax Exemption Validation**: Verify valid exemption certificates
- **Multi-Tax Scenarios**: Correctly calculate multiple tax jurisdictions

## Approval Validation

### Threshold Validation
- **Amount Thresholds**: Route to appropriate approval level
- **Client History Check**: Consider client payment history
- **First-Time Client**: Additional scrutiny for new clients
- **International Invoice**: Special validation for foreign clients

### Business Rule Validation
- **Scope Alignment**: Invoice items match approved scope of work
- **Rate Verification**: Applied rates match agreed-upon rates
- **Time/Materials Cap**: Check against project caps if applicable
- **Duplicate Prevention**: Ensure no duplicate billing

## Post-Generation Validation

### Final Checks
- **PDF Generation Success**: Verify invoice document created properly
- **Attachment Validation**: Check all required attachments included
- **Email Delivery Format**: Validate email format for sending
- **Audit Trail Creation**: Ensure proper logging of invoice creation

## Error Handling Rules

### Critical Errors (Stop Processing)
- Invalid client information
- Mathematical calculation errors
- Duplicate invoice number
- Missing required fields
- Amount mismatch in calculations

### Warning Conditions (Allow with Alert)
- Large discount percentages (>20%)
- First invoice for new client
- International client invoicing
- Credit limit close to being exceeded
- Unusual item descriptions

### Validation Severity Levels
1. **Critical**: Stop invoice generation
2. **High**: Require manager approval
3. **Medium**: Generate alert but continue
4. **Low**: Log for review but continue

## Client-Specific Validation Rules

### VIP Client Rules
- Expedited validation process
- Automatic approval up to higher thresholds
- Special formatting requirements
- Premium delivery options

### Standard Client Rules
- Normal validation process
- Standard approval thresholds
- Regular delivery methods
- Standard follow-up procedures

### Risk Client Rules
- Enhanced validation requirements
- Higher approval thresholds
- Additional documentation required
- Closer payment monitoring

## Recurring Invoice Validation

### Recurring Pattern Checks
- **Consistency Verification**: Ensure amounts consistent with previous invoices
- **Billing Cycle Validation**: Verify invoice aligns with agreed cycle
- **Proration Calculation**: Correct calculation for partial periods
- **Adjustment Validation**: Proper handling of changes from previous invoices

## Project-Based Invoice Validation

### Scope Validation
- **Work Completion**: Verify work has been completed before invoicing
- **Milestone Verification**: Confirm milestone achievement for milestone billing
- **Budget Adherence**: Check against project budget constraints
- **Change Order Integration**: Include approved change orders

### Time & Materials Validation
- **Time Entry Verification**: Validate time entries against project
- **Rate Application**: Apply correct rates for team members
- **Expense Validation**: Verify expenses are project-appropriate
- **Cap Monitoring**: Track against project spending caps

## International Invoice Validation

### Currency Rules
- **Exchange Rate Validation**: Use appropriate exchange rate
- **Currency Disclosure**: Clearly indicate currency used
- **Conversion Documentation**: Record conversion methodology
- **VAT/GST Compliance**: Apply appropriate international taxes

### Legal Requirement Validation
- **Local Tax Compliance**: Follow destination country tax rules
- **Language Requirements**: Provide invoices in required languages
- **Format Compliance**: Meet local invoice format requirements
- **Retention Rules**: Follow local record retention requirements

## Payment Term Validation

### Terms Verification
- **Standard Term Application**: Apply correct standard terms
- **Client-Specific Terms**: Honor negotiated special terms
- **Credit Hold Check**: Verify client not on credit hold
- **History Consideration**: Consider payment history in terms

## Delivery Validation

### Method Validation
- **Email Verification**: Confirm email addresses are valid
- **Portal Access**: Verify client portal access exists
- **Physical Address**: Validate physical delivery addresses
- **Secure Delivery**: Ensure secure delivery for sensitive invoices

### Confirmation Validation
- **Delivery Confirmation**: Verify delivery success
- **Read Receipt**: Attempt to confirm client receipt
- **Delivery Failure**: Handle and retry failed deliveries
- **Confirmation Logging**: Log all delivery confirmations

## Compliance Validation

### Regulatory Compliance
- **Tax Law Compliance**: Ensure compliance with tax regulations
- **Industry Standards**: Follow industry-specific billing standards
- **Data Protection**: Ensure compliance with privacy laws
- **Record Keeping**: Maintain required records per regulations

### Audit Trail Validation
- **Creation Logging**: Log all invoice creation activities
- **Modification Tracking**: Track all changes to invoices
- **Approval Documentation**: Record all approval activities
- **Delivery Logging**: Log all invoice delivery attempts