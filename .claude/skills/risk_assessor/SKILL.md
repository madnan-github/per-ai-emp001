# Risk Assessor Skill

## Purpose and Use Cases
The Risk Assessor skill evaluates risks associated with proposed actions, business decisions, and operational changes. This skill provides quantitative and qualitative risk analysis to support informed decision-making while identifying potential threats to business continuity.

## Input Parameters and Expected Formats
- `activity_type`: Category of activity being assessed ('financial', 'operational', 'strategic', 'compliance')
- `risk_factors`: Array of specific risk factors to evaluate ('financial', 'reputational', 'operational', 'regulatory')
- `probability_matrix`: Probability assessments for different risk scenarios
- `impact_assessment`: Potential impact levels ('low', 'medium', 'high', 'critical')
- `mitigation_strategies`: Available risk mitigation approaches
- `risk_tolerance`: Organization's tolerance for the specific risk type
- `time_horizon`: Time period over which risk applies ('short_term', 'medium_term', 'long_term')

## Processing Logic and Decision Trees
1. **Risk Identification**:
   - Identify potential risks based on activity type and context
   - Consider internal and external risk factors
   - Map risks to business impact areas

2. **Risk Analysis**:
   - Calculate probability and impact for each identified risk
   - Apply quantitative risk assessment models
   - Consider correlations between different risks

3. **Risk Evaluation**:
   - Compare calculated risks against tolerance thresholds
   - Prioritize risks by combined probability and impact
   - Assess effectiveness of available mitigations

4. **Recommendation Process**:
   - Generate risk treatment recommendations
   - Identify required controls or safeguards
   - Suggest risk acceptance, mitigation, transfer, or avoidance

## Output Formats and File Structures
- Creates risk assessments in /Reports/risk_assessment_[activity]_[date].md
- Maintains risk register in /Data/risk_register.db
- Generates risk scoring in /Data/risk_scores.db
- Updates Dashboard.md with risk metrics and heat maps

## Error Handling Procedures
- Retry failed risk model calculations if data unavailable
- Apply conservative risk estimates if precise data lacking
- Alert if risk assessments exceed organizational thresholds
- Log risk calculation errors to /Logs/risk_assessment_errors.log

## Security Considerations
- Implement access controls for sensitive risk assessments
- Encrypt confidential risk information
- Maintain audit trail of all risk evaluations
- Secure risk model parameters and calculations

## Integration Points with Other System Components
- Integrates with Approval Processor for high-risk activities
- Connects with Policy Enforcer for risk-based controls
- Updates Dashboard Updater with risk metrics
- Creates action files in /Needs_Action for risk mitigation activities