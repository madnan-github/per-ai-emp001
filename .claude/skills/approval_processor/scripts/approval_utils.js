#!/usr/bin/env node

/**
 * Approval Processor Utility Functions
 *
 * This script provides utility functions for managing and interacting with
 * the approval processing system, including request creation, approval,
 * reporting, and management tools.
 */

const { ApprovalProcessor, ApprovalRequest, ApprovalAction, ApprovalStatus, ApprovalPriority } = require('./approval_processor.js');
const fs = require('fs').promises;
const path = require('path');

class ApprovalUtils {
    constructor(processor) {
        this.processor = processor;
    }

    /**
     * Create a new approval request programmatically
     */
    createRequest(options = {}) {
        const request = {
            requestorId: options.requestorId || 'manual',
            requestorName: options.requestorName || 'Manual Requestor',
            requestorEmail: options.requestorEmail || 'manual@company.com',
            approvalType: options.approvalType || 'general',
            category: options.category || 'general',
            amount: options.amount || 100.00,
            currency: options.currency || 'USD',
            description: options.description || 'Manual approval request',
            justification: options.justification || 'Requested manually',
            riskLevel: options.riskLevel || 'medium',
            priority: options.priority || ApprovalPriority.NORMAL,
            associatedDocuments: options.associatedDocuments || [],
            metadata: options.metadata || {}
        };

        return request;
    }

    /**
     * Filter requests by various criteria
     */
    filterRequests(requests, filters = {}) {
        return requests.filter(request => {
            // Filter by status
            if (filters.status && request.status !== filters.status) {
                return false;
            }

            // Filter by approval type
            if (filters.approvalType && request.approvalType !== filters.approvalType) {
                return false;
            }

            // Filter by category
            if (filters.category && request.category !== filters.category) {
                return false;
            }

            // Filter by amount range
            if (filters.minAmount && request.amount < filters.minAmount) {
                return false;
            }

            if (filters.maxAmount && request.amount > filters.maxAmount) {
                return false;
            }

            // Filter by date range
            if (filters.startDate && request.requestDate < new Date(filters.startDate).getTime()) {
                return false;
            }

            if (filters.endDate && request.requestDate > new Date(filters.endDate).getTime()) {
                return false;
            }

            // Filter by keyword in description or justification
            if (filters.keyword) {
                const keyword = filters.keyword.toLowerCase();
                const description = request.description.toLowerCase();
                const justification = request.justification.toLowerCase();

                if (!description.includes(keyword) && !justification.includes(keyword)) {
                    return false;
                }
            }

            // Filter by current approver
            if (filters.currentApprover && request.currentApproverId !== filters.currentApprover) {
                return false;
            }

            return true;
        });
    }

    /**
     * Get summary statistics for approval requests
     */
    getRequestStats(requests) {
        const stats = {
            total: requests.length,
            byStatus: {
                [ApprovalStatus.PENDING]: 0,
                [ApprovalStatus.APPROVED]: 0,
                [ApprovalStatus.REJECTED]: 0,
                [ApprovalStatus.CANCELLED]: 0,
                [ApprovalStatus.ESCALATED]: 0
            },
            byType: {},
            byCategory: {},
            byPriority: {
                [ApprovalPriority.LOW]: 0,
                [ApprovalPriority.NORMAL]: 0,
                [ApprovalPriority.HIGH]: 0,
                [ApprovalPriority.CRITICAL]: 0
            },
            totalAmount: 0,
            pendingAmount: 0
        };

        for (const request of requests) {
            // Count by status
            stats.byStatus[request.status]++;

            // Count by type
            if (!stats.byType[request.approvalType]) {
                stats.byType[request.approvalType] = 0;
            }
            stats.byType[request.approvalType]++;

            // Count by category
            if (!stats.byCategory[request.category]) {
                stats.byCategory[request.category] = 0;
            }
            stats.byCategory[request.category]++;

            // Count by priority
            stats.byPriority[request.priority]++;

            // Sum amounts
            stats.totalAmount += request.amount;

            if (request.status === ApprovalStatus.PENDING) {
                stats.pendingAmount += request.amount;
            }
        }

        return stats;
    }

