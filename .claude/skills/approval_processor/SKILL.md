# Approval Processor Skill

## Purpose and Use Cases
The Approval Processor skill handles approval workflows for payments, sensitive actions, and business decisions. This skill manages the human-in-the-loop approval process while maintaining security and compliance through the "claim-by-move" pattern and systematic oversight.

## Input Parameters and Expected Formats
- `request_type`: Type of approval request ('payment', 'communication', 'data_access', 'system_change')
- `requestor`: Identity of the requesting entity
- `approver`: Designated approver for the request
- `request_details`: Detailed information about the request
- `approval_threshold`: Value or risk level requiring approval
- `business_justification`: Reason for the requested action
- `expiration_time`: Time limit for approval decision
- `fallback_action`: Action to take if approval not received

## Processing Logic and Decision Trees
1. **Request Validation**:
   - Verify request format and completeness
   - Check requestor permissions and authorization
   - Validate business justification

2. **Approval Routing**:
   - Determine appropriate approver based on request type and value
   - Create approval request file in /Pending_Approval/
   - Notify designated approver via preferred channel

3. **Monitoring Process**:
   - Watch for file movement from /Pending_Approval/ to /Approved/
   - Track approval status and timing
   - Handle expired or rejected requests

4. **Execution Process**:
   - Execute approved requests upon file movement
   - Log all approval activities
   - Notify requestor of outcome

## Output Formats and File Structures
- Creates approval requests in /Pending_Approval/[request_type]_[timestamp].md
- Maintains approval records in /Data/approvals.db
- Creates execution logs in /Logs/approval_execution_[date].log
- Updates Dashboard.md with approval metrics

## Error Handling Procedures
- Retry failed approval notifications with exponential backoff
- Queue requests for manual processing if approval system unavailable
- Alert if approvals remain pending beyond expiration time
- Log approval failures to /Logs/approval_errors.log

## Security Considerations
- Implement strict access controls for approval files
- Encrypt sensitive approval information
- Maintain immutable audit trail of all approval activities
- Secure approval channels and authentication

## Integration Points with Other System Components
- Creates approval requests for all other system components when needed
- Updates Dashboard Updater with approval metrics
- Integrates with Communication Logger for approval notifications
- Creates action files in /Needs_Action for approved requests