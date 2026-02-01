#!/usr/bin/env node

/**
 * Rule Interpreter Utility Functions
 *
 * This script provides utility functions for managing and interacting with
 * the rule interpretation system, including rule creation, testing,
 * evaluation, and management tools.
 */

const { RuleInterpreter, BusinessRule, RuleAction, RuleCondition, RuleActionType } = require('./rule_interpreter.js');
const fs = require('fs').promises;
const path = require('path');

class RuleUtils {
    constructor(interpreter) {
        this.interpreter = interpreter;
    }

    /**
     * Create a new business rule programmatically
     */
    createRule(options = {}) {
        const rule = new BusinessRule({
            name: options.name || 'New Rule',
            description: options.description || 'Rule created programmatically',
            category: options.category || 'general',
            priority: options.priority || 50,
            enabled: options.enabled !== false, // Default to true
            conditions: options.conditions || [],
            actions: options.actions || [],
            metadata: options.metadata || {}
        });

        return rule;
    }

    /**
     * Create a condition for a rule
     */
    createCondition(field, operator, value, comparator = 'AND') {
        return new RuleCondition(field, operator, value, comparator);
    }

    /**
     * Create an action for a rule
     */
    createAction(type, parameters = {}) {
        return new RuleAction(type, parameters);
    }

    /**
     * Filter rules by various criteria
     */
    filterRules(rules, filters = {}) {
        return rules.filter(rule => {
            // Filter by category
            if (filters.category && rule.category !== filters.category) {
                return false;
            }

            // Filter by enabled status
            if (filters.enabled !== undefined && rule.enabled !== filters.enabled) {
                return false;
            }

            // Filter by priority range
            if (filters.minPriority && rule.priority < filters.minPriority) {
                return false;
            }

            if (filters.maxPriority && rule.priority > filters.maxPriority) {
                return false;
            }

            // Filter by keyword in name or description
            if (filters.keyword) {
                const keyword = filters.keyword.toLowerCase();
                const name = rule.name.toLowerCase();
                const description = rule.description.toLowerCase();

                if (!name.includes(keyword) && !description.includes(keyword)) {
                    return false;
                }
            }

            // Filter by action type
            if (filters.actionType) {
                const hasActionType = rule.actions.some(action => action.type === filters.actionType);
                if (!hasActionType) {
                    return false;
                }
            }

            return true;
        });
    }

    /**
     * Get summary statistics for rules
     */
    getRuleStats(rules) {
        const stats = {
            total: rules.length,
            byCategory: {},
            byPriority: { low: 0, medium: 0, high: 0, critical: 0 },
            byStatus: { enabled: 0, disabled: 0 },
            byActionType: {},
            totalConditions: 0,
            totalActions: 0
        };

        for (const rule of rules) {
            // Count by category
            if (!stats.byCategory[rule.category]) {
                stats.byCategory[rule.category] = 0;
            }
            stats.byCategory[rule.category]++;

            // Count by priority level
            if (rule.priority >= 90) {
                stats.byPriority.critical++;
            } else if (rule.priority >= 70) {
                stats.byPriority.high++;
            } else if (rule.priority >= 40) {
                stats.byPriority.medium++;
            } else {
                stats.byPriority.low++;
            }

            // Count by status
            if (rule.enabled) {
                stats.byStatus.enabled++;
            } else {
                stats.byStatus.disabled++;
            }

            // Count conditions and actions
            stats.totalConditions += rule.conditions.length;
            stats.totalActions += rule.actions.length;

            // Count by action type
            for (const action of rule.actions) {
                if (!stats.byActionType[action.type]) {
                    stats.byActionType[action.type] = 0;
                }
                stats.byActionType[action.type]++;
            }
        }

        return stats;
    }

    /**
     * Export rules to various formats
     */
    async exportRules(rules, format = 'json', outputPath) {
        let content;

        switch (format.toLowerCase()) {
            case 'json':
                content = JSON.stringify(rules.map(r => r.toJSON()), null, 2);
                break;

            case 'csv':
                content = this.rulesToCSV(rules);
                break;

            case 'markdown':
                content = this.rulesToMarkdown(rules);
                break;

            default:
                throw new Error(`Unsupported export format: ${format}`);
        }

        if (outputPath) {
            await fs.writeFile(outputPath, content);
            console.log(`Rules exported to ${outputPath}`);
        }

        return content;
    }

