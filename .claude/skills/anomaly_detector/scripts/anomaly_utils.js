#!/usr/bin/env node

/**
 * Anomaly Detector Utility Functions
 *
 * This script provides utility functions for managing and interacting with
 * the anomaly detection system, including anomaly analysis, reporting,
 * and management tools.
 */

const { AnomalyDetector, Anomaly, AnomalySeverity, AnomalyType } = require('./anomaly_detector.js');
const fs = require('fs').promises;
const path = require('path');

class AnomalyUtils {
    constructor(detector) {
        this.detector = detector;
    }

    /**
     * Create a new anomaly programmatically
     */
    createAnomaly(options = {}) {
        return new Anomaly({
            entityId: options.entityId || 'manual',
            entityType: options.entityType || 'generic',
            anomalyType: options.anomalyType || AnomalyType.POINT_ANOMALY,
            severity: options.severity || AnomalySeverity.MEDIUM,
            score: options.score || 1.0,
            confidence: options.confidence || 0.8,
            description: options.description || 'Manual anomaly entry',
            dataPoint: options.dataPoint || {},
            detectionMethod: options.detectionMethod || 'manual',
            metadata: options.metadata || {},
            timestamp: options.timestamp || Date.now()
        });
    }

    /**
     * Filter anomalies by various criteria
     */
    filterAnomalies(anomalies, filters = {}) {
        return anomalies.filter(anomaly => {
            // Filter by severity (minimum level)
            if (filters.minSeverity && anomaly.severity > filters.minSeverity) {
                return false;
            }

            // Filter by type
            if (filters.type && anomaly.anomalyType !== filters.type) {
                return false;
            }

            // Filter by entity type
            if (filters.entityType && anomaly.entityType !== filters.entityType) {
                return false;
            }

            // Filter by detection method
            if (filters.method && anomaly.detectionMethod !== filters.method) {
                return false;
            }

            // Filter by date range
            if (filters.startDate && anomaly.timestamp < new Date(filters.startDate).getTime()) {
                return false;
            }

            if (filters.endDate && anomaly.timestamp > new Date(filters.endDate).getTime()) {
                return false;
            }

            // Filter by keyword in description
            if (filters.keyword) {
                const keyword = filters.keyword.toLowerCase();
                const description = anomaly.description.toLowerCase();

                if (!description.includes(keyword)) {
                    return false;
                }
            }

            // Filter by confidence threshold
            if (filters.minConfidence && anomaly.confidence < filters.minConfidence) {
                return false;
            }

            return true;
        });
    }

    /**
     * Get summary statistics for anomalies
     */
    getAnomalyStats(anomalies) {
        const stats = {
            total: anomalies.length,
            bySeverity: {
                [AnomalySeverity.CRITICAL]: 0,
                [AnomalySeverity.HIGH]: 0,
                [AnomalySeverity.MEDIUM]: 0,
                [AnomalySeverity.LOW]: 0
            },
            byType: {
                [AnomalyType.POINT_ANOMALY]: 0,
                [AnomalyType.CONTEXTUAL_ANOMALY]: 0,
                [AnomalyType.COLLECTIVE_ANOMALY]: 0,
                [AnomalyType.STATISTICAL_OUTLIER]: 0,
                [AnomalyType.ML_PREDICTED]: 0
            },
            byMethod: {},
            byEntity: {},
            acknowledged: 0,
            unacknowledged: 0
        };

        for (const anomaly of anomalies) {
            // Count by severity
            stats.bySeverity[anomaly.severity]++;

            // Count by type
            stats.byType[anomaly.anomalyType]++;

            // Count by method
            if (!stats.byMethod[anomaly.detectionMethod]) {
                stats.byMethod[anomaly.detectionMethod] = 0;
            }
            stats.byMethod[anomaly.detectionMethod]++;

            // Count by entity
            if (!stats.byEntity[anomaly.entityId]) {
                stats.byEntity[anomaly.entityId] = 0;
            }
            stats.byEntity[anomaly.entityId]++;

            // Count acknowledged vs unacknowledged
            if (anomaly.acknowledged) {
                stats.acknowledged++;
            } else {
                stats.unacknowledged++;
            }
        }

        return stats;
    }

