# Priority Evaluator Skill

## Purpose and Use Cases
The Priority Evaluator skill enables the AI employee to assess incoming tasks and prioritize them based on business rules, urgency, and impact. This skill ensures that critical activities receive appropriate attention while managing workload efficiently.

## Input Parameters and Expected Formats
- `task_type`: Category of task ('communication', 'financial', 'operational', 'strategic')
- `urgency`: Time sensitivity ('immediate', 'today', 'week', 'month', 'whenever')
- `impact_level`: Potential impact if not addressed ('low', 'medium', 'high', 'critical')
- `resource_requirement`: Estimated effort level ('minimal', 'low', 'medium', 'high', 'extensive')
- `deadline`: Due date in ISO 8601 format
- `stakeholder_priority`: Priority assigned by stakeholders ('low', 'medium', 'high', 'critical')
- `dependency_level`: Number of dependent tasks that require completion
- `business_value`: Estimated value to business if completed successfully

## Processing Logic and Decision Trees
1. **Assessment Process**:
   - Evaluate urgency and impact independently
   - Consider stakeholder input and business value
   - Factor in resource availability and constraints

2. **Scoring Process**:
   - Calculate composite priority score using weighted factors
   - Apply business rules for specific task categories
   - Adjust scores based on contextual factors

3. **Ranking Process**:
   - Sort tasks by priority score
   - Apply tie-breaking rules for equal scores
   - Consider resource allocation and scheduling constraints

4. **Assignment Process**:
   - Assign priority level ('P0', 'P1', 'P2', 'P3')
   - Determine execution timeline
   - Identify required resources

## Output Formats and File Structures
- Updates task records in /Data/tasks.db with priority scores
- Creates priority reports in /Reports/priority_[date].md
- Generates action files in /Needs_Action ordered by priority
- Updates Dashboard.md with priority distribution metrics

## Error Handling Procedures
- Retry failed priority calculations if data unavailable
- Assign default priority if scoring algorithm fails
- Alert if priority conflicts exist between tasks
- Log evaluation errors to /Logs/priority_errors.log

## Security Considerations
- Protect access to priority algorithms and business rules
- Maintain audit trail of priority assignments
- Secure sensitive business value estimates
- Validate input parameters to prevent manipulation

## Integration Points with Other System Components
- Integrates with Task Scheduler for execution planning
- Connects with Project Tracker for milestone prioritization
- Updates Dashboard Updater with priority metrics
- Creates action files in /Needs_Action for highest priority items