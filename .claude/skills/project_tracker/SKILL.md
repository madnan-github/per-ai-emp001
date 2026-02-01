# Project Tracker Skill

## Purpose and Use Cases
The Project Tracker skill enables the AI employee to monitor project progress, deadlines, and deliverables. This skill provides automated project management oversight while identifying potential delays, resource constraints, and risks to project success.

## Input Parameters and Expected Formats
- `project_id`: Unique identifier for the project
- `project_name`: Human-readable name for the project
- `start_date`: Project start date in ISO 8601 format
- `end_date`: Project deadline in ISO 8601 format
- `milestones`: Array of milestone objects with id, name, date, and status
- `team_members`: Array of team member identifiers assigned to project
- `budget`: Budget allocated for the project
- `status`: Current project status ('planning', 'active', 'on_hold', 'delayed', 'completed')
- `risk_level`: Current risk assessment ('low', 'medium', 'high', 'critical')

## Processing Logic and Decision Trees
1. **Project Setup**:
   - Validate project parameters and timeline
   - Create project tracking records
   - Set up milestone tracking

2. **Progress Monitoring**:
   - Track milestone completion against timeline
   - Monitor resource allocation and utilization
   - Compare actual vs planned progress

3. **Risk Assessment**:
   - Identify potential delays or obstacles
   - Assess impact of changes to timeline or resources
   - Flag projects approaching critical risk levels

4. **Reporting Process**:
   - Generate regular status reports
   - Alert stakeholders of potential issues
   - Update project dashboards with current status

## Output Formats and File Structures
- Maintains project data in /Data/projects.db
- Creates project status reports in /Reports/projects_[date].md
- Generates alerts in /Notifications/project_alerts_[date].txt
- Updates Dashboard.md with project health metrics

## Error Handling Procedures
- Retry failed data synchronization with project management tools
- Queue projects for manual review if status unclear
- Alert if critical milestones are missed
- Log project tracking errors to /Logs/project_errors.log

## Security Considerations
- Implement role-based access controls for project information
- Encrypt sensitive project data in storage
- Maintain audit trail of project status changes
- Secure sharing of project information with stakeholders

## Integration Points with Other System Components
- Integrates with Task Scheduler for milestone tracking
- Connects with Status Reporter for regular updates
- Updates Dashboard Updater with project metrics
- Creates action files in /Needs_Action for project interventions