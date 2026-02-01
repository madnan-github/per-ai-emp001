# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a "Personal AI Employee" project - an autonomous digital employee that operates 24/7 to manage personal and business affairs. The system is built around Claude Code as the reasoning engine with Obsidian as the local knowledge base and dashboard. The architecture follows a four-tier approach for comprehensive functionality and robust operations.

## Four-Tier Architecture

### Tier 1: Perception Layer (Sensors & Watchers)
- **Gmail Watcher**: Monitors Gmail for important/unread messages using the Gmail API
- **WhatsApp Watcher**: Uses Playwright to automate WhatsApp Web for message monitoring
- **File System Watcher**: Monitors file drops and system events
- **Calendar Watcher**: Monitors calendar events and appointments
- **Database Connector**: Connects to various databases for data retrieval
- **API Gateway**: Manages API communications with external services

### Tier 2: Reasoning Layer (Core Intelligence)
- **The Brain**: Claude Code acts as the reasoning engine with "Ralph Wiggum" stop hooks to keep the agent iterating until tasks are complete
- **Error Handler**: Manages errors across all system components with retry mechanisms and circuit breakers
- **Credential Manager**: Securely manages authentication credentials and API keys
- **Backup & Recovery**: Handles data backup and system recovery procedures
- **Scheduler Coordinator**: Orchestrates scheduled tasks and job execution
- **Resource Monitor**: Tracks system resources and performance metrics
- **Communication Router**: Routes messages between system components
- **Learning & Adaptation**: Implements machine learning for system improvement
- **Knowledge Base Updater**: Maintains and updates system knowledge
- **Security Scanner**: Performs security assessments and vulnerability scans
- **Quality Assurance**: Ensures system quality through testing and validation

### Tier 3: Action Layer (Actuators & MCP)
- **Email MCP**: Send, draft, and search emails
- **Browser MCP**: Navigate, click, fill forms for payment portals
- **Calendar MCP**: Create and update calendar events
- **Slack MCP**: Send messages and read channels
- **File System MCP**: Manage file operations and storage
- **Payment Processor**: Handle financial transactions securely
- **Document Generator**: Create and format documents
- **Invoice Generator**: Generate invoices and billing documents
- **Expense Tracker**: Track expenses and costs
- **Revenue Reporter**: Generate revenue reports and analytics
- **Subscription Auditor**: Monitor and manage subscriptions
- **Bank Transaction Monitor**: Track bank transactions
- **Task Scheduler**: Schedule and manage recurring tasks
- **Project Tracker**: Track project progress and deadlines
- **Priority Evaluator**: Assess and prioritize tasks
- **Status Reporter**: Generate status reports and updates
- **Gmail Watcher**: Monitor Gmail for triggers and updates

### Tier 4: Presentation Layer (User Interface & Communication)
- **Social Media Poster**: Post updates to social media platforms
- **Communication Logger**: Log all communications and interactions
- **Dashboard Updater**: Maintain real-time dashboard status
- **Notification Aggregator**: Consolidate and manage notifications
- **NextJS UI Builder**: Create and manage NextJS user interfaces
- **Authentication Manager**: Handle user authentication and authorization

## Core Components

### Watcher System
- **Gmail Watcher**: Monitors Gmail for important/unread messages using the Gmail API
- **WhatsApp Watcher**: Uses Playwright to automate WhatsApp Web for message monitoring
- **File System Watcher**: Monitors file drops and system events
- **Calendar Watcher**: Monitors calendar events and appointments

### MCP (Model Context Protocol) Servers
- **Email MCP**: Send, draft, and search emails
- **Browser MCP**: Navigate, click, fill forms for payment portals
- **Calendar MCP**: Create and update calendar events
- **Slack MCP**: Send messages and read channels
- **File System MCP**: Manage file operations and storage
- **Payment Processor**: Handle financial transactions securely

### Human-in-the-Loop (HITL) Pattern
- Critical actions require approval via file-based workflow
- Files created in `/Pending_Approval` folder require manual movement to `/Approved` to proceed
- Prevents unauthorized actions like payments or sensitive communications

## Skill Architecture

The system utilizes a comprehensive skill-based architecture located in `.claude/skills/` directory. Each skill follows a standardized structure:

### Skill Structure
Each skill contains:
- `SKILL.md`: Documentation with purpose, use cases, input parameters, processing logic, output formats, error handling, security considerations, and integration points
- `reference/`: Detailed documentation and guides for the skill
- `scripts/`: Implementation code for the skill functionality

### Available Skills
#### Communication & Marketing
- **Email Composer**: Compose and send professional emails
- **Social Media Poster**: Post updates to social media platforms
- **Marketing Campaign Manager**: Plan and execute marketing campaigns
- **Customer Outreach**: Manage customer communication and outreach
- **Lead Generation**: Identify and qualify potential leads

#### Business Management
- **Project Tracker**: Track project progress and deadlines
- **Task Scheduler**: Schedule and manage recurring tasks
- **Invoice Generator**: Generate invoices and billing documents
- **Expense Tracker**: Track expenses and costs
- **Revenue Reporter**: Generate revenue reports and analytics
- **Subscription Auditor**: Monitor and manage subscriptions
- **Bank Transaction Monitor**: Track bank transactions
- **Priority Evaluator**: Assess and prioritize tasks
- **Status Reporter**: Generate status reports and updates

#### Personal Assistance
- **Calendar Coordinator**: Manage calendar events and appointments
- **Travel Planner**: Plan trips and travel arrangements
- **Meeting Scheduler**: Coordinate meeting schedules
- **Personal Finance Manager**: Track personal finances
- **Health & Wellness Tracker**: Monitor health and wellness goals

