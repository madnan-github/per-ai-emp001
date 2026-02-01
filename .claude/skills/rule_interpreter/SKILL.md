# Rule Interpreter Skill

## Purpose and Use Cases
The Rule Interpreter skill applies company handbook rules to incoming situations and business scenarios. This skill ensures consistent enforcement of business policies while providing automated decision-making based on documented company guidelines and procedures.

## Input Parameters and Expected Formats
- `rule_set`: Identifier for the set of rules to apply ('company_handbook', 'compliance', 'security', 'operations')
- `situation_context`: Description of the situation requiring rule interpretation
- `applicable_policies`: Specific policies relevant to the situation
- `decision_type`: Type of decision needed ('compliance_check', 'policy_enforcement', 'approval_guidance')
- `stakeholder_input`: Input from relevant stakeholders (optional)
- `precedent_cases`: Previous similar situations for reference
- `override_permissions`: Permissions allowing rule overrides (if applicable)

## Processing Logic and Decision Trees
1. **Context Analysis**:
   - Parse situation description and identify key elements
   - Match situation to relevant rule categories
   - Extract applicable policy sections

2. **Rule Application**:
   - Apply relevant rules to the specific situation
   - Resolve conflicts between competing rules
   - Consider situational context and exceptions

3. **Decision Processing**:
   - Generate recommended action based on rule application
   - Identify required approvals or escalations
   - Document reasoning for the decision

4. **Validation Process**:
   - Cross-check decision against related policies
   - Verify compliance with regulatory requirements
   - Flag edge cases for human review

## Output Formats and File Structures
- Creates decision logs in /Logs/rule_decisions_[date].log
- Maintains rule application records in /Data/rule_applications.db
- Generates policy compliance reports in /Reports/compliance_[date].md
- Updates Dashboard.md with rule enforcement metrics

## Error Handling Procedures
- Retry failed rule lookups if policy documents unavailable
- Route ambiguous situations to /Pending_Approval/ for human judgment
- Alert if conflicting rules are detected
- Log rule interpretation errors to /Logs/rule_errors.log

## Security Considerations
- Implement access controls for sensitive policy documents
- Encrypt confidential rule applications
- Maintain audit trail of all rule interpretations
- Secure policy document storage and retrieval

## Integration Points with Other System Components
- Integrates with Approval Processor for policy exceptions
- Connects with Policy Enforcer for rule compliance
- Updates Dashboard Updater with compliance metrics
- Creates action files in /Needs_Action for policy violations