    /**
     * Convert rules to CSV format
     */
    rulesToCSV(rules) {
        const headers = ['ID', 'Name', 'Category', 'Priority', 'Enabled', 'Conditions', 'Actions', 'Description'];
        const rows = [headers];

        for (const rule of rules) {
            rows.push([
                rule.id,
                `"${rule.name.replace(/"/g, '""')}"`,
                rule.category,
                rule.priority,
                rule.enabled,
                rule.conditions.length,
                rule.actions.length,
                `"${rule.description.replace(/"/g, '""')}"`
            ]);
        }

        return rows.map(row => row.join(',')).join('\n');
    }

    /**
     * Convert rules to Markdown format
     */
    rulesToMarkdown(rules) {
        let markdown = '# Business Rules Catalog\n\n';
        markdown += `Generated: ${new Date().toISOString()}\n\n`;

        for (const rule of rules) {
            markdown += `## ${rule.name}\n\n`;
            markdown += `- **ID**: ${rule.id}\n`;
            markdown += `- **Category**: ${rule.category}\n`;
            markdown += `- **Priority**: ${rule.priority}\n`;
            markdown += `- **Status**: ${rule.enabled ? 'Enabled' : 'Disabled'}\n`;
            markdown += `- **Conditions**: ${rule.conditions.length}\n`;
            markdown += `- **Actions**: ${rule.actions.length}\n\n`;
            markdown += `**Description:**\n${rule.description}\n\n`;

            if (rule.conditions.length > 0) {
                markdown += `**Conditions:**\n`;
                for (const condition of rule.conditions) {
                    markdown += `- ${condition.field} ${condition.operator} ${condition.value}\n`;
                }
                markdown += `\n`;
            }

            if (rule.actions.length > 0) {
                markdown += `**Actions:**\n`;
                for (const action of rule.actions) {
                    markdown += `- ${action.type}: ${JSON.stringify(action.parameters)}\n`;
                }
                markdown += `\n`;
            }

            markdown += `---\n\n`;
        }

        return markdown;
    }

    /**
     * Import rules from a file
     */
    async importRules(inputPath, format = 'json') {
        const content = await fs.readFile(inputPath, 'utf8');

        switch (format.toLowerCase()) {
            case 'json':
                const jsonData = JSON.parse(content);
                return jsonData.map(data => new BusinessRule({
                    ...data,
                    conditions: data.conditions.map(c => new RuleCondition(c.field, c.operator, c.value, c.comparator)),
                    actions: data.actions.map(a => new RuleAction(a.type, a.parameters))
                }));

            default:
                throw new Error(`Unsupported import format: ${format}`);
        }
    }

    /**
     * Test rule evaluation with a sample context
     */
    testRuleEvaluation(context, category = 'all') {
        console.log('Testing rule evaluation with context:', JSON.stringify(context, null, 2));

        const results = this.interpreter.evaluateRules(context, category);

        console.log(`\nEvaluation Results:`);
        for (const result of results) {
            console.log(`- Rule: ${result.ruleId} (Matched: ${result.matched})`);
            console.log(`  Actions: ${result.actions.length}`);
            console.log(`  Execution Time: ${result.executionTime}ms`);
        }

        return results;
    }