    /**
     * Export requests to various formats
     */
    async exportRequests(requests, format = 'json', outputPath) {
        let content;

        switch (format.toLowerCase()) {
            case 'json':
                content = JSON.stringify(requests.map(r => ({
                    id: r.id,
                    requestorName: r.requestorName,
                    approvalType: r.approvalType,
                    category: r.category,
                    amount: r.amount,
                    currency: r.currency,
                    description: r.description,
                    status: r.status,
                    priority: ApprovalPriority.toString(r.priority),
                    requestDate: new Date(r.requestDate).toISOString(),
                    dueDate: new Date(r.dueDate).toISOString()
                })), null, 2);
                break;

            case 'csv':
                content = this.requestsToCSV(requests);
                break;

            case 'markdown':
                content = this.requestsToMarkdown(requests);
                break;

            default:
                throw new Error(`Unsupported export format: ${format}`);
        }

        if (outputPath) {
            await fs.writeFile(outputPath, content);
            console.log(`Requests exported to ${outputPath}`);
        }

        return content;
    }

    /**
     * Convert requests to CSV format
     */
    requestsToCSV(requests) {
        const headers = ['ID', 'Requestor', 'Type', 'Category', 'Amount', 'Currency', 'Description', 'Status', 'Priority', 'Request Date', 'Due Date'];
        const rows = [headers];

        for (const request of requests) {
            rows.push([
                request.id,
                `"${request.requestorName.replace(/"/g, '""')}"`,
                request.approvalType,
                request.category,
                request.amount,
                request.currency,
                `"${request.description.replace(/"/g, '""')}"`,
                request.status,
                ApprovalPriority.toString(request.priority),
                new Date(request.requestDate).toISOString(),
                new Date(request.dueDate).toISOString()
            ]);
        }

        return rows.map(row => row.join(',')).join('\n');
    }

    /**
     * Convert requests to Markdown format
     */
    requestsToMarkdown(requests) {
        let markdown = '# Approval Request Report\n\n';
        markdown += `Generated: ${new Date().toISOString()}\n\n`;

        for (const request of requests) {
            const priorityStr = ApprovalPriority.toString(request.priority).toUpperCase();
            markdown += `## Request #${request.id}\n\n`;
            markdown += `- **Requestor**: ${request.requestorName}\n`;
            markdown += `- **Type**: ${request.approvalType}\n`;
            markdown += `- **Category**: ${request.category}\n`;
            markdown += `- **Amount**: ${request.currency} ${request.amount}\n`;
            markdown += `- **Priority**: ${priorityStr}\n`;
            markdown += `- **Status**: ${request.status.toUpperCase()}\n`;
            markdown += `- **Request Date**: ${new Date(request.requestDate).toISOString()}\n`;
            markdown += `- **Due Date**: ${new Date(request.dueDate).toISOString()}\n\n`;
            markdown += `**Description:**\n${request.description}\n\n`;
            markdown += `**Justification:**\n${request.justification}\n\n---\n\n`;
        }

        return markdown;
    }

    /**
     * Import requests from a file (for testing purposes)
     */
    async importRequests(inputPath, format = 'json') {
        const content = await fs.readFile(inputPath, 'utf8');

        switch (format.toLowerCase()) {
            case 'json':
                const jsonData = JSON.parse(content);
                return jsonData.map(data => new ApprovalRequest(data));

            default:
                throw new Error(`Unsupported import format: ${format}`);
        }
    }

    /**
     * Get pending approvals for a specific approver
     */
    getPendingApprovals(approverId) {
        return this.processor.store.getPendingApprovals(approverId);
    }