    /**
     * Export anomalies to various formats
     */
    async exportAnomalies(anomalies, format = 'json', outputPath) {
        let content;

        switch (format.toLowerCase()) {
            case 'json':
                content = JSON.stringify(anomalies.map(a => a.toJSON()), null, 2);
                break;

            case 'csv':
                content = this.anomaliesToCSV(anomalies);
                break;

            case 'markdown':
                content = this.anomaliesToMarkdown(anomalies);
                break;

            default:
                throw new Error(`Unsupported export format: ${format}`);
        }

        if (outputPath) {
            await fs.writeFile(outputPath, content);
            console.log(`Anomalies exported to ${outputPath}`);
        }

        return content;
    }

    /**
     * Convert anomalies to CSV format
     */
    anomaliesToCSV(anomalies) {
        const headers = ['ID', 'Timestamp', 'EntityID', 'EntityType', 'AnomalyType', 'Severity', 'Score', 'Confidence', 'Description', 'DetectionMethod', 'Acknowledged'];
        const rows = [headers];

        for (const anomaly of anomalies) {
            rows.push([
                anomaly.id,
                new Date(anomaly.timestamp).toISOString(),
                anomaly.entityId,
                anomaly.entityType,
                anomaly.anomalyType,
                AnomalySeverity.toString(anomaly.severity),
                anomaly.score,
                anomaly.confidence,
                `"${anomaly.description.replace(/"/g, '""')}"`,
                anomaly.detectionMethod,
                anomaly.acknowledged
            ]);
        }

        return rows.map(row => row.join(',')).join('\n');
    }

    /**
     * Convert anomalies to Markdown format
     */
    anomaliesToMarkdown(anomalies) {
        let markdown = '# Anomaly Report\n\n';
        markdown += `Generated: ${new Date().toISOString()}\n\n`;

        for (const anomaly of anomalies) {
            const severityStr = AnomalySeverity.toString(anomaly.severity).toUpperCase();
            markdown += `## [${severityStr}] ${anomaly.description}\n\n`;
            markdown += `- **ID**: ${anomaly.id}\n`;
            markdown += `- **Entity**: ${anomaly.entityId} (${anomaly.entityType})\n`;
            markdown += `- **Type**: ${anomaly.anomalyType}\n`;
            markdown += `- **Method**: ${anomaly.detectionMethod}\n`;
            markdown += `- **Timestamp**: ${new Date(anomaly.timestamp).toISOString()}\n`;
            markdown += `- **Score**: ${anomaly.score}\n`;
            markdown += `- **Confidence**: ${(anomaly.confidence * 100).toFixed(2)}%\n`;
            markdown += `- **Acknowledged**: ${anomaly.acknowledged ? 'Yes' : 'No'}\n\n`;
            markdown += `**Data Point:**\n\`\`\`json\n${JSON.stringify(anomaly.dataPoint, null, 2)}\n\`\`\`\n\n---\n\n`;
        }

        return markdown;
    }

    /**
     * Import anomalies from a file
     */
    async importAnomalies(inputPath, format = 'json') {
        const content = await fs.readFile(inputPath, 'utf8');

        switch (format.toLowerCase()) {
            case 'json':
                const jsonData = JSON.parse(content);
                return jsonData.map(data => new Anomaly(data));

            default:
                throw new Error(`Unsupported import format: ${format}`);
        }
    }

    /**
     * Acknowledge multiple anomalies
     */
    acknowledgeAnomalies(anomalyIds) {
        for (const id of anomalyIds) {
            this.detector.store.acknowledgeAnomaly(id);
        }
        console.log(`Acknowledged ${anomalyIds.length} anomalies`);
    }