    /**
     * Validate a rule for correctness
     */
    validateRule(rule) {
        const errors = [];

        // Check if rule has a name
        if (!rule.name || rule.name.trim() === '') {
            errors.push('Rule must have a name');
        }

        // Check if rule has conditions
        if (!rule.conditions || rule.conditions.length === 0) {
            errors.push('Rule must have at least one condition');
        }

        // Check if rule has actions
        if (!rule.actions || rule.actions.length === 0) {
            errors.push('Rule must have at least one action');
        }

        // Check if all conditions have required fields
        for (let i = 0; i < rule.conditions.length; i++) {
            const condition = rule.conditions[i];
            if (!condition.field) {
                errors.push(`Condition ${i} must have a field`);
            }
            if (!condition.operator) {
                errors.push(`Condition ${i} must have an operator`);
            }
            if (condition.value === undefined) {
                errors.push(`Condition ${i} must have a value`);
            }
        }

        // Check if all actions have required fields
        for (let i = 0; i < rule.actions.length; i++) {
            const action = rule.actions[i];
            if (!action.type) {
                errors.push(`Action ${i} must have a type`);
            }
        }

        return {
            isValid: errors.length === 0,
            errors
        };
    }

    /**
     * Find conflicting rules based on conditions
     */
    findConflictingRules(rules) {
        const conflicts = [];

        for (let i = 0; i < rules.length; i++) {
            for (let j = i + 1; j < rules.length; j++) {
                const rule1 = rules[i];
                const rule2 = rules[j];

                // Simple conflict detection: rules with identical conditions but different actions
                if (this.conditionsAreEquivalent(rule1.conditions, rule2.conditions)) {
                    conflicts.push({
                        rule1: rule1.id,
                        rule2: rule2.id,
                        type: 'duplicate_conditions',
                        description: `Rules have identical conditions but may have different actions`
                    });
                }
            }
        }

        return conflicts;
    }

    /**
     * Check if two condition arrays are equivalent
     */
    conditionsAreEquivalent(conds1, conds2) {
        if (conds1.length !== conds2.length) {
            return false;
        }

        // Simple check: compare field, operator, and value for each condition
        for (let i = 0; i < conds1.length; i++) {
            if (conds1[i].field !== conds2[i].field ||
                conds1[i].operator !== conds2[i].operator ||
                conds1[i].value !== conds2[i].value) {
                return false;
            }
        }

        return true;
    }

    /**
     * Optimize rules by removing duplicates and improving efficiency
     */
    optimizeRules(rules) {
        const optimizedRules = [];
        const seenConditions = new Set();

        for (const rule of rules) {
            // Create a hash of the conditions to identify duplicates
            const conditionHash = this.hashConditions(rule.conditions);

            if (!seenConditions.has(conditionHash)) {
                seenConditions.add(conditionHash);
                optimizedRules.push(rule);
            } else {
                console.log(`Removed duplicate rule with conditions hash: ${conditionHash}`);
            }
        }

        console.log(`Optimized rules: ${rules.length} -> ${optimizedRules.length}`);
        return optimizedRules;
    }

    /**
     * Create a hash of conditions for comparison
     */
    hashConditions(conditions) {
        const sortedConditions = [...conditions].sort((a, b) => {
            if (a.field !== b.field) return a.field.localeCompare(b.field);
            if (a.operator !== b.operator) return a.operator.localeCompare(b.operator);
            return String(a.value).localeCompare(String(b.value));
        });

        return sortedConditions.map(c => `${c.field}_${c.operator}_${c.value}`).join('|');
    }

    /**
     * Generate a rule coverage report
     */
    generateCoverageReport(rules, testContexts) {
        const coverage = {
            totalRules: rules.length,
            rulesTriggered: 0,
            rulesNotTriggered: 0,
            ruleCoverage: [],
            contextCoverage: []
        };

        for (const rule of rules) {
            let triggered = false;

            for (const context of testContexts) {
                try {
                    // Create a temporary evaluator to test this specific rule
                    const conditionMatched = this.interpreter.conditionEvaluator.evaluateConditions(rule.conditions, context);
                    if (conditionMatched) {
                        triggered = true;
                        break;
                    }
                } catch (e) {
                    console.error(`Error evaluating rule ${rule.id}:`, e.message);
                }
            }

            coverage.ruleCoverage.push({
                ruleId: rule.id,
                ruleName: rule.name,
                triggered
            });

            if (triggered) {
                coverage.rulesTriggered++;
            } else {
                coverage.rulesNotTriggered++;
            }
        }

        coverage.contextCoverage = testContexts.map((context, idx) => {
            const triggeredRules = rules.filter(rule => {
                try {
                    return this.interpreter.conditionEvaluator.evaluateConditions(rule.conditions, context);
                } catch (e) {
                    return false;
                }
            });

            return {
                contextId: `context_${idx}`,
                rulesTriggered: triggeredRules.length,
                rules: triggeredRules.map(r => r.id)
            };
        });

        return coverage;
    }
}