    /**
     * Generate an approval summary report for a specific time period
     */
    generateSummaryReport(requests, startDate, endDate) {
        const filtered = this.filterRequests(requests, {
            startDate,
            endDate
        });

        const stats = this.getRequestStats(filtered);
        const pendingCount = stats.byStatus[ApprovalStatus.PENDING];
        const approvedCount = stats.byStatus[ApprovalStatus.APPROVED];
        const rejectedCount = stats.byStatus[ApprovalStatus.REJECTED];

        let report = `# Approval Summary Report\n\n`;
        report += `Period: ${new Date(startDate).toISOString()} to ${new Date(endDate).toISOString()}\n\n`;
        report += `## Summary\n`;
        report += `- Total requests: ${stats.total}\n`;
        report += `- Approved: ${approvedCount}\n`;
        report += `- Rejected: ${rejectedCount}\n`;
        report += `- Pending: ${pendingCount}\n`;
        report += `- Total amount: ${stats.totalAmount.toFixed(2)} USD\n`;
        report += `- Pending amount: ${stats.pendingAmount.toFixed(2)} USD\n\n`;

        if (pendingCount > 0) {
            report += `## Pending Requests\n`;
            const pendingRequests = this.filterRequests(filtered, { status: ApprovalStatus.PENDING });
            for (const request of pendingRequests) {
                report += `- **#${request.id}** ${request.description} (${request.currency} ${request.amount})\n`;
            }
            report += `\n`;
        }

        report += `## By Approval Type\n`;
        for (const [type, count] of Object.entries(stats.byType)) {
            report += `- ${type}: ${count}\n`;
        }

        report += `\n## By Category\n`;
        for (const [category, count] of Object.entries(stats.byCategory)) {
            report += `- ${category}: ${count}\n`;
        }

        report += `\n## By Priority\n`;
        for (const [priority, count] of Object.entries(stats.byPriority)) {
            report += `- ${ApprovalPriority.toString(priority)}: ${count}\n`;
        }

        return report;
    }

    /**
     * Find overdue requests
     */
    findOverdueRequests(requests) {
        const now = Date.now();
        return requests.filter(request =>
            request.status === ApprovalStatus.PENDING && request.dueDate < now
        );
    }

    /**
     * Escalate overdue requests
     */
    escalateOverdueRequests(requests, escalationNotes = 'Escalated due to overdue status') {
        const overdueRequests = this.findOverdueRequests(requests);
        const escalated = [];

        for (const request of overdueRequests) {
            // In a real implementation, this would update the request to an escalated status
            // For now, we'll just return the list of overdue requests
            escalated.push({
                id: request.id,
                description: request.description,
                overdueBy: Date.now() - request.dueDate
            });
        }

        console.log(`Identified ${overdueRequests.length} overdue requests for escalation`);
        return escalated;
    }

    /**
     * Generate compliance report
     */
    generateComplianceReport(requests, filters = {}) {
        const filtered = this.filterRequests(requests, filters);

        // Calculate compliance metrics
        const totalRequests = filtered.length;
        const approvedRequests = filtered.filter(r => r.status === ApprovalStatus.APPROVED).length;
        const rejectedRequests = filtered.filter(r => r.status === ApprovalStatus.REJECTED).length;
        const avgApprovalTime = this.calculateAverageApprovalTime(filtered);

        let report = `# Compliance Report\n\n`;
        report += `Generated: ${new Date().toISOString()}\n\n`;
        report += `## Compliance Metrics\n`;
        report += `- Total Requests: ${totalRequests}\n`;
        report += `- Approved: ${approvedRequests} (${totalRequests ? ((approvedRequests / totalRequests) * 100).toFixed(2) : 0}%)\n`;
        report += `- Rejected: ${rejectedRequests} (${totalRequests ? ((rejectedRequests / totalRequests) * 100).toFixed(2) : 0}%)\n`;
        report += `- Average Approval Time: ${avgApprovalTime} hours\n\n`;

        // Add detailed breakdown by category
        report += `## By Category\n`;
        const byCategory = {};
        for (const request of filtered) {
            if (!byCategory[request.category]) {
                byCategory[request.category] = { total: 0, approved: 0, rejected: 0 };
            }
            byCategory[request.category].total++;

            if (request.status === ApprovalStatus.APPROVED) {
                byCategory[request.category].approved++;
            } else if (request.status === ApprovalStatus.REJECTED) {
                byCategory[request.category].rejected++;
            }
        }

        for (const [category, metrics] of Object.entries(byCategory)) {
            report += `- ${category}: ${metrics.total} total (${metrics.approved} approved, ${metrics.rejected} rejected)\n`;
        }

        return report;
    }

    /**
     * Calculate average approval time
     */
    calculateAverageApprovalTime(requests) {
        let totalTime = 0;
        let completedCount = 0;

        for (const request of requests) {
            if (request.status === ApprovalStatus.APPROVED || request.status === ApprovalStatus.REJECTED) {
                // In a real system, we would calculate the time from submission to final decision
                // For this demo, we'll use a placeholder calculation
                totalTime += 24; // Assume 24 hours average for demo
                completedCount++;
            }
        }

        return completedCount > 0 ? (totalTime / completedCount) : 0;
    }
}

// Command line interface
async function main() {
    const args = process.argv.slice(2);

    // Check for help flag
    if (args.includes('--help') || args.includes('-h')) {
        console.log(`
Approval Processor Utility

Usage:
  node approval_utils.js [command] [options]

Commands:
  create <description> [options]          Create a new approval request
  list [options]                          List requests with filters
  stats [options]                         Show request statistics
  export <format> <output-file>          Export requests
  pending <approver-id>                  List pending approvals for approver
  report [options]                       Generate approval summary report
  overdue [options]                      Find overdue requests
  compliance [options]                   Generate compliance report

Options:
  --status <status>                      Filter by status (pending, approved, rejected, etc.)
  --type <type>                          Filter by approval type
  --category <category>                  Filter by category
  --min-amount <amount>                  Filter by minimum amount
  --max-amount <amount>                  Filter by maximum amount
  --keyword <keyword>                    Filter by keyword
  --start-date <date>                    Filter by start date (ISO format)
  --end-date <date>                      Filter by end date (ISO format)
  --approver <id>                        Filter by current approver
  --priority <level>                     Filter by priority (1-4)
  --config <path>                        Path to config file

Examples:
  node approval_utils.js create "New software license" --amount 1200 --type financial --category software
  node approval_utils.js list --status pending --approver john.doe
  node approval_utils.js export csv ./requests.csv
  node approval_utils.js stats
  node approval_utils.js pending john.doe
        `);
        return;
    }

    // Initialize processor
    let configPath = null;
    const configIndex = args.indexOf('--config');
    if (configIndex !== -1) {
        configPath = args[configIndex + 1];
    }

    const processor = new ApprovalProcessor(configPath);
    const utils = new ApprovalUtils(processor);

    // Parse command
    const command = args[0];
    const commandArgs = args.slice(1);

    try {
        switch (command) {
            case 'create':
                if (commandArgs.length < 1) {
                    console.error('Usage: create <description> [options]');
                    process.exit(1);
                }

                const description = commandArgs[0];

                // Parse options
                const options = { description };

                const amountIndex = commandArgs.indexOf('--amount');
                if (amountIndex !== -1) {
                    options.amount = parseFloat(commandArgs[amountIndex + 1]) || 100.00;
                }

                const typeIndex = commandArgs.indexOf('--type');
                if (typeIndex !== -1) {
                    options.approvalType = commandArgs[typeIndex + 1] || 'general';
                }

                const categoryIndex = commandArgs.indexOf('--category');
                if (categoryIndex !== -1) {
                    options.category = commandArgs[categoryIndex + 1] || 'general';
                }

                const priorityIndex = commandArgs.indexOf('--priority');
                if (priorityIndex !== -1) {
                    options.priority = parseInt(commandArgs[priorityIndex + 1]) || ApprovalPriority.NORMAL;
                }

                const request = utils.createRequest(options);
                const requestId = processor.submitRequest(request);
                console.log(`Created approval request: ${requestId}`);
                break;

            case 'list':
                const allRequests = processor.store.requests.map(r => new ApprovalRequest(r));
                const filtered = applyFilters(utils, allRequests, commandArgs);

                for (const request of filtered) {
                    const priorityStr = ApprovalPriority.toString(request.priority).toUpperCase();
                    console.log(`${request.status.toUpperCase()} [${priorityStr}] #${request.id}: ${request.description} (${request.currency} ${request.amount}) - ${request.requestorName}`);
                }
                break;

            case 'stats':
                const requests = processor.store.requests.map(r => new ApprovalRequest(r));
                const stats = utils.getRequestStats(requests);
                console.log('Approval Request Statistics:');
                console.log(JSON.stringify(stats, null, 2));
                break;

            case 'export':
                if (commandArgs.length < 2) {
                    console.error('Usage: export <format> <output-file>');
                    process.exit(1);
                }

                const exportFormat = commandArgs[0];
                const exportOutput = commandArgs[1];
                const allReqs = processor.store.requests.map(r => new ApprovalRequest(r));

                await utils.exportRequests(allReqs, exportFormat, exportOutput);
                break;

            case 'pending':
                if (commandArgs.length < 1) {
                    console.error('Usage: pending <approver-id>');
                    process.exit(1);
                }

                const approverId = commandArgs[0];
                const pendingApprovals = utils.getPendingApprovals(approverId);

                console.log(`Pending approvals for ${approverId}:`);
                for (const request of pendingApprovals) {
                    console.log(`  #${request.id}: ${request.description} (${request.currency} ${request.amount})`);
                }
                break;

            case 'report':
                const startDateIndex = commandArgs.indexOf('--start-date');
                const endDateIndex = commandArgs.indexOf('--end-date');

                const startDate = startDateIndex !== -1 ? new Date(commandArgs[startDateIndex + 1]).getTime() : Date.now() - (30 * 24 * 60 * 60 * 1000); // 30 days ago
                const endDate = endDateIndex !== -1 ? new Date(commandArgs[endDateIndex + 1]).getTime() : Date.now();

                const allReqsForReport = processor.store.requests.map(r => new ApprovalRequest(r));
                const report = utils.generateSummaryReport(allReqsForReport, startDate, endDate);
                console.log(report);
                break;

            case 'overdue':
                const allReqsForOverdue = processor.store.requests.map(r => new ApprovalRequest(r));
                const overdue = utils.findOverdueRequests(allReqsForOverdue);
                console.log(`Found ${overdue.length} overdue requests:`);
                for (const request of overdue) {
                    const overdueHours = Math.floor((Date.now() - request.dueDate) / (1000 * 60 * 60));
                    console.log(`  #${request.id}: ${request.description} (overdue by ${overdueHours} hours)`);
                }
                break;

            case 'compliance':
                const allReqsForCompliance = processor.store.requests.map(r => new ApprovalRequest(r));
                const complianceReport = utils.generateComplianceReport(allReqsForCompliance);
                console.log(complianceReport);
                break;

            default:
                console.error(`Unknown command: ${command}`);
                console.error('Use --help for usage information');
                process.exit(1);
        }
    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

// Helper function to apply filters from command line args
function applyFilters(utils, requests, args) {
    const filters = {};

    const statusIndex = args.indexOf('--status');
    if (statusIndex !== -1) {
        filters.status = args[statusIndex + 1];
    }

    const typeIndex = args.indexOf('--type');
    if (typeIndex !== -1) {
        filters.approvalType = args[typeIndex + 1];
    }

    const categoryIndex = args.indexOf('--category');
    if (categoryIndex !== -1) {
        filters.category = args[categoryIndex + 1];
    }

    const minAmountIndex = args.indexOf('--min-amount');
    if (minAmountIndex !== -1) {
        filters.minAmount = parseFloat(args[minAmountIndex + 1]);
    }

    const maxAmountIndex = args.indexOf('--max-amount');
    if (maxAmountIndex !== -1) {
        filters.maxAmount = parseFloat(args[maxAmountIndex + 1]);
    }

    const keywordIndex = args.indexOf('--keyword');
    if (keywordIndex !== -1) {
        filters.keyword = args[keywordIndex + 1];
    }

    const startDateIndex = args.indexOf('--start-date');
    if (startDateIndex !== -1) {
        filters.startDate = args[startDateIndex + 1];
    }

    const endDateIndex = args.indexOf('--end-date');
    if (endDateIndex !== -1) {
        filters.endDate = args[endDateIndex + 1];
    }

    const approverIndex = args.indexOf('--approver');
    if (approverIndex !== -1) {
        filters.currentApprover = args[approverIndex + 1];
    }

    const priorityIndex = args.indexOf('--priority');
    if (priorityIndex !== -1) {
        filters.priority = parseInt(args[priorityIndex + 1]);
    }

    return utils.filterRequests(requests, filters);
}

if (require.main === module) {
    main().catch(error => {
        console.error('Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { ApprovalUtils };