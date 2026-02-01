# Scheduler Coordinator Skill

## Purpose and Use Cases
The Scheduler Coordinator skill provides centralized task scheduling and coordination for the Personal AI Employee system. It manages task execution timing, dependencies, resource allocation, and ensures optimal scheduling across all system components. This skill handles both recurring and one-time tasks while considering system resources, priorities, and dependencies.

## Input Parameters and Expected Formats
- `task_id`: Unique identifier for the scheduled task (string)
- `task_name`: Descriptive name for the task (string)
- `schedule_type`: Type of schedule ('once', 'recurring', 'conditional', 'event_driven')
- `execution_time`: When to execute the task (ISO format, cron expression, or relative time)
- `task_function`: Function or command to execute (string)
- `dependencies`: List of task IDs this task depends on (list of strings)
- `priority`: Task priority level ('low', 'normal', 'high', 'critical')
- `resource_requirements`: Resources needed for task execution (dictionary)
- `timeout_seconds`: Maximum execution time allowed (integer)
- `retry_policy`: How to handle failures ('none', 'fixed', 'exponential', 'custom')

## Processing Logic and Decision Trees
1. **Task Scheduling**:
   - Validate task parameters and dependencies
   - Check resource availability and constraints
   - Determine optimal execution time based on system load
   - Add task to execution queue

2. **Dependency Management**:
   - Resolve task dependencies and execution order
   - Detect circular dependency issues
   - Queue tasks until dependencies are satisfied
   - Handle dependency failures appropriately

3. **Resource Allocation**:
   - Monitor system resources (CPU, memory, disk, network)
   - Allocate resources based on task priority and requirements
   - Prevent resource conflicts and overallocation
   - Optimize resource utilization

4. **Execution Coordination**:
   - Execute tasks at scheduled times
   - Monitor task execution status
   - Handle task failures and retries
   - Coordinate with other system components

5. **Load Balancing**:
   - Distribute tasks to prevent system overload
   - Adjust scheduling based on system performance
   - Prioritize critical tasks during high load
   - Scale execution based on demand

## Output Formats and File Structures
- Updates task execution logs in /Logs/scheduler_[date].log
- Maintains schedule registry in /Data/schedule_registry.db
- Generates scheduling reports in /Reports/schedule_summary_[date].md
- Updates Dashboard.md with task execution metrics
- Creates task completion notifications in /Notifications/

## Error Handling Procedures
- Retry failed tasks according to retry policy
- Alert if scheduled tasks exceed timeout limits
- Implement circuit breaker for overloaded schedulers
- Log scheduling errors to /Logs/scheduler_errors.log
- Route critical scheduling failures to /Pending_Approval/ for manual intervention

## Security Considerations
- Validate all scheduled commands to prevent injection
- Implement permission checks for task execution
- Maintain detailed audit trail of all scheduled tasks
- Secure scheduling configuration and parameters
- Protect against denial-of-service through scheduling abuse

## Integration Points with Other System Components
- Integrates with all other skills for task scheduling
- Connects with Error Handler for scheduling-related errors
- Updates Dashboard Updater with scheduling metrics
- Creates audit logs for Communication Logger
- Coordinates with Resource Monitor for resource allocation