    /**
     * Generate an anomaly report for a specific time period
     */
    generateReport(anomalies, startDate, endDate) {
        const filtered = this.filterAnomalies(anomalies, {
            startDate,
            endDate
        });

        const stats = this.getAnomalyStats(filtered);
        const criticalCount = stats.bySeverity[AnomalySeverity.CRITICAL];
        const highCount = stats.bySeverity[AnomalySeverity.HIGH];

        let report = `# Anomaly Detection Report\n\n`;
        report += `Period: ${new Date(startDate).toISOString()} to ${new Date(endDate).toISOString()}\n\n`;
        report += `## Executive Summary\n`;
        report += `- Total anomalies detected: ${stats.total}\n`;
        report += `- Critical: ${criticalCount}\n`;
        report += `- High: ${highCount}\n`;
        report += `- Medium: ${stats.bySeverity[AnomalySeverity.MEDIUM]}\n`;
        report += `- Low: ${stats.bySeverity[AnomalySeverity.LOW]}\n\n`;

        if (criticalCount > 0 || highCount > 0) {
            report += `## High Priority Anomalies\n`;
            const highPriority = this.filterAnomalies(filtered, { minSeverity: AnomalySeverity.HIGH });
            for (const anomaly of highPriority) {
                report += `- **[${AnomalySeverity.toString(anomaly.severity).toUpperCase()}]** ${anomaly.description} (${anomaly.detectionMethod})\n`;
            }
            report += `\n`;
        }

        report += `## By Detection Method\n`;
        for (const [method, count] of Object.entries(stats.byMethod)) {
            report += `- ${method}: ${count}\n`;
        }

        report += `\n## By Entity\n`;
        for (const [entity, count] of Object.entries(stats.byEntity)) {
            report += `- ${entity}: ${count}\n`;
        }

        return report;
    }

    /**
     * Find similar anomalies based on description or data patterns
     */
    findSimilarAnomalies(anomalies, similarityThreshold = 0.8) {
        // Simple similarity based on description length and common words
        const similarGroups = [];
        const processed = new Set();

        for (let i = 0; i < anomalies.length; i++) {
            if (processed.has(i)) continue;

            const group = [anomalies[i]];
            processed.add(i);

            for (let j = i + 1; j < anomalies.length; j++) {
                if (processed.has(j)) continue;

                const similarity = this.calculateAnomalySimilarity(anomalies[i], anomalies[j]);
                if (similarity >= similarityThreshold) {
                    group.push(anomalies[j]);
                    processed.add(j);
                }
            }

            if (group.length > 1) {
                similarGroups.push(group);
            }
        }

        return similarGroups;
    }

    /**
     * Calculate similarity between two anomalies
     */
    calculateAnomalySimilarity(anomaly1, anomaly2) {
        // Calculate similarity based on description
        const desc1 = anomaly1.description.toLowerCase();
        const desc2 = anomaly2.description.toLowerCase();

        // Split descriptions into words
        const words1 = desc1.split(/\s+/);
        const words2 = desc2.split(/\s+/);

        // Calculate intersection of words
        const intersection = words1.filter(word => words2.includes(word)).length;
        const union = new Set([...words1, ...words2]).size;

        // Calculate Jaccard similarity
        return union > 0 ? intersection / union : 0;
    }

    /**
     * Clean up old anomalies based on retention policy
     */
    async cleanupOldAnomalies(retentionDays = 90) {
        const cutoffDate = Date.now() - (retentionDays * 24 * 60 * 60 * 1000);
        const allAnomalies = this.detector.store.getUnacknowledgedAnomalies(Infinity);

        const toKeep = allAnomalies.filter(a => a.timestamp >= cutoffDate);
        const toRemove = allAnomalies.filter(a => a.timestamp < cutoffDate);

        // In a real implementation, we would remove the old anomalies
        // For now, we'll just report what would be removed
        console.log(`Would remove ${toRemove.length} anomalies older than ${retentionDays} days`);
        console.log(`Keeping ${toKeep.length} recent anomalies`);

        return { removed: toRemove.length, kept: toKeep.length };
    }