#### Monitoring & Reporting
- **System Monitor**: Monitor system performance and health
- **Analytics Dashboard**: Generate analytics and insights
- **Performance Reporter**: Track and report performance metrics
- **Risk Assessor**: Evaluate and mitigate risks
- **Compliance Checker**: Ensure regulatory compliance

#### Decision Making & Strategy
- **Decision Support**: Provide data-driven decision support
- **Strategic Planner**: Develop strategic plans
- **Market Research**: Conduct market research and analysis
- **Competitive Analysis**: Analyze competitors and market position
- **Financial Analyst**: Perform financial analysis and projections

#### Development & Operations
- **Database Connector**: Connect to various databases for data retrieval
- **API Gateway**: Manage API communications with external services
- **File System MCP**: Manage file operations and storage
- **Payment Processor**: Handle financial transactions securely
- **Document Generator**: Create and format documents
- **Gmail Watcher**: Monitor Gmail for triggers and updates

#### System Infrastructure
- **Error Handler**: Manages errors across all system components with retry mechanisms and circuit breakers
- **Credential Manager**: Securely manages authentication credentials and API keys
- **Backup & Recovery**: Handles data backup and system recovery procedures
- **Scheduler Coordinator**: Orchestrates scheduled tasks and job execution
- **Resource Monitor**: Tracks system resources and performance metrics
- **Communication Router**: Routes messages between system components
- **Learning & Adaptation**: Implements machine learning for system improvement
- **Knowledge Base Updater**: Maintains and updates system knowledge
- **Security Scanner**: Performs security assessments and vulnerability scans
- **Quality Assurance**: Ensures system quality through testing and validation
- **NextJS UI Builder**: Create and manage NextJS user interfaces
- **Authentication Manager**: Handle user authentication and authorization

## Development Commands

### Setup
```bash
# Install Claude Code
npm install -g @anthropic/claude-code

# Verify installation
claude --version

# Install Python dependencies
pip install watchdog google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client playwright

# Setup Playwright browsers
playwright install
```

### Running Watchers
```bash
# Run individual watchers
python gmail_watcher.py
python whatsapp_watcher.py
python filesystem_watcher.py

# Using PM2 for persistent running
pm2 start gmail_watcher.py --interpreter python3
pm2 start whatsapp_watcher.py --interpreter python3
pm2 save  # Save current processes
pm2 startup  # Enable auto-start on boot
```

### Ralph Wiggum Loop (Autonomous Operation)
```bash
# Run Claude in autonomous mode until task completion
/ralph-loop "Process all files in /Needs_Action, move to /Done when complete" \
  --completion-promise "TASK_COMPLETE" \
  --max-iterations 10
```

### MCP Configuration
Configure MCP servers in `~/.config/claude-code/mcp.json`:

```json
{
  "servers": [
    {
      "name": "email",
      "command": "node",
      "args": ["/path/to/email-mcp/index.js"],
      "env": {
        "GMAIL_CREDENTIALS": "/path/to/credentials.json"
      }
    },
    {
      "name": "browser",
      "command": "npx",
      "args": ["@anthropic/browser-mcp"],
      "env": {
        "HEADLESS": "true"
      }
    }
  ]
}
```

## Key File Structure
- `Dashboard.md`: Real-time summary of activities and status
- `Company_Handbook.md`: Rules of engagement and operational guidelines
- `Business_Goals.md`: Business objectives and metrics to track
- `/Needs_Action/`: Files created by watchers for Claude to process
- `/Plans/`: Generated plans for multi-step tasks
- `/Pending_Approval/`: Actions requiring human approval
- `/Done/`: Completed tasks
- `/Logs/`: Audit logs of all actions taken
- `.claude/skills/`: Comprehensive skill-based architecture for all system functions

## Security Patterns
- Store credentials in `.env` files (never commit to version control)
- Use environment variables for API keys
- Implement dry-run mode for all action scripts
- Set approval thresholds for different action types
- Maintain comprehensive audit logging
- Encrypt sensitive data at rest and in transit
- Implement role-based access control (RBAC)
- Use secure authentication mechanisms

## Common Development Tasks

### Adding a New Watcher
1. Extend the `BaseWatcher` abstract class
2. Implement `check_for_updates()` and `create_action_file()` methods
3. Add to PM2 process manager for persistent operation

### Creating MCP Server
1. Follow MCP protocol specifications
2. Define capabilities and permissions
3. Configure in `mcp.json` with appropriate environment variables

### Extending Approval Workflow
1. Create approval request files in `/Pending_Approval/` format
2. Implement orchestrator logic to watch for approval movements
3. Execute actions only after approval confirmation

### Adding a New Skill
1. Create a new directory in `.claude/skills/[skill_name]`
2. Create `SKILL.md` with comprehensive documentation
3. Create `reference/` directory with detailed guides
4. Create `scripts/` directory with implementation code
5. Implement proper error handling, audit logging, and security measures

## Troubleshooting

### Watchers Stopping
- Use PM2 or a custom watchdog to restart crashed processes
- Implement proper exception handling and logging

### MCP Connection Issues
- Verify server processes are running
- Check paths in `mcp.json` are absolute
- Review Claude Code logs for connection errors

### Credential Issues
- Ensure OAuth credentials are properly configured
- Check Google Cloud Console API settings
- Rotate credentials regularly

### Skill-Specific Issues
- Check skill-specific logs in `/Logs/[skill_name]/`
- Verify environment variables are properly set
- Ensure required dependencies are installed
- Review skill-specific documentation in `reference/` directory