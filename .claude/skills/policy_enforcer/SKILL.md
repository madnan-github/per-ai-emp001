# Policy Enforcer Skill

## Purpose and Use Cases
The Policy Enforcer skill ensures all actions comply with predefined policies by validating activities against established rules and procedures. This skill provides automated compliance checking while preventing unauthorized or policy-violating activities from proceeding.

## Input Parameters and Expected Formats
- `activity_type`: Type of activity being validated ('communication', 'financial', 'data_access', 'system_operation')
- `policy_area`: Area of policy being enforced ('security', 'compliance', 'operations', 'finance')
- `activity_details`: Detailed information about the proposed activity
- `applicable_policies`: Specific policies that apply to this activity
- `exception_request`: Request for policy exception (if applicable)
- `authorization_level`: Authorization level required for the activity
- `compliance_requirements`: Regulatory or standard requirements

## Processing Logic and Decision Trees
1. **Policy Matching**:
   - Identify relevant policies based on activity type
   - Retrieve applicable policy rules and constraints
   - Validate activity against policy requirements

2. **Compliance Check**:
   - Verify activity meets all policy criteria
   - Check authorization levels and permissions
   - Validate required approvals are in place

3. **Exception Handling**:
   - Process exception requests if applicable
   - Route to /Pending_Approval/ for exception review
   - Apply temporary permissions if approved

4. **Enforcement Action**:
   - Block activities that violate policies
   - Allow compliant activities to proceed
   - Log all enforcement decisions

## Output Formats and File Structures
- Creates compliance logs in /Logs/policy_compliance_[date].log
- Maintains policy violation records in /Data/violations.db
- Generates compliance reports in /Reports/compliance_[date].md
- Updates Dashboard.md with policy compliance metrics

## Error Handling Procedures
- Retry failed policy lookups if policy documents unavailable
- Apply default deny policy if uncertain about compliance
- Alert if policy conflicts are detected
- Log enforcement errors to /Logs/policy_enforcement_errors.log

## Security Considerations
- Implement privileged access for policy enforcement functions
- Encrypt sensitive policy violation information
- Maintain immutable audit trail of all enforcement actions
- Secure policy documents and enforcement rules

## Integration Points with Other System Components
- Integrates with Approval Processor for policy exceptions
- Connects with Rule Interpreter for complex policy applications
- Updates Dashboard Updater with compliance metrics
- Creates action files in /Needs_Action for policy violations