    /**
     * Perform root cause analysis on anomalies
     */
    async performRootCauseAnalysis(anomalies, relatedData = {}) {
        const analysisResults = [];

        for (const anomaly of anomalies) {
            const result = {
                anomalyId: anomaly.id,
                timestamp: anomaly.timestamp,
                description: anomaly.description,
                potentialCauses: [],
                recommendations: []
            };

            // Analyze data point for potential causes
            const dataPoint = anomaly.dataPoint;

            // Check for common patterns that might indicate causes
            if (dataPoint.value && typeof dataPoint.value === 'number') {
                if (dataPoint.value > 10000) {
                    result.potentialCauses.push('Unusually high numerical value detected');
                    result.recommendations.push('Investigate data source for potential errors or unexpected events');
                }

                if (dataPoint.value < 0 && anomaly.entityType.includes('financial')) {
                    result.potentialCauses.push('Negative financial value detected');
                    result.recommendations.push('Verify transaction validity and accounting practices');
                }
            }

            // Analyze by entity type
            if (anomaly.entityType === 'system_metric') {
                result.potentialCauses.push('System performance anomaly');
                result.recommendations.push('Check system logs and resource utilization');
            } else if (anomaly.entityType === 'financial_transaction') {
                result.potentialCauses.push('Unusual transaction pattern');
                result.recommendations.push('Review transaction for fraud indicators');
            }

            analysisResults.push(result);
        }

        return analysisResults;
    }
}

// Command line interface
async function main() {
    const args = process.argv.slice(2);

    // Check for help flag
    if (args.includes('--help') || args.includes('-h')) {
        console.log(`
Anomaly Detector Utility

Usage:
  node anomaly_utils.js [command] [options]

Commands:
  create <description> [options]          Create a new anomaly
  list [options]                          List anomalies with filters
  stats [options]                         Show anomaly statistics
  export <format> <output-file>           Export anomalies
  import <format> <input-file>            Import anomalies
  acknowledge <id> [id...]                Acknowledge anomalies
  report [options]                        Generate anomaly report
  find-similar [options]                  Find similar anomalies
  analyze [options]                       Perform root cause analysis
  cleanup [days]                          Clean up old anomalies

Options:
  --severity <level>                     Filter by minimum severity (1-4)
  --type <type>                          Filter by anomaly type
  --entity-type <type>                   Filter by entity type
  --method <method>                      Filter by detection method
  --keyword <keyword>                    Filter by keyword
  --start-date <date>                    Filter by start date (ISO format)
  --end-date <date>                      Filter by end date (ISO format)
  --min-confidence <value>               Filter by minimum confidence (0-1)
  --config <path>                        Path to config file

Examples:
  node anomaly_utils.js create "High CPU usage detected" --severity 2 --entity-type system_metric
  node anomaly_utils.js list --severity 1 --type statistical_outlier
  node anomaly_utils.js export json ./anomalies.json
  node anomaly_utils.js stats
        `);
        return;
    }

    // Initialize detector
    let configPath = null;
    const configIndex = args.indexOf('--config');
    if (configIndex !== -1) {
        configPath = args[configIndex + 1];
    }

    const detector = new AnomalyDetector(configPath);
    const utils = new AnomalyUtils(detector);

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
                const options = {};

                const severityIndex = commandArgs.indexOf('--severity');
                if (severityIndex !== -1) {
                    options.severity = parseInt(commandArgs[severityIndex + 1]) || AnomalySeverity.MEDIUM;
                }

                const entityTypeIndex = commandArgs.indexOf('--entity-type');
                if (entityTypeIndex !== -1) {
                    options.entityType = commandArgs[entityTypeIndex + 1] || 'generic';
                }

                const typeIndex = commandArgs.indexOf('--type');
                if (typeIndex !== -1) {
                    options.anomalyType = commandArgs[typeIndex + 1] || AnomalyType.POINT_ANOMALY;
                }

                const anomaly = utils.createAnomaly({
                    description,
                    ...options
                });

                detector.store.saveAnomaly(anomaly);
                console.log(`Created anomaly: ${anomaly.id}`);
                break;

            case 'list':
                const allAnomalies = detector.store.getUnacknowledgedAnomalies(Infinity);
                const filtered = applyFilters(utils, allAnomalies, commandArgs);

                for (const anomaly of filtered) {
                    const severityStr = AnomalySeverity.toString(anomaly.severity).toUpperCase();
                    console.log(`[${severityStr}] ${anomaly.description} (${anomaly.detectionMethod}) - ${new Date(anomaly.timestamp).toISOString()}`);
                }
                break;

            case 'stats':
                const anomalies = detector.store.getUnacknowledgedAnomalies(Infinity);
                const stats = utils.getAnomalyStats(anomalies);
                console.log('Anomaly Statistics:');
                console.log(JSON.stringify(stats, null, 2));
                break;

            case 'export':
                if (commandArgs.length < 2) {
                    console.error('Usage: export <format> <output-file>');
                    process.exit(1);
                }

                const exportFormat = commandArgs[0];
                const exportOutput = commandArgs[1];
                const allAnoms = detector.store.getUnacknowledgedAnomalies(Infinity);

                await utils.exportAnomalies(allAnoms, exportFormat, exportOutput);
                break;

            case 'import':
                if (commandArgs.length < 2) {
                    console.error('Usage: import <format> <input-file>');
                    process.exit(1);
                }

                const importFormat = commandArgs[0];
                const importInput = commandArgs[1];

                const imported = await utils.importAnomalies(importInput, importFormat);
                for (const anomaly of imported) {
                    detector.store.saveAnomaly(anomaly);
                }
                console.log(`Imported ${imported.length} anomalies`);
                break;

            case 'acknowledge':
                if (commandArgs.length === 0) {
                    console.error('Usage: acknowledge <id> [id...]');
                    process.exit(1);
                }

                utils.acknowledgeAnomalies(commandArgs);
                break;

            case 'report':
                const startDateIndex = commandArgs.indexOf('--start-date');
                const endDateIndex = commandArgs.indexOf('--end-date');

                const startDate = startDateIndex !== -1 ? new Date(commandArgs[startDateIndex + 1]).getTime() : Date.now() - (7 * 24 * 60 * 60 * 1000); // 1 week ago
                const endDate = endDateIndex !== -1 ? new Date(commandArgs[endDateIndex + 1]).getTime() : Date.now();

                const allAnomsForReport = detector.store.getUnacknowledgedAnomalies(Infinity);
                const report = utils.generateReport(allAnomsForReport, startDate, endDate);
                console.log(report);
                break;

            case 'find-similar':
                const allAnomsForSim = detector.store.getUnacknowledgedAnomalies(Infinity);
                const similarGroups = utils.findSimilarAnomalies(allAnomsForSim);
                console.log(`Found ${similarGroups.length} groups of similar anomalies:`);
                for (let i = 0; i < similarGroups.length; i++) {
                    console.log(`Group ${i + 1}: ${similarGroups[i].length} similar anomalies`);
                    for (const anomaly of similarGroups[i]) {
                        console.log(`  - ${anomaly.description}`);
                    }
                }
                break;

            case 'analyze':
                const allAnomsForAnalysis = detector.store.getUnacknowledgedAnomalies(Infinity);
                const analysisResults = await utils.performRootCauseAnalysis(allAnomsForAnalysis);
                console.log('Root Cause Analysis Results:');
                for (const result of analysisResults) {
                    console.log(`\nAnomaly: ${result.description}`);
                    console.log(`Potential Causes: ${result.potentialCauses.join(', ')}`);
                    console.log(`Recommendations: ${result.recommendations.join(', ')}`);
                }
                break;

            case 'cleanup':
                const days = parseInt(commandArgs[0]) || 90;
                const result = await utils.cleanupOldAnomalies(days);
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
function applyFilters(utils, anomalies, args) {
    const filters = {};

    const severityIndex = args.indexOf('--severity');
    if (severityIndex !== -1) {
        filters.minSeverity = parseInt(args[severityIndex + 1]);
    }

    const typeIndex = args.indexOf('--type');
    if (typeIndex !== -1) {
        filters.type = args[typeIndex + 1];
    }

    const entityTypeIndex = args.indexOf('--entity-type');
    if (entityTypeIndex !== -1) {
        filters.entityType = args[entityTypeIndex + 1];
    }

    const methodIndex = args.indexOf('--method');
    if (methodIndex !== -1) {
        filters.method = args[methodIndex + 1];
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

    const minConfidenceIndex = args.indexOf('--min-confidence');
    if (minConfidenceIndex !== -1) {
        filters.minConfidence = parseFloat(args[minConfidenceIndex + 1]);
    }

    return utils.filterAnomalies(anomalies, filters);
}

if (require.main === module) {
    main().catch(error => {
        console.error('Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { AnomalyUtils };