// Command line interface
async function main() {
    const args = process.argv.slice(2);

    // Check for help flag
    if (args.includes('--help') || args.includes('-h')) {
        console.log(`
Rule Interpreter Utility

Usage:
  node rule_utils.js [command] [options]

Commands:
  create-rule <name> [options]            Create a new business rule
  list [options]                          List rules with filters
  stats [options]                         Show rule statistics
  export <format> <output-file>          Export rules
  import <format> <input-file>           Import rules
  test-eval [options]                     Test rule evaluation
  validate <rule-id>                     Validate a specific rule
  find-conflicts                         Find conflicting rules
  optimize                              Optimize rules by removing duplicates
  coverage [options]                     Generate rule coverage report

Options:
  --category <category>                  Filter by category
  --enabled <true/false>                 Filter by enabled status
  --min-priority <num>                   Filter by minimum priority
  --max-priority <num>                   Filter by maximum priority
  --keyword <keyword>                    Filter by keyword
  --action-type <type>                   Filter by action type
  --config <path>                        Path to config file

Examples:
  node rule_utils.js create-rule "High Value Approval" --category financial_controls --priority 90
  node rule_utils.js list --category financial_controls --enabled true
  node rule_utils.js export json ./rules.json
  node rule_utils.js stats
  node rule_utils.js test-eval --context '{"request": {"amount": 10000}}'
        `);
        return;
    }

    // Initialize interpreter
    let configPath = null;
    const configIndex = args.indexOf('--config');
    if (configIndex !== -1) {
        configPath = args[configIndex + 1];
    }

    const interpreter = new RuleInterpreter(configPath);
    const utils = new RuleUtils(interpreter);

    // Parse command
    const command = args[0];
    const commandArgs = args.slice(1);

    try {
        switch (command) {
            case 'create-rule':
                if (commandArgs.length < 1) {
                    console.error('Usage: create-rule <name> [options]');
                    process.exit(1);
                }

                const name = commandArgs[0];

                // Parse options
                const options = { name };

                const categoryIndex = commandArgs.indexOf('--category');
                if (categoryIndex !== -1) {
                    options.category = commandArgs[categoryIndex + 1] || 'general';
                }

                const priorityIndex = commandArgs.indexOf('--priority');
                if (priorityIndex !== -1) {
                    options.priority = parseInt(commandArgs[priorityIndex + 1]) || 50;
                }

                const enabledIndex = commandArgs.indexOf('--enabled');
                if (enabledIndex !== -1) {
                    options.enabled = commandArgs[enabledIndex + 1] === 'true';
                }

                const rule = utils.createRule(options);
                interpreter.addRule(rule);
                console.log(`Created rule: ${rule.id} - ${rule.name}`);
                break;

            case 'list':
                const allRules = interpreter.store.getAllRules();
                const filtered = applyFilters(utils, allRules, commandArgs);

                for (const rule of filtered) {
                    const status = rule.enabled ? 'ENABLED' : 'DISABLED';
                    console.log(`${status} [${rule.priority}] ${rule.category}/${rule.id}: ${rule.name}`);
                }
                break;

            case 'stats':
                const rules = interpreter.store.getAllRules();
                const stats = utils.getRuleStats(rules);
                console.log('Rule Statistics:');
                console.log(JSON.stringify(stats, null, 2));
                break;

            case 'export':
                if (commandArgs.length < 2) {
                    console.error('Usage: export <format> <output-file>');
                    process.exit(1);
                }

                const exportFormat = commandArgs[0];
                const exportOutput = commandArgs[1];
                const allRulesForExport = interpreter.store.getAllRules();

                await utils.exportRules(allRulesForExport, exportFormat, exportOutput);
                break;

            case 'import':
                if (commandArgs.length < 2) {
                    console.error('Usage: import <format> <input-file>');
                    process.exit(1);
                }

                const importFormat = commandArgs[0];
                const importInput = commandArgs[1];

                const imported = await utils.importRules(importInput, importFormat);
                for (const rule of imported) {
                    interpreter.addRule(rule);
                }
                console.log(`Imported ${imported.length} rules`);
                break;

            case 'test-eval':
                // Create a sample context for testing
                const sampleContext = {
                    request: {
                        amount: 10000,
                        category: "purchase",
                        description: "Test purchase request"
                    },
                    user: {
                        id: "test-user",
                        name: "Test User",
                        department: "Engineering"
                    },
                    organization: {
                        departmentBudget: 50000,
                        remainingBudget: 40000
                    },
                    temporal: {
                        currentDate: new Date().toISOString(),
                        businessHours: true
                    }
                };

                utils.testRuleEvaluation(sampleContext);
                break;

            case 'validate':
                if (commandArgs.length < 1) {
                    console.error('Usage: validate <rule-id>');
                    process.exit(1);
                }

                const ruleId = commandArgs[0];
                const allRulesForValidation = interpreter.store.getAllRules();
                const ruleToValidate = allRulesForValidation.find(r => r.id === ruleId);

                if (ruleToValidate) {
                    const validationResult = utils.validateRule(ruleToValidate);
                    console.log(`Validation result for rule ${ruleId}:`);
                    console.log(JSON.stringify(validationResult, null, 2));
                } else {
                    console.log(`Rule not found: ${ruleId}`);
                }
                break;

            case 'find-conflicts':
                const allRulesForConflict = interpreter.store.getAllRules();
                const conflicts = utils.findConflictingRules(allRulesForConflict);
                console.log(`Found ${conflicts.length} potential conflicts:`);
                for (const conflict of conflicts) {
                    console.log(`- ${conflict.type}: ${conflict.rule1} vs ${conflict.rule2}`);
                }
                break;

            case 'optimize':
                const allRulesBefore = interpreter.store.getAllRules();
                const optimizedRules = utils.optimizeRules(allRulesBefore);
                console.log(`Optimization complete. ${allRulesBefore.length} rules optimized to ${optimizedRules.length} rules.`);

                // Optionally save optimized rules (implement if needed)
                break;

            case 'coverage':
                const allRulesForCoverage = interpreter.store.getAllRules();
                const testContexts = [{
                    request: { amount: 1000 },
                    user: { department: "engineering" }
                }, {
                    request: { amount: 10000 },
                    user: { department: "sales" }
                }];

                const coverage = utils.generateCoverageReport(allRulesForCoverage, testContexts);
                console.log('Rule Coverage Report:');
                console.log(JSON.stringify(coverage, null, 2));
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
function applyFilters(utils, rules, args) {
    const filters = {};

    const categoryIndex = args.indexOf('--category');
    if (categoryIndex !== -1) {
        filters.category = args[categoryIndex + 1];
    }

    const enabledIndex = args.indexOf('--enabled');
    if (enabledIndex !== -1) {
        filters.enabled = args[enabledIndex + 1] === 'true';
    }

    const minPriorityIndex = args.indexOf('--min-priority');
    if (minPriorityIndex !== -1) {
        filters.minPriority = parseInt(args[minPriorityIndex + 1]);
    }

    const maxPriorityIndex = args.indexOf('--max-priority');
    if (maxPriorityIndex !== -1) {
        filters.maxPriority = parseInt(args[maxPriorityIndex + 1]);
    }

    const keywordIndex = args.indexOf('--keyword');
    if (keywordIndex !== -1) {
        filters.keyword = args[keywordIndex + 1];
    }

    const actionTypeIndex = args.indexOf('--action-type');
    if (actionTypeIndex !== -1) {
        filters.actionType = args[actionTypeIndex + 1];
    }

    return utils.filterRules(rules, filters);
}

if (require.main === module) {
    main().catch(error => {
        console.error('Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { RuleUtils };