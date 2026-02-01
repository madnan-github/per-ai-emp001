/**
 * Rule Interpreter - JavaScript Implementation
 *
 * This script implements a rule interpreter that evaluates business rules, company policies,
 * and operational guidelines to determine appropriate actions or responses based on input
 * situations and contexts.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const EventEmitter = require('events');

class RuleActionType {
    static ALLOW = 'allow';
    static DENY = 'deny';
    static REQUIRE_APPROVAL = 'require_approval';
    static ESCALATE = 'escalate';
    static REDIRECT = 'redirect';
    static NOTIFY = 'notify';
    static LOG = 'log';
    static ALERT = 'alert';
    static MODIFY_FIELD = 'modify_field';
    static ADD_TAG = 'add_tag';
    static SET_PRIORITY = 'set_priority';
    static ASSIGN_OWNER = 'assign_owner';

    static toString(type) {
        switch (type) {
            case RuleActionType.ALLOW: return 'allow';
            case RuleActionType.DENY: return 'deny';
            case RuleActionType.REQUIRE_APPROVAL: return 'require_approval';
            case RuleActionType.ESCALATE: return 'escalate';
            case RuleActionType.REDIRECT: return 'redirect';
            case RuleActionType.NOTIFY: return 'notify';
            case RuleActionType.LOG: return 'log';
            case RuleActionType.ALERT: return 'alert';
            case RuleActionType.MODIFY_FIELD: return 'modify_field';
            case RuleActionType.ADD_TAG: return 'add_tag';
            case RuleActionType.SET_PRIORITY: return 'set_priority';
            case RuleActionType.ASSIGN_OWNER: return 'assign_owner';
            default: return 'unknown';
        }
    }
}

class RuleCondition {
    constructor(field, operator, value, comparator = 'AND') {
        this.field = field;
        this.operator = operator;
        this.value = value;
        this.comparator = comparator; // AND/OR with next condition
    }

    toJSON() {
        return {
            field: this.field,
            operator: this.operator,
            value: this.value,
            comparator: this.comparator
        };
    }
}

class RuleAction {
    constructor(type, parameters = {}) {
        this.type = type;
        this.parameters = parameters;
    }

    toJSON() {
        return {
            type: this.type,
            parameters: this.parameters
        };
    }
}

class BusinessRule {
    constructor(options = {}) {
        this.id = options.id || this.generateId();
        this.name = options.name || 'Unnamed Rule';
        this.description = options.description || '';
        this.category = options.category || 'general';
        this.priority = options.priority || 50;
        this.enabled = options.enabled !== false; // Default to true
        this.conditions = options.conditions || [];
        this.actions = options.actions || [];
        this.metadata = options.metadata || {};
    }

    generateId() {
        const content = `${this.name}:${this.description}:${Date.now()}`;
        return crypto.createHash('sha256').update(content).digest('hex').substring(0, 16);
    }

    toJSON() {
        return {
            id: this.id,
            name: this.name,
            description: this.description,
            category: this.category,
            priority: this.priority,
            enabled: this.enabled,
            conditions: this.conditions.map(c => c.toJSON()),
            actions: this.actions.map(a => a.toJSON()),
            metadata: this.metadata
        };
    }
}

class RuleEvaluationResult {
    constructor(options = {}) {
        this.ruleId = options.ruleId;
        this.matched = options.matched || false;
        this.actions = options.actions || [];
        this.executionTime = options.executionTime || 0;
        this.details = options.details || {};
    }

    toJSON() {
        return {
            ruleId: this.ruleId,
            matched: this.matched,
            actions: this.actions.map(a => a.toJSON()),
            executionTime: this.executionTime,
            details: this.details
        };
    }
}

class RuleStore {
    constructor(dbPath = './rules.json') {
        this.dbPath = dbPath;
        this.rules = this.loadRules();
    }

    loadRules() {
        try {
            if (fs.existsSync(this.dbPath)) {
                const data = fs.readFileSync(this.dbPath, 'utf8');
                const rawData = JSON.parse(data);

                // Convert raw data to BusinessRule objects
                return rawData.map(rawRule => {
                    const rule = new BusinessRule({
                        ...rawRule,
                        conditions: rawRule.conditions.map(c => new RuleCondition(c.field, c.operator, c.value, c.comparator)),
                        actions: rawRule.actions.map(a => new RuleAction(a.type, a.parameters))
                    });
                    return rule;
                });
            }
        } catch (error) {
            console.error('Error loading rules:', error.message);
        }
        return [];
    }

    saveRules() {
        try {
            const serializableRules = this.rules.map(rule => rule.toJSON());
            fs.writeFileSync(this.dbPath, JSON.stringify(serializableRules, null, 2));
        } catch (error) {
            console.error('Error saving rules:', error.message);
        }
    }

    saveRule(rule) {
        // Check if rule already exists
        const existingIndex = this.rules.findIndex(r => r.id === rule.id);

        if (existingIndex !== -1) {
            this.rules[existingIndex] = rule;
        } else {
            this.rules.push(rule);
        }

        this.saveRules();
    }

    getRulesByCategory(category) {
        return this.rules
            .filter(r => r.category === category && r.enabled)
            .sort((a, b) => b.priority - a.priority);
    }

    getAllRules() {
        return [...this.rules].sort((a, b) => b.priority - a.priority);
    }
}

class ConditionEvaluator {
    constructor(config = {}) {
        this.config = config;
        this.operators = this.loadOperators();
    }

    loadOperators() {
        return {
            // Comparison operators
            '=': (x, y) => x == y,
            '!=': (x, y) => x != y,
            '>': (x, y) => x > y,
            '<': (x, y) => x < y,
            '>=': (x, y) => x >= y,
            '<=': (x, y) => x <= y,
            // String operators
            'contains': (x, y) => typeof x === 'string' && x.includes(y),
            'starts_with': (x, y) => typeof x === 'string' && x.startsWith(y),
            'ends_with': (x, y) => typeof x === 'string' && x.endsWith(y),
            'matches_regex': (x, y) => typeof x === 'string' && new RegExp(y).test(x),
            // Collection operators
            'in': (x, y) => Array.isArray(y) && y.includes(x),
            'not_in': (x, y) => Array.isArray(y) && !y.includes(x),
            'has_any': (x, y) => Array.isArray(x) && Array.isArray(y) && y.some(item => x.includes(item)),
            'has_all': (x, y) => Array.isArray(x) && Array.isArray(y) && y.every(item => x.includes(item))
        };
    }

    evaluateCondition(condition, context) {
        // Extract the value from context based on the field path
        const fieldValue = this.getNestedValue(context, condition.field);

        if (fieldValue === undefined || fieldValue === null) {
            return false; // If field doesn't exist, condition fails
        }

        // Get the operator function
        const opFunc = this.operators[condition.operator];
        if (!opFunc) {
            console.warn(`Unknown operator: ${condition.operator}`);
            return false;
        }

        try {
            // Apply the operator
            return opFunc(fieldValue, condition.value);
        } catch (e) {
            console.error(`Error evaluating condition ${condition.field} ${condition.operator} ${condition.value}:`, e.message);
            return false;
        }
    }

    evaluateConditions(conditions, context) {
        if (!conditions || conditions.length === 0) {
            return true; // Empty conditions should pass
        }

        let result = this.evaluateCondition(conditions[0], context);

        for (let i = 1; i < conditions.length; i++) {
            const nextResult = this.evaluateCondition(conditions[i], context);

            // Apply logical operator (from previous condition's comparator)
            if (conditions[i - 1].comparator.toUpperCase() === 'AND') {
                result = result && nextResult;
            } else if (conditions[i - 1].comparator.toUpperCase() === 'OR') {
                result = result || nextResult;
            } else {
                // Default to AND if not specified
                result = result && nextResult;
            }
        }

        return result;
    }

    getNestedValue(obj, path) {
        const parts = path.split('.');
        let current = obj;

        for (const part of parts) {
            if (current && typeof current === 'object' && part in current) {
                current = current[part];
            } else {
                return undefined; // Path doesn't exist
            }
        }

        return current;
    }
}

class ActionExecutor {
    constructor(config = {}) {
        this.config = config;
    }

    executeAction(action, context) {
        try {
            switch (action.type) {
                case RuleActionType.ALLOW:
                    return this.executeAllow(action.parameters, context);
                case RuleActionType.DENY:
                    return this.executeDeny(action.parameters, context);
                case RuleActionType.REQUIRE_APPROVAL:
                    return this.executeRequireApproval(action.parameters, context);
                case RuleActionType.ESCALATE:
                    return this.executeEscalate(action.parameters, context);
                case RuleActionType.REDIRECT:
                    return this.executeRedirect(action.parameters, context);
                case RuleActionType.NOTIFY:
                    return this.executeNotify(action.parameters, context);
                case RuleActionType.LOG:
                    return this.executeLog(action.parameters, context);
                case RuleActionType.ALERT:
                    return this.executeAlert(action.parameters, context);
                case RuleActionType.MODIFY_FIELD:
                    return this.executeModifyField(action.parameters, context);
                case RuleActionType.ADD_TAG:
                    return this.executeAddTag(action.parameters, context);
                case RuleActionType.SET_PRIORITY:
                    return this.executeSetPriority(action.parameters, context);
                case RuleActionType.ASSIGN_OWNER:
                    return this.executeAssignOwner(action.parameters, context);
                default:
                    console.warn(`Unknown action type: ${action.type}`);
                    return { success: false, message: `Unknown action type: ${action.type}` };
            }
        } catch (e) {
            console.error(`Error executing action ${action.type}:`, e.message);
            return { success: false, message: e.message };
        }
    }

    executeActions(actions, context) {
        const results = [];
        for (const action of actions) {
            const result = this.executeAction(action, context);
            results.push(result);
        }
        return results;
    }

    executeAllow(parameters, context) {
        return { success: true, action: 'allow', contextModified: false };
    }

    executeDeny(parameters, context) {
        const reason = parameters.reason || 'Rule violation';
        return { success: true, action: 'deny', reason, contextModified: false };
    }

    executeRequireApproval(parameters, context) {
        const level = parameters.level || 'manager';
        const deadline = parameters.deadline || 'PT24H';
        return {
            success: true,
            action: 'require_approval',
            level,
            deadline,
            contextModified: true
        };
    }

    executeEscalate(parameters, context) {
        const target = parameters.to || 'management';
        const reason = parameters.reason || 'Rule requirement';
        return {
            success: true,
            action: 'escalate',
            to: target,
            reason,
            contextModified: true
        };
    }

    executeRedirect(parameters, context) {
        const process = parameters.process || 'default';
        const reason = parameters.reason || 'Rule requirement';
        return {
            success: true,
            action: 'redirect',
            process,
            reason,
            contextModified: true
        };
    }

    executeNotify(parameters, context) {
        const recipients = parameters.recipients || [];
        const message = parameters.message || 'Notification from rule evaluation';
        return {
            success: true,
            action: 'notify',
            recipients,
            message,
            contextModified: false
        };
    }

    executeLog(parameters, context) {
        const level = parameters.level || 'info';
        const message = parameters.message || 'Rule evaluation event';
        const category = parameters.category || 'rule_evaluation';

        // Log the message (in a real system, this would go to proper logging)
        const logMsg = `[${level.toUpperCase()}] ${category}: ${message}`;
        console.log(logMsg); // For demo purposes

        return {
            success: true,
            action: 'log',
            level,
            message,
            contextModified: false
        };
    }

    executeAlert(parameters, context) {
        const severity = parameters.severity || 'medium';
        const message = parameters.message || 'Rule evaluation alert';
        const target = parameters.targetSystem || 'default_monitoring';

        // In a real system, this would send to monitoring system
        console.log(`ALERT [${severity.toUpperCase()}]: ${message}`); // For demo purposes

        return {
            success: true,
            action: 'alert',
            severity,
            message,
            contextModified: false
        };
    }

    executeModifyField(parameters, context) {
        const field = parameters.field || '';
        const value = parameters.value;
        const operation = parameters.operation || 'set';

        // This is a simplified implementation - in a real system you'd modify the actual context
        // For this example, we'll just return what we'd do
        return {
            success: true,
            action: 'modify_field',
            field,
            value,
            operation,
            contextModified: true
        };
    }

    executeAddTag(parameters, context) {
        const tag = parameters.tag || '';
        const category = parameters.category || 'classification';

        return {
            success: true,
            action: 'add_tag',
            tag,
            category,
            contextModified: true
        };
    }

    executeSetPriority(parameters, context) {
        const level = parameters.level || 'normal';

        return {
            success: true,
            action: 'set_priority',
            level,
            contextModified: true
        };
    }

    executeAssignOwner(parameters, context) {
        const owner = parameters.owner || '';
        const reason = parameters.reason || 'Rule assignment';

        return {
            success: true,
            action: 'assign_owner',
            owner,
            reason,
            contextModified: true
        };
    }
}

class RuleInterpreter extends EventEmitter {
    constructor(configPath = null) {
        super();
        this.config = this.loadConfig(configPath);
        this.store = new RuleStore();
        this.conditionEvaluator = new ConditionEvaluator(this.config);
        this.actionExecutor = new ActionExecutor(this.config);
        this.running = false;
        this.intervalId = null;

        // Load default rules if store is empty
        this.ensureDefaultRules();
    }

    loadConfig(configPath = null) {
        const defaultConfig = {
            processing: {
                maxWorkers: 16,
                timeout: 30000, // milliseconds
                maxConcurrentEvaluations: 100
            },
            evaluationStrategies: {
                defaultStrategy: 'first_match'
            },
            contextVariables: {
                request: { enabled: true },
                user: { enabled: true },
                organization: { enabled: true },
                temporal: { enabled: true }
            }
        };

        if (configPath && fs.existsSync(configPath)) {
            try {
                const loadedConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));
                // Deep merge configs
                this.deepMerge(defaultConfig, loadedConfig);
            } catch (error) {
                console.error(`Warning: Could not load config ${configPath}:`, error.message);
            }
        }

        return defaultConfig;
    }

    deepMerge(base, override) {
        for (const [key, value] of Object.entries(override)) {
            if (key in base && typeof base[key] === 'object' && typeof value === 'object' && base[key] !== null && value !== null) {
                this.deepMerge(base[key], value);
            } else {
                base[key] = value;
            }
        }
    }

    ensureDefaultRules() {
        // Check if we have any rules
        const rules = this.store.getAllRules();
        if (rules.length === 0) {
            // Add some default rules for demonstration
            this.addDefaultRules();
        }
    }

    addDefaultRules() {
        // Rule 1: High-value requests require approval
        const highValueRule = new BusinessRule({
            name: "High Value Approval Rule",
            description: "Requests with high monetary value require approval",
            category: "financial_controls",
            priority: 90,
            enabled: true,
            conditions: [
                new RuleCondition("request.amount", ">", 5000, "AND"),
                new RuleCondition("request.category", "!=", "expense", "AND")
            ],
            actions: [
                new RuleAction(RuleActionType.REQUIRE_APPROVAL, { level: "director", deadline: "PT24H" })
            ]
        });

        // Rule 2: Weekend requests get flagged
        const weekendRule = new BusinessRule({
            name: "Weekend Request Flag",
            description: "Flag requests made on weekends",
            category: "operational_procedures",
            priority: 70,
            enabled: true,
            conditions: [
                new RuleCondition("temporal.business_hours", "==", false)
            ],
            actions: [
                new RuleAction(RuleActionType.ADD_TAG, { tag: "weekend_request", category: "timing" }),
                new RuleAction(RuleActionType.NOTIFY, { recipients: ["supervisor"], message: "Weekend request detected" })
            ]
        });

        // Rule 3: HR requests need special handling
        const hrRule = new BusinessRule({
            name: "HR Request Handler",
            description: "Special handling for HR-related requests",
            category: "human_resources",
            priority: 80,
            enabled: true,
            conditions: [
                new RuleCondition("request.category", "contains", "hr")
            ],
            actions: [
                new RuleAction(RuleActionType.REDIRECT, { process: "hr_approval", reason: "HR category request" }),
                new RuleAction(RuleActionType.SET_PRIORITY, { level: "high" })
            ]
        });

        // Save the default rules
        this.store.saveRule(highValueRule);
        this.store.saveRule(weekendRule);
        this.store.saveRule(hrRule);
    }

    evaluateRules(context, category = "all") {
        const startTime = Date.now();

        // Get rules for the specified category or all rules
        const rules = category === "all" ? this.store.getAllRules() : this.store.getRulesByCategory(category);

        const results = [];

        for (const rule of rules) {
            try {
                // Evaluate conditions
                const conditionMatched = this.conditionEvaluator.evaluateConditions(rule.conditions, context);

                if (conditionMatched) {
                    // Execute actions
                    const actionResults = this.actionExecutor.executeActions(rule.actions, context);

                    // Create evaluation result
                    const result = new RuleEvaluationResult({
                        ruleId: rule.id,
                        matched: true,
                        actions: rule.actions,
                        executionTime: Date.now() - startTime,
                        details: {
                            ruleName: rule.name,
                            actionResults
                        }
                    });
                    results.push(result);

                    // For first_match strategy, stop after first match
                    const strategy = this.config.evaluationStrategies.defaultStrategy;
                    if (strategy === 'first_match') {
                        break;
                    }
                }
            } catch (e) {
                console.error(`Error evaluating rule ${rule.id}:`, e.message);
                // Continue with other rules
                continue;
            }
        }

        const totalTime = Date.now() - startTime;
        console.log(`Rule evaluation completed in ${(totalTime / 1000).toFixed(3)}s with ${results.length} matches`);

        // Emit event
        this.emit('rulesEvaluated', {
            timestamp: Date.now(),
            contextSample: Object.keys(context).join(', '),
            matchedRules: results.length,
            executionTime: totalTime
        });

        return results;
    }

    addRule(rule) {
        this.store.saveRule(rule);
        console.log(`Added rule: ${rule.name}`);

        // Emit event
        this.emit('ruleAdded', {
            ruleId: rule.id,
            ruleName: rule.name
        });
    }

    updateRule(rule) {
        this.store.saveRule(rule);
        console.log(`Updated rule: ${rule.name}`);

        // Emit event
        this.emit('ruleUpdated', {
            ruleId: rule.id,
            ruleName: rule.name
        });
    }

    removeRule(ruleId) {
        const allRules = this.store.getAllRules();
        for (const rule of allRules) {
            if (rule.id === ruleId) {
                rule.enabled = false;
                this.store.saveRule(rule);
                console.log(`Disabled rule: ${rule.name}`);

                // Emit event
                this.emit('ruleRemoved', {
                    ruleId: rule.id,
                    ruleName: rule.name
                });
                return;
            }
        }
        console.log(`Rule not found: ${ruleId}`);
    }

    async runContinuous() {
        if (this.running) {
            throw new Error('Rule interpreter is already running');
        }

        this.running = true;
        console.log('Starting rule interpreter...');

        try {
            while (this.running) {
                // Perform any periodic maintenance tasks
                await new Promise(resolve => setTimeout(resolve, 60000)); // Check every minute
            }
        } catch (error) {
            console.error('Error in main loop:', error.message);
        }

        console.log('Rule interpreter stopped');
        this.emit('stopped');
    }

    async stop() {
        if (!this.running) {
            return;
        }

        this.running = false;

        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }

        console.log('Rule interpreter stopped');
        this.emit('stopped');
    }

    async getStatus() {
        return {
            running: this.running,
            ruleCount: this.store.getAllRules().length,
            config: {
                maxWorkers: this.config.processing.maxWorkers,
                timeout: this.config.processing.timeout
            }
        };
    }
}

// If running directly, start the interpreter
if (require.main === module) {
    const args = process.argv.slice(2);

    // Parse command line arguments
    const configIndex = args.indexOf('--config');
    const configPath = configIndex !== -1 ? args[configIndex + 1] : null;

    const testModeIndex = args.indexOf('--test-mode');
    const testMode = testModeIndex !== -1;

    const interpreter = new RuleInterpreter(configPath);

    if (testMode) {
        // Create a sample context to test with
        const sampleContext = {
            request: {
                amount: 7500,
                category: "software_purchase",
                description: "New software license",
                requestorId: "user123"
            },
            user: {
                id: "user123",
                name: "John Doe",
                department: "Engineering",
                role: "developer"
            },
            organization: {
                departmentBudget: 100000,
                remainingBudget: 85000
            },
            temporal: {
                currentDate: new Date().toISOString(),
                businessHours: true
            }
        };

        console.log("Testing rule evaluation with sample context...");
        const results = interpreter.evaluateRules(sampleContext, "financial_controls");

        console.log(`Found ${results.length} matching rules:`);
        for (const result of results) {
            console.log(`  - ${result.ruleId}: ${result.actions.length} actions executed`);
        }
    }

    // Handle shutdown gracefully
    const shutdown = async () => {
        console.log('\nReceived interrupt signal, stopping interpreter...');
        await interpreter.stop();
        process.exit(0);
    };

    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);

    // Start interpreter
    interpreter.runContinuous().catch(err => {
        console.error('Error starting interpreter:', err);
        process.exit(1);
    });

    // Listen for events
    interpreter.on('rulesEvaluated', (data) => {
        console.log(`Rules evaluated at ${new Date(data.timestamp).toISOString()}: ${data.matchedRules} matches`);
    });

    interpreter.on('ruleAdded', (data) => {
        console.log(`Rule added: ${data.ruleName}`);
    });

    interpreter.on('ruleUpdated', (data) => {
        console.log(`Rule updated: ${data.ruleName}`);
    });

    interpreter.on('ruleRemoved', (data) => {
        console.log(`Rule removed: ${data.ruleName}`);
    });

    interpreter.on('stopped', () => {
        console.log('Interpreter stopped successfully');
    });
}

module.exports = {
    RuleInterpreter,
    BusinessRule,
    RuleAction,
    RuleCondition,
    RuleActionType,
    RuleEvaluationResult
};