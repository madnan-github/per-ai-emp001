# Invoice Generator Skill

## Purpose and Use Cases
The Invoice Generator skill enables the AI employee to create and send professional invoices based on completed work or predefined schedules. This skill automates billing processes while ensuring accuracy, compliance, and timely delivery of invoices to clients.

## Input Parameters and Expected Formats
- `client_info`: Client details object with name, address, tax ID
- `invoice_items`: Array of items/services with description, quantity, unit price
- `due_date`: Payment due date in ISO 8601 format
- `currency`: Currency code ('USD', 'EUR', 'GBP', etc.)
- `payment_terms`: Payment terms ('net30', 'net15', 'due_on_receipt')
- `invoice_number`: Optional invoice number (auto-generated if not provided)
- `notes`: Additional notes for the invoice
- `attachments`: Array of file paths to attach to invoice email

## Processing Logic and Decision Trees
1. **Invoice Creation**:
   - Validate client information and invoice items
   - Calculate totals, taxes, and discounts
   - Generate unique invoice number
   - Format invoice according to company branding

2. **Approval Process**:
   - Check invoice amount against approval thresholds
   - Route high-value invoices to /Pending_Approval/
   - Auto-approve low-risk invoices

3. **Delivery Process**:
   - Generate PDF invoice document
   - Send via email to client
   - Record invoice in accounting system

4. **Follow-up Process**:
   - Schedule payment reminders
   - Track payment status
   - Escalate overdue invoices per policy

## Output Formats and File Structures
- Creates invoice PDFs in /Documents/Invoices/[year]/[month]/
- Generates approval requests in /Pending_Approval/invoice_[timestamp].md for high-value invoices
- Updates accounting records in /Data/invoices.db
- Updates Dashboard.md with billing metrics and outstanding amounts

## Error Handling Procedures
- Retry failed email sends with exponential backoff
- Log failed invoice generations to /Logs/invoice_errors.log
- Queue invoices for manual processing if template unavailable
- Alert if client record incomplete

## Security Considerations
- Encrypt sensitive financial data in storage
- Implement approval workflow for all invoices
- Maintain audit trail of invoice creation and delivery
- Secure deletion of temporary invoice files

## Integration Points with Other System Components
- Integrates with Approval Processor for high-value invoices
- Updates Dashboard Updater with billing metrics
- Creates action files in /Needs_Action for overdue payments
- Connects with Bank Transaction Monitor to reconcile payments