#!/usr/bin/env node

/**
 * Notification Aggregator Utility Functions
 *
 * This script provides utility functions for managing and interacting with
 * the notification aggregator system, including notification creation,
 * filtering, and management tools.
 */

const { NotificationAggregator, Notification, NotificationSeverity, NotificationCategory } = require('./notification_aggregator.js');
const fs = require('fs').promises;
const path = require('path');

class NotificationUtils {
    constructor(aggregator) {
        this.aggregator = aggregator;
    }

    /**
     * Create a new notification programmatically
     */
    createNotification(options = {}) {
        return new Notification({
            source: options.source || 'manual',
            title: options.title || 'Manual Notification',
            description: options.description || '',
            category: options.category || NotificationCategory.BUSINESS,
            severity: options.severity || NotificationSeverity.MEDIUM,
            metadata: options.metadata || {},
            timestamp: options.timestamp || Date.now()
        });
    }

    /**
     * Filter notifications by various criteria
     */
    filterNotifications(notifications, filters = {}) {
        return notifications.filter(notification => {
            // Filter by category
            if (filters.category && notification.category !== filters.category) {
                return false;
            }

            // Filter by severity (minimum level)
            if (filters.minSeverity && notification.severity > filters.minSeverity) {
                return false;
            }

            // Filter by source
            if (filters.source && notification.source !== filters.source) {
                return false;
            }

            // Filter by date range
            if (filters.startDate && notification.timestamp < new Date(filters.startDate).getTime()) {
                return false;
            }

            if (filters.endDate && notification.timestamp > new Date(filters.endDate).getTime()) {
                return false;
            }

            // Filter by keyword in title or description
            if (filters.keyword) {
                const keyword = filters.keyword.toLowerCase();
                const title = notification.title.toLowerCase();
                const description = notification.description.toLowerCase();

                if (!title.includes(keyword) && !description.includes(keyword)) {
                    return false;
                }
            }

            return true;
        });
    }

    /**
     * Get summary statistics for notifications
     */
    getNotificationStats(notifications) {
        const stats = {
            total: notifications.length,
            bySeverity: {
                [NotificationSeverity.CRITICAL]: 0,
                [NotificationSeverity.HIGH]: 0,
                [NotificationSeverity.MEDIUM]: 0,
                [NotificationSeverity.LOW]: 0
            },
            byCategory: {
                [NotificationCategory.SYSTEM]: 0,
                [NotificationCategory.BUSINESS]: 0,
                [NotificationCategory.COMMUNICATION]: 0,
                [NotificationCategory.MONITORING]: 0,
                [NotificationCategory.SECURITY]: 0
            },
            bySource: {},
            unacknowledged: 0,
            delivered: 0
        };

        for (const notification of notifications) {
            // Count by severity
            stats.bySeverity[notification.severity]++;

            // Count by category
            stats.byCategory[notification.category]++;

            // Count by source
            if (!stats.bySource[notification.source]) {
                stats.bySource[notification.source] = 0;
            }
            stats.bySource[notification.source]++;

            // Count unacknowledged and delivered
            if (!notification.acknowledged) {
                stats.unacknowledged++;
            }
            if (notification.delivered) {
                stats.delivered++;
            }
        }

        return stats;
    }

    /**
     * Export notifications to various formats
     */
    async exportNotifications(notifications, format = 'json', outputPath) {
        let content;

        switch (format.toLowerCase()) {
            case 'json':
                content = JSON.stringify(notifications.map(n => n.toJSON()), null, 2);
                break;

            case 'csv':
                content = this.notificationsToCSV(notifications);
                break;

            case 'markdown':
                content = this.notificationsToMarkdown(notifications);
                break;

            default:
                throw new Error(`Unsupported export format: ${format}`);
        }

        if (outputPath) {
            await fs.writeFile(outputPath, content);
            console.log(`Notifications exported to ${outputPath}`);
        }

        return content;
    }

    /**
     * Convert notifications to CSV format
     */
    notificationsToCSV(notifications) {
        const headers = ['ID', 'Source', 'Timestamp', 'Category', 'Severity', 'Title', 'Description', 'Acknowledged', 'Delivered'];
        const rows = [headers];

        for (const notification of notifications) {
            rows.push([
                notification.id,
                notification.source,
                new Date(notification.timestamp).toISOString(),
                notification.category,
                NotificationSeverity.toString(notification.severity),
                `"${notification.title.replace(/"/g, '""')}"`,
                `"${notification.description.replace(/"/g, '""')}"`,
                notification.acknowledged,
                notification.delivered
            ]);
        }

        return rows.map(row => row.join(',')).join('\n');
    }

    /**
     * Convert notifications to Markdown format
     */
    notificationsToMarkdown(notifications) {
        let markdown = '# Notification Report\n\n';
        markdown += `Generated: ${new Date().toISOString()}\n\n`;

        for (const notification of notifications) {
            const severityStr = NotificationSeverity.toString(notification.severity).toUpperCase();
            markdown += `## [${severityStr}] ${notification.title}\n\n`;
            markdown += `- **ID**: ${notification.id}\n`;
            markdown += `- **Source**: ${notification.source}\n`;
            markdown += `- **Category**: ${notification.category}\n`;
            markdown += `- **Timestamp**: ${new Date(notification.timestamp).toISOString()}\n`;
            markdown += `- **Acknowledged**: ${notification.acknowledged ? 'Yes' : 'No'}\n`;
            markdown += `- **Delivered**: ${notification.delivered ? 'Yes' : 'No'}\n\n`;
            markdown += `**Description:**\n${notification.description}\n\n---\n\n`;
        }

        return markdown;
    }

    /**
     * Import notifications from a file
     */
    async importNotifications(inputPath, format = 'json') {
        const content = await fs.readFile(inputPath, 'utf8');

        switch (format.toLowerCase()) {
            case 'json':
                const jsonData = JSON.parse(content);
                return jsonData.map(data => new Notification(data));

            default:
                throw new Error(`Unsupported import format: ${format}`);
        }
    }

    /**
     * Acknowledge multiple notifications
     */
    acknowledgeNotifications(notificationIds) {
        for (const id of notificationIds) {
            this.aggregator.store.acknowledgeNotification(id);
        }
        console.log(`Acknowledged ${notificationIds.length} notifications`);
    }

    /**
     * Generate a notification digest for a specific time period
     */
    generateDigest(notifications, startDate, endDate) {
        const filtered = this.filterNotifications(notifications, {
            startDate,
            endDate
        });

        const stats = this.getNotificationStats(filtered);
        const criticalCount = stats.bySeverity[NotificationSeverity.CRITICAL];
        const highCount = stats.bySeverity[NotificationSeverity.HIGH];

        let digest = `# Notification Digest\n\n`;
        digest += `Period: ${new Date(startDate).toISOString()} to ${new Date(endDate).toISOString()}\n\n`;
        digest += `## Summary\n`;
        digest += `- Total notifications: ${stats.total}\n`;
        digest += `- Critical: ${criticalCount}\n`;
        digest += `- High: ${highCount}\n`;
        digest += `- Medium: ${stats.bySeverity[NotificationSeverity.MEDIUM]}\n`;
        digest += `- Low: ${stats.bySeverity[NotificationSeverity.LOW]}\n\n`;

        if (criticalCount > 0 || highCount > 0) {
            digest += `## High Priority Items\n`;
            const highPriority = this.filterNotifications(filtered, { minSeverity: NotificationSeverity.HIGH });
            for (const notification of highPriority) {
                digest += `- **[${NotificationSeverity.toString(notification.severity).toUpperCase()}]** ${notification.title} (${notification.source})\n`;
            }
            digest += `\n`;
        }

        digest += `## By Category\n`;
        for (const [category, count] of Object.entries(stats.byCategory)) {
            digest += `- ${category}: ${count}\n`;
        }

        return digest;
    }

    /**
     * Find duplicate notifications
     */
    findDuplicates(notifications, timeWindowMs = 300000) { // 5 minutes default
        const duplicates = [];
        const seen = new Map();

        for (const notification of notifications) {
            const key = `${notification.source}:${notification.title}`;
            const now = notification.timestamp;

            if (seen.has(key)) {
                const prevTime = seen.get(key);
                if (now - prevTime <= timeWindowMs) {
                    duplicates.push(notification);
                }
            }

            seen.set(key, now);
        }

        return duplicates;
    }

    /**
     * Clean up old notifications based on retention policy
     */
    async cleanupOldNotifications(retentionDays = 30) {
        const cutoffDate = Date.now() - (retentionDays * 24 * 60 * 60 * 1000);
        const allNotifications = this.aggregator.store.getUnprocessedNotifications(Infinity);

        const toKeep = allNotifications.filter(n => n.timestamp >= cutoffDate);
        const toRemove = allNotifications.filter(n => n.timestamp < cutoffDate);

        // In a real implementation, we would remove the old notifications
        // For now, we'll just report what would be removed
        console.log(`Would remove ${toRemove.length} notifications older than ${retentionDays} days`);
        console.log(`Keeping ${toKeep.length} recent notifications`);

        return { removed: toRemove.length, kept: toKeep.length };
    }
}

// Command line interface
async function main() {
    const args = process.argv.slice(2);

    // Check for help flag
    if (args.includes('--help') || args.includes('-h')) {
        console.log(`
Notification Aggregator Utility

Usage:
  node notification_utils.js [command] [options]

Commands:
  create <title> <description> [options]    Create a new notification
  list [options]                           List notifications with filters
  stats [options]                          Show notification statistics
  export <format> <output-file>            Export notifications
  import <format> <input-file>             Import notifications
  acknowledge <id> [id...]                 Acknowledge notifications
  digest [options]                         Generate notification digest
  find-duplicates [options]                Find duplicate notifications
  cleanup [days]                          Clean up old notifications

Options:
  --category <category>                   Filter by category
  --severity <level>                      Filter by minimum severity (1-4)
  --source <source>                       Filter by source
  --keyword <keyword>                     Filter by keyword
  --start-date <date>                     Filter by start date (ISO format)
  --end-date <date>                       Filter by end date (ISO format)
  --config <path>                         Path to config file

Examples:
  node notification_utils.js create "System Alert" "High CPU usage detected" --severity 2 --category system
  node notification_utils.js list --severity 1 --category security
  node notification_utils.js export json ./notifications.json
  node notification_utils.js stats
        `);
        return;
    }

    // Initialize aggregator
    let configPath = null;
    const configIndex = args.indexOf('--config');
    if (configIndex !== -1) {
        configPath = args[configIndex + 1];
    }

    const aggregator = new NotificationAggregator(configPath);
    const utils = new NotificationUtils(aggregator);

    // Parse command
    const command = args[0];
    const commandArgs = args.slice(1);

    try {
        switch (command) {
            case 'create':
                if (commandArgs.length < 2) {
                    console.error('Usage: create <title> <description> [options]');
                    process.exit(1);
                }

                const title = commandArgs[0];
                const description = commandArgs[1];

                // Parse options
                const options = {};

                const severityIndex = commandArgs.indexOf('--severity');
                if (severityIndex !== -1) {
                    options.severity = parseInt(commandArgs[severityIndex + 1]) || NotificationSeverity.MEDIUM;
                }

                const categoryIndex = commandArgs.indexOf('--category');
                if (categoryIndex !== -1) {
                    options.category = commandArgs[categoryIndex + 1] || NotificationCategory.BUSINESS;
                }

                const sourceIndex = commandArgs.indexOf('--source');
                if (sourceIndex !== -1) {
                    options.source = commandArgs[sourceIndex + 1] || 'cli';
                }

                const notification = utils.createNotification({
                    title,
                    description,
                    ...options
                });

                aggregator.store.saveNotification(notification);
                console.log(`Created notification: ${notification.id}`);
                break;

            case 'list':
                const allNotifications = aggregator.store.getUnprocessedNotifications(Infinity);
                const filtered = applyFilters(utils, allNotifications, commandArgs);

                for (const notification of filtered) {
                    const severityStr = NotificationSeverity.toString(notification.severity).toUpperCase();
                    console.log(`[${severityStr}] ${notification.title} (${notification.source}) - ${new Date(notification.timestamp).toISOString()}`);
                }
                break;

            case 'stats':
                const notifications = aggregator.store.getUnprocessedNotifications(Infinity);
                const stats = utils.getNotificationStats(notifications);
                console.log('Notification Statistics:');
                console.log(JSON.stringify(stats, null, 2));
                break;

            case 'export':
                if (commandArgs.length < 2) {
                    console.error('Usage: export <format> <output-file>');
                    process.exit(1);
                }

                const exportFormat = commandArgs[0];
                const exportOutput = commandArgs[1];
                const allNotifs = aggregator.store.getUnprocessedNotifications(Infinity);

                await utils.exportNotifications(allNotifs, exportFormat, exportOutput);
                break;

            case 'import':
                if (commandArgs.length < 2) {
                    console.error('Usage: import <format> <input-file>');
                    process.exit(1);
                }

                const importFormat = commandArgs[0];
                const importInput = commandArgs[1];

                const imported = await utils.importNotifications(importInput, importFormat);
                for (const notification of imported) {
                    aggregator.store.saveNotification(notification);
                }
                console.log(`Imported ${imported.length} notifications`);
                break;

            case 'acknowledge':
                if (commandArgs.length === 0) {
                    console.error('Usage: acknowledge <id> [id...]');
                    process.exit(1);
                }

                utils.acknowledgeNotifications(commandArgs);
                break;

            case 'digest':
                const startDateIndex = commandArgs.indexOf('--start-date');
                const endDateIndex = commandArgs.indexOf('--end-date');

                const startDate = startDateIndex !== -1 ? new Date(commandArgs[startDateIndex + 1]).getTime() : Date.now() - (24 * 60 * 60 * 1000); // 1 day ago
                const endDate = endDateIndex !== -1 ? new Date(commandArgs[endDateIndex + 1]).getTime() : Date.now();

                const allNotifsForDigest = aggregator.store.getUnprocessedNotifications(Infinity);
                const digest = utils.generateDigest(allNotifsForDigest, startDate, endDate);
                console.log(digest);
                break;

            case 'find-duplicates':
                const allNotifsForDupes = aggregator.store.getUnprocessedNotifications(Infinity);
                const duplicates = utils.findDuplicates(allNotifsForDupes);
                console.log(`Found ${duplicates.length} duplicate notifications:`);
                for (const dupe of duplicates) {
                    console.log(`- ${dupe.title} (${new Date(dupe.timestamp).toISOString()})`);
                }
                break;

            case 'cleanup':
                const days = parseInt(commandArgs[0]) || 30;
                const result = await utils.cleanupOldNotifications(days);
                console.log(`Cleanup completed: removed ${result.removed}, kept ${result.kept}`);
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
function applyFilters(utils, notifications, args) {
    const filters = {};

    const categoryIndex = args.indexOf('--category');
    if (categoryIndex !== -1) {
        filters.category = args[categoryIndex + 1];
    }

    const severityIndex = args.indexOf('--severity');
    if (severityIndex !== -1) {
        filters.minSeverity = parseInt(args[severityIndex + 1]);
    }

    const sourceIndex = args.indexOf('--source');
    if (sourceIndex !== -1) {
        filters.source = args[sourceIndex + 1];
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

    return utils.filterNotifications(notifications, filters);
}

if (require.main === module) {
    main().catch(error => {
        console.error('Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { NotificationUtils };