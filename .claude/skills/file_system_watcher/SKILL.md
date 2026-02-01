# File System Watcher Skill

## Purpose and Use Cases
The File System Watcher skill enables the AI employee to monitor file drops and system events, triggering appropriate responses based on file types and locations. This skill provides automated file handling while ensuring important documents are processed and acted upon promptly.

## Input Parameters and Expected Formats
- `watch_directories`: Array of directory paths to monitor
- `file_patterns`: Array of file patterns to watch for ('*.pdf', '*.xlsx', 'invoice_*')
- `event_types`: Types of file events to monitor ('created', 'modified', 'deleted', 'moved')
- `priority_paths`: Directories with higher processing priority
- `processing_rules`: Mapping of file patterns to processing actions
- `retention_policy`: How long to retain processed files ('keep', 'archive', 'delete')
- `notification_settings`: Channels for file event notifications

## Processing Logic and Decision Trees
1. **Monitoring Process**:
   - Establish file system watchers on specified directories
   - Detect file creation, modification, or movement
   - Validate file types and integrity

2. **Classification Process**:
   - Match file patterns to processing rules
   - Determine appropriate action based on file type and location
   - Assign processing priority based on directory and content

3. **Action Process**:
   - Move files to appropriate processing queues
   - Create action files in /Needs_Action for processing
   - Apply retention policies to processed files

4. **Logging Process**:
   - Record all file events in monitoring logs
   - Track processing status and outcomes
   - Alert for unusual file activity patterns

## Output Formats and File Structures
- Creates file system logs in /Logs/filesystem_events_[date].log
- Generates action files in /Needs_Action for new files
- Creates processing records in /Data/file_processing.db
- Updates Dashboard.md with file processing metrics

## Error Handling Procedures
- Retry failed file operations with exponential backoff
- Queue files for manual processing if automated processing fails
- Alert if watched directories become inaccessible
- Log file system errors to /Logs/filesystem_errors.log

## Security Considerations
- Implement proper file system permissions for watchers
- Validate file types to prevent malicious uploads
- Encrypt sensitive files during processing
- Maintain audit trail of all file operations

## Integration Points with Other System Components
- Creates action files in /Needs_Action for document processing
- Updates Dashboard Updater with file processing metrics
- Integrates with Approval Processor for sensitive documents
- Connects with Communication Logger for file-related activities