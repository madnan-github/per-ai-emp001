# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a "Personal AI Employee" project - an autonomous digital employee that operates 24/7 to manage personal and business affairs. The system is built around Claude Code as the reasoning engine with Obsidian as the local knowledge base and dashboard. The architecture follows a four-tier approach for comprehensive functionality and robust operations.

## Four-Tier Implementation Roadmap

The project is organized into four progressive tiers, each building upon the previous one:

### 1. Bronze Tier: Foundation (Minimum Viable Deliverable)
**Objective**: Establish core functionality and basic automation capabilities
**Status**: Current Implementation Level

**Core Components**:
- Basic watcher system (Gmail, WhatsApp, File System)
- Essential MCP servers (Email, Browser, Calendar, Slack)
- Human-in-the-loop approval workflow
- Basic skill architecture
- Core file structure and organization

**Key Features**:
- Monitor Gmail for important messages
- Monitor WhatsApp for messages
- Monitor file system events
- Send and receive emails via MCP
- Schedule calendar events
- Send Slack messages
- Basic file processing in `/Needs_Action/`
- Approval workflow in `/Pending_Approval/`
- Audit logging for all actions

**Implementation Requirements**:
- Initialize git repository
- Set up basic project structure
- Implement core watchers
- Configure MCP servers
- Create approval workflow
- Implement basic skills (Email Composer, Calendar Coordinator, File System MCP)
- Set up logging and audit trails

### 2. Silver Tier: Functional Assistant
**Objective**: Enhance automation with broader skill set and improved intelligence
**Prerequisites**: Complete Bronze Tier

**Core Components**:
- Expanded skill architecture
- Enhanced decision-making capabilities
- Advanced automation workflows
- Improved error handling and recovery

**Key Features**:
- Business management skills (Invoice Generator, Expense Tracker, Revenue Reporter)
- Personal assistance skills (Travel Planner, Meeting Scheduler)
- Communication skills (Social Media Poster, Customer Outreach)
- Advanced error handling and retry mechanisms
- Automated task scheduling
- Basic analytics and reporting

**Implementation Requirements**:
- Implement 15+ additional skills
- Create advanced workflow automation
- Add comprehensive error handling
- Implement task scheduling capabilities
- Add analytics and reporting features

### 3. Gold Tier: Autonomous Employee
**Objective**: Achieve high-level autonomy with learning and adaptation capabilities
**Prerequisites**: Complete Silver Tier

**Core Components**:
- Machine learning and adaptation systems
- Advanced decision-making algorithms
- Predictive analytics and forecasting
- Self-healing and recovery systems

**Key Features**:
- Learning & Adaptation system
- Predictive analytics for business decisions
- Automated optimization of workflows
- Self-monitoring and health checks
- Advanced security scanning
- Quality assurance automation
- Risk assessment and mitigation

**Implementation Requirements**:
- Implement ML-based learning system
- Add predictive analytics capabilities
- Create self-healing mechanisms
- Implement advanced security features
- Add quality assurance automation
- Integrate risk assessment tools

### 4. Platinum Tier: Always-On Cloud + Local Executive (Production-ish AI Employee)
**Objective**: Enterprise-grade, always-available system with cloud infrastructure
**Prerequisites**: Complete Gold Tier

**Core Components**:
- Cloud infrastructure and deployment
- High availability and redundancy
- Advanced security and compliance
- Enterprise monitoring and alerting

**Key Features**:
- Cloud-native deployment (Docker, Kubernetes)
- High availability and failover
- Enterprise-grade security
- Advanced monitoring and alerting
- Compliance and governance
- Scalable architecture
- Disaster recovery

**Implementation Requirements**:
- Containerize applications
- Implement cloud deployment
- Add high availability features
- Implement enterprise security
- Add advanced monitoring
- Create disaster recovery procedures

## Current Tier: Bronze Tier Implementation

### Bronze Tier - Core Components

#### Watcher System
- **Gmail Watcher**: Monitors Gmail for important/unread messages using the Gmail API
- **WhatsApp Watcher**: Uses Playwright to automate WhatsApp Web for message monitoring
- **File System Watcher**: Monitors file drops and system events
- **Calendar Watcher**: Monitors calendar events and appointments

#### MCP (Model Context Protocol) Servers
- **Email MCP**: Send, draft, and search emails
- **Browser MCP**: Navigate, click, fill forms for payment portals
- **Calendar MCP**: Create and update calendar events
- **Slack MCP**: Send messages and read channels
- **File System MCP**: Manage file operations and storage

#### Human-in-the-Loop (HITL) Pattern
- Critical actions require approval via file-based workflow
- Files created in `/Pending_Approval` folder require manual movement to `/Approved` to proceed
- Prevents unauthorized actions like payments or sensitive communications

#### Core Skills (Bronze Tier)
- **Email Composer**: Compose and send professional emails
- **Calendar Coordinator**: Manage calendar events and appointments
- **File System MCP**: Manage file operations and storage
- **Communication Logger**: Log all communications and interactions
- **Dashboard Updater**: Maintain real-time dashboard status

### Skill Architecture

The system utilizes a comprehensive skill-based architecture located in `.claude/skills/` directory. Each skill follows a standardized structure:

#### Skill Structure
Each skill contains:
- `SKILL.md`: Documentation with purpose, use cases, input parameters, processing logic, output formats, error handling, security considerations, and integration points
- `reference/`: Detailed documentation and guides for the skill
- `scripts/`: Implementation code for the skill functionality

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

### Git Branch Management
```bash
# Start with Bronze Tier (Foundation)
git checkout -b bronze-tier
# After completing Bronze Tier requirements:
git add .
git commit -m "Complete Bronze Tier: Foundation implementation"
git push origin bronze-tier

# Move to Silver Tier
git checkout -b silver-tier main  # or git checkout main && git pull && git checkout -b silver-tier
# Continue with Silver Tier implementation...

# Move to Gold Tier
git checkout -b gold-tier main
# Continue with Gold Tier implementation...

# Move to Platinum Tier
git checkout -b platinum-tier main
# Continue with Platinum Tier implementation...
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

## Available Skills

### Communication & Marketing
- **Email Composer**: Compose and send professional emails
- **Social Media Poster**: Post updates to social media platforms
- **Marketing Campaign Manager**: Plan and execute marketing campaigns
- **Customer Outreach**: Manage customer communication and outreach
- **Lead Generation**: Identify and qualify potential leads
- **Communication Logger**: Log all communications and interactions

### Business Management
- **Project Tracker**: Track project progress and deadlines
- **Task Scheduler**: Schedule and manage recurring tasks
- **Invoice Generator**: Generate invoices and billing documents
- **Expense Tracker**: Track expenses and costs
- **Revenue Reporter**: Generate revenue reports and analytics
- **Subscription Auditor**: Monitor and manage subscriptions
- **Bank Transaction Monitor**: Track bank transactions
- **Priority Evaluator**: Assess and prioritize tasks
- **Status Reporter**: Generate status reports and updates

### Personal Assistance
- **Calendar Coordinator**: Manage calendar events and appointments
- **Travel Planner**: Plan trips and travel arrangements
- **Meeting Scheduler**: Coordinate meeting schedules
- **Personal Finance Manager**: Track personal finances
- **Health & Wellness Tracker**: Monitor health and wellness goals

### Monitoring & Reporting
- **System Monitor**: Monitor system performance and health
- **Analytics Dashboard**: Generate analytics and insights
- **Performance Reporter**: Track and report performance metrics
- **Risk Assessor**: Evaluate and mitigate risks
- **Compliance Checker**: Ensure regulatory compliance
- **Performance Analyzer**: Analyze system performance metrics
- **Trend Identifier**: Identify trends and patterns in data

### Decision Making & Strategy
- **Decision Support**: Provide data-driven decision support
- **Strategic Planner**: Develop strategic plans
- **Market Research**: Conduct market research and analysis
- **Competitive Analysis**: Analyze competitors and market position
- **Financial Analyst**: Perform financial analysis and projections
- **Rule Interpreter**: Interpret and execute business rules
- **Anomaly Detector**: Detect anomalies and outliers in data
- **Policy Enforcer**: Enforce business policies and rules

### Development & Operations
- **Database Connector**: Connect to various databases for data retrieval
- **API Gateway**: Manage API communications with external services
- **File System MCP**: Manage file operations and storage
- **Payment Processor**: Handle financial transactions securely
- **Document Generator**: Create and format documents
- **Gmail Watcher**: Monitor Gmail for triggers and updates
- **WhatsApp Manager**: Manage WhatsApp communications
- **File System Watcher**: Monitor file system events

### System Infrastructure
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
- **Dashboard Updater**: Maintain real-time dashboard status

### Approval & Governance
- **Approval Processor**: Process and manage approval workflows
- **Weekly Business Briefing**: Generate weekly business summary reports

### Notification & Alerting
- **Notification Aggregator**: Consolidate and manage notifications

## Bronze Tier Implementation Checklist

### Phase 1: Repository Setup
- [x] Initialize git repository
- [x] Create project structure
- [x] Add initial files and documentation

### Phase 2: Core Infrastructure
- [ ] Implement basic watcher system
- [ ] Configure MCP servers
- [ ] Set up file structure and workflows

### Phase 3: Core Skills
- [ ] Implement Email Composer skill
- [ ] Implement Calendar Coordinator skill
- [ ] Implement File System MCP skill
- [ ] Implement Communication Logger skill
- [ ] Implement Dashboard Updater skill

### Phase 4: Approval Workflow
- [ ] Create approval workflow in `/Pending_Approval/`
- [ ] Implement approval processing logic
- [ ] Add audit logging for approvals

### Phase 5: Testing and Validation
- [ ] Test all core components
- [ ] Validate approval workflow
- [ ] Verify audit logging
- [ ] Complete Bronze Tier documentation

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

## Silver Tier Implementation Requirements

### Phase 1: Expanded Skill Architecture
- [ ] Implement Invoice Generator skill with templates and validation rules
- [ ] Implement Expense Tracker skill with receipt analysis capabilities
- [ ] Implement Revenue Reporter skill with analytics and metrics
- [ ] Implement Subscription Auditor skill with optimization rules
- [ ] Implement Bank Transaction Monitor skill with transaction categories
- [ ] Implement Task Scheduler skill with scheduling policies
- [ ] Implement Project Tracker skill with project phases and metrics
- [ ] Implement Priority Evaluator skill with evaluation criteria
- [ ] Implement Status Reporter skill with report templates
- [ ] Implement Social Media Poster skill with scheduling rules

### Phase 2: Enhanced Decision-Making
- [ ] Implement Rule Interpreter skill with configuration guide
- [ ] Implement Anomaly Detector skill with detection techniques
- [ ] Implement Risk Assessor skill with assessment framework
- [ ] Implement Trend Identifier skill with pattern recognition
- [ ] Implement Performance Analyzer skill with monitoring capabilities
- [ ] Implement Policy Enforcer skill with compliance checking
- [ ] Implement Approval Processor skill with workflow specs

### Phase 3: Advanced Automation
- [ ] Integrate all new skills with existing MCP infrastructure
- [ ] Implement advanced workflow automation between skills
- [ ] Create cross-skill communication protocols
- [ ] Implement task orchestration capabilities
- [ ] Add comprehensive error handling and retry mechanisms

### Phase 4: Analytics and Reporting
- [ ] Implement Weekly Business Briefing skill with briefing framework
- [ ] Create comprehensive analytics dashboard
- [ ] Implement business intelligence features
- [ ] Add predictive analytics capabilities
- [ ] Create executive summary reports

### Phase 5: Testing and Validation
- [ ] Test all new Silver Tier skills
- [ ] Validate cross-skill communication
- [ ] Verify workflow automation
- [ ] Confirm analytics and reporting accuracy
- [ ] Complete Silver Tier documentation

## Gold Tier Implementation Requirements

### Phase 1: Machine Learning and Adaptation
- [ ] Implement Learning & Adaptation skill with configuration guide and framework
- [ ] Implement Knowledge Base Updater skill with automated update mechanisms
- [ ] Create machine learning models for pattern recognition and anomaly detection
- [ ] Implement adaptive algorithms for workflow optimization
- [ ] Add intelligent recommendation systems for business decisions
- [ ] Implement neural networks for predictive modeling
- [ ] Create feedback loops for continuous learning

### Phase 2: Advanced Decision Making
- [ ] Implement predictive analytics engine for business decisions
- [ ] Create automated optimization of workflows using ML
- [ ] Add advanced risk assessment with quantitative models
- [ ] Implement intelligent resource allocation algorithms
- [ ] Add forecasting capabilities for revenue and expenses
- [ ] Create decision trees for complex business scenarios
- [ ] Implement cognitive reasoning for problem solving

### Phase 3: Self-Healing Systems
- [ ] Implement comprehensive self-monitoring and health checks
- [ ] Create automated recovery procedures for all system components
- [ ] Add fault tolerance mechanisms with redundancy
- [ ] Implement predictive maintenance using ML models
- [ ] Add system resilience features with auto-scaling
- [ ] Create automated backup and failover systems
- [ ] Implement chaos engineering for system resilience testing

### Phase 4: Advanced Security
- [ ] Implement Security Scanner skill with comprehensive vulnerability assessment
- [ ] Add Quality Assurance skill with automated testing framework
- [ ] Implement advanced authentication with biometric options
- [ ] Add security monitoring with real-time threat detection
- [ ] Create comprehensive vulnerability management system
- [ ] Implement zero-trust security architecture
- [ ] Add advanced encryption for data at rest and in transit

### Phase 5: Intelligent Automation
- [ ] Implement cognitive automation for complex tasks
- [ ] Add natural language processing for document analysis
- [ ] Create intelligent chatbot for customer interactions
- [ ] Implement computer vision for document processing
- [ ] Add robotic process automation (RPA) capabilities
- [ ] Create intelligent scheduling algorithms
- [ ] Implement autonomous decision-making capabilities

### Phase 6: Testing and Validation
- [ ] Test all Gold Tier capabilities in isolated environment
- [ ] Validate machine learning models with real-world data
- [ ] Confirm self-healing mechanisms under stress conditions
- [ ] Verify security implementations with penetration testing
- [ ] Complete Gold Tier documentation and training materials

## Platinum Tier Implementation Requirements

### Phase 1: Cloud Infrastructure
- [ ] Containerize all applications using Docker with optimized images
- [ ] Implement Kubernetes orchestration with auto-scaling
- [ ] Set up cloud-native CI/CD deployment pipelines
- [ ] Implement microservices architecture with service mesh
- [ ] Add intelligent load balancing and auto-scaling capabilities
- [ ] Create infrastructure as code (Terraform) templates
- [ ] Implement multi-cloud deployment capabilities

### Phase 2: High Availability & Resilience
- [ ] Implement geographically distributed redundant systems
- [ ] Add automated disaster recovery procedures with RTO/RPO targets
- [ ] Create automated backup and point-in-time recovery systems
- [ ] Implement multi-region geographic distribution
- [ ] Add continuous monitoring with predictive alerts
- [ ] Create circuit breaker and bulkhead patterns for resilience
- [ ] Implement blue-green deployment strategies

### Phase 3: Enterprise Features
- [ ] Implement enterprise-grade zero-trust security model
- [ ] Add comprehensive compliance and governance tools (SOC2, GDPR, etc.)
- [ ] Create secure multi-tenant architecture with data isolation
- [ ] Implement advanced identity and access management (IAM)
- [ ] Add comprehensive API management with rate limiting and quotas
- [ ] Create enterprise billing and subscription management
- [ ] Implement role-based access control (RBAC) with granular permissions

### Phase 4: Advanced Monitoring & Observability
- [ ] Implement comprehensive observability with metrics, logs, traces
- [ ] Add real-time performance analytics and business intelligence
- [ ] Create executive dashboards with customizable KPIs
- [ ] Implement automated incident response and on-call management
- [ ] Add predictive capacity planning and resource optimization
- [ ] Create advanced alerting with noise reduction
- [ ] Implement application performance monitoring (APM)

### Phase 5: Advanced AI & Automation
- [ ] Implement advanced AI/ML pipeline with model management
- [ ] Add continuous training and model revalidation systems
- [ ] Create autonomous operations (AutoOps) capabilities
- [ ] Implement intelligent workload optimization
- [ ] Add predictive analytics for business forecasting
- [ ] Create digital twin for system simulation and testing
- [ ] Implement federated learning for privacy-preserving AI

### Phase 6: Production Validation & Governance
- [ ] Test all Platinum Tier features in production-like environment with chaos engineering
- [ ] Validate scalability under realistic load with performance benchmarks
- [ ] Confirm high availability mechanisms with failover testing
- [ ] Verify disaster recovery procedures with recovery time objectives
- [ ] Complete comprehensive security audit and penetration testing
- [ ] Document all processes for operations and governance
- [ ] Create runbooks and incident response procedures

## Next Steps

1. Complete the Bronze Tier implementation checklist
2. Once Bronze Tier is complete, create the `silver-tier` branch
3. Implement Silver Tier requirements following the detailed checklist above
4. After Silver Tier completion, create the `gold-tier` branch
5. Implement Gold Tier requirements following the detailed checklist above
6. After Gold Tier completion, create the `platinum-tier` branch
7. Implement Platinum Tier requirements following the detailed checklist above