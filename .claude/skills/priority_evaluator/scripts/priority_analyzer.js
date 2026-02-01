/**
 * PriorityEvaluatorJS: JavaScript module for evaluating and ranking tasks based on business rules and impact assessment.
 *
 * This module provides sophisticated priority evaluation capabilities using multiple
 * scoring frameworks and contextual factors to determine the optimal priority order
 * for tasks, projects, and initiatives.
 */

const fs = require('fs').promises;
const path = require('path');
const sqlite3 = require('sqlite3').verbose();

// Priority levels for evaluated items
const PriorityLevel = {
    CRITICAL: 5,
    HIGH: 4,
    MEDIUM: 3,
    LOW: 2,
    MINIMAL: 1
};

// Types of items that can be prioritized
const ItemType = {
    TASK: "task",
    PROJECT: "project",
    BUG: "bug",
    FEATURE_REQUEST: "feature_request",
    INCIDENT: "incident",
    OPPORTUNITY: "opportunity"
};

class PriorityItem {
    constructor(options = {}) {
        this.id = options.id || this.generateId();
        this.name = options.name || 'Untitled Item';
        this.description = options.description || '';
        this.itemType = options.itemType || ItemType.TASK;
        this.createdAt = options.createdAt || new Date();

        // Impact Assessment
        this.businessImpact = options.businessImpact || 0.0;  // 0.0-10.0 scale
        this.userImpact = options.userImpact || 0.0;          // 0.0-10.0 scale
        this.strategicAlignment = options.strategicAlignment || 0.0;  // 0.0-10.0 scale

        // Effort Assessment
        this.implementationComplexity = options.implementationComplexity || 0.0;  // 0.0-10.0 scale (inverse)
        this.resourceRequirements = options.resourceRequirements || 0.0;      // 0.0-10.0 scale (inverse)
        this.riskFactor = options.riskFactor || 0.0;                // 0.0-10.0 scale (inverse)

        // Urgency Assessment
        this.timeSensitivity = options.timeSensitivity || 0.0;           // 0.0-10.0 scale
        this.dependencyImpact = options.dependencyImpact || 0.0;          // 0.0-10.0 scale
        this.opportunityWindow = options.opportunityWindow || 0.0;         // 0.0-10.0 scale

        // Contextual factors
        this.stakeholderImportance = options.stakeholderImportance || 0.0;     // 0.0-10.0 scale
        this.resourceAvailability = options.resourceAvailability || 0.0;      // 0.0-10.0 scale
        this.strategicTiming = options.strategicTiming || 0.0;           // 0.0-10.0 scale

        // Calculated values
        this.calculatedScore = options.calculatedScore || 0.0;
        this.priorityLevel = options.priorityLevel || PriorityLevel.MINIMAL;
        this.evaluatorNotes = options.evaluatorNotes || null;
        this.evaluationTimestamp = options.evaluationTimestamp || null;
    }

    generateId() {
        return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    }
}

class PriorityEvaluatorJS {
    /**
     * Creates a new PriorityEvaluatorJS instance
     * @param {string} dbPath - Path to the SQLite database file
     */
    constructor(dbPath = './priorities.db') {
        this.dbPath = dbPath;
        this.db = null;
        this.setupDatabase();

        // Default weights for scoring model
        this.weights = {
            impact: 0.50,  // Business impact, user impact, strategic alignment
            effort: 0.30,  // Inverse of complexity, resources, risk
            urgency: 0.20  // Time sensitivity, dependencies, opportunity
        };

        // Impact sub-weights
        this.impactWeights = {
            businessImpact: 0.50,
            userImpact: 0.30,
            strategicAlignment: 0.20
        };

        // Effort sub-weights (inverted)
        this.effortWeights = {
            implementationComplexity: 0.40,
            resourceRequirements: 0.35,
            riskFactor: 0.25
        };

        // Urgency sub-weights
        this.urgencyWeights = {
            timeSensitivity: 0.50,
            dependencyImpact: 0.30,
            opportunityWindow: 0.20
        };

        // Configure logging
        this.logger = console;
    }

    /**
     * Sets up the database schema for priority tracking
     */
    setupDatabase() {
        this.db = new sqlite3.Database(this.dbPath);

        // Create priority_items table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS priority_items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                item_type TEXT,
                created_at DATETIME,

                -- Impact Assessment
                business_impact REAL,
                user_impact REAL,
                strategic_alignment REAL,

                -- Effort Assessment
                implementation_complexity REAL,
                resource_requirements REAL,
                risk_factor REAL,

                -- Urgency Assessment
                time_sensitivity REAL,
                dependency_impact REAL,
                opportunity_window REAL,

                -- Contextual factors
                stakeholder_importance REAL,
                resource_availability REAL,
                strategic_timing REAL,

                -- Calculated values
                calculated_score REAL,
                priority_level INTEGER,
                evaluator_notes TEXT,
                evaluation_timestamp DATETIME
            )
        `);

        // Create evaluation_history table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS evaluation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT,
                evaluation_data_json TEXT,
                calculated_score REAL,
                priority_level INTEGER,
                evaluator_notes TEXT,
                evaluation_timestamp DATETIME,
                FOREIGN KEY (item_id) REFERENCES priority_items (id)
            )
        `);

        // Create priority_decisions table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS priority_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item1_id TEXT,
                item2_id TEXT,
                preferred_item_id TEXT,
                reason TEXT,
                decision_maker TEXT,
                decision_timestamp DATETIME,
                FOREIGN KEY (item1_id) REFERENCES priority_items (id),
                FOREIGN KEY (item2_id) REFERENCES priority_items (id),
                FOREIGN KEY (preferred_item_id) REFERENCES priority_items (id)
            )
        `);
    }

    /**
     * Adds an item to be evaluated
     * @param {PriorityItem} item - The item to add
     * @returns {Promise<string>} The ID of the added item
     */
    async addItem(item) {
        await this.saveItemToDb(item);
        this.logger.info(`Added item '${item.name}' (ID: ${item.id}) for evaluation`);
        return item.id;
    }

    /**
     * Saves an item to the database
     * @param {PriorityItem} item - The item to save
     * @returns {Promise<void>}
     */
    async saveItemToDb(item) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT INTO priority_items
                (id, name, description, item_type, created_at,
                 business_impact, user_impact, strategic_alignment,
                 implementation_complexity, resource_requirements, risk_factor,
                 time_sensitivity, dependency_impact, opportunity_window,
                 stakeholder_importance, resource_availability, strategic_timing,
                 calculated_score, priority_level, evaluator_notes, evaluation_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `);

            stmt.run([
                item.id, item.name, item.description, item.itemType,
                item.createdAt.toISOString(),
                item.businessImpact, item.userImpact, item.strategicAlignment,
                item.implementationComplexity, item.resourceRequirements, item.riskFactor,
                item.timeSensitivity, item.dependencyImpact, item.opportunityWindow,
                item.stakeholderImportance, item.resourceAvailability, item.strategicTiming,
                item.calculatedScore, item.priorityLevel,
                item.evaluatorNotes, item.evaluationTimestamp ? item.evaluationTimestamp.toISOString() : null
            ], function(err) {
                if (err) {
                    reject(err);
                } else {
                    resolve();
                }
            });

            stmt.finalize();
        });
    }

    /**
     * Evaluates a single item and returns the evaluated item
     * @param {string} itemId - The ID of the item to evaluate
     * @returns {Promise<PriorityItem>} The evaluated item
     */
    async evaluateItem(itemId) {
        const item = await this.getItem(itemId);
        if (!item) {
            throw new Error(`Item with ID ${itemId} not found`);
        }

        // Calculate the priority score
        const score = this.calculatePriorityScore(item);

        // Determine priority level based on score
        const priorityLevel = this.scoreToPriorityLevel(score);

        // Update the item with calculated values
        item.calculatedScore = score;
        item.priorityLevel = priorityLevel;
        item.evaluationTimestamp = new Date();

        // Save updated item
        await this.saveItemToDb(item);

        // Save to evaluation history
        await this.saveEvaluationToHistory(item);

        this.logger.info(`Evaluated item '${item.name}' (ID: ${item.id}), Score: ${score.toFixed(2)}, Priority: ${this.priorityLevelToString(priorityLevel)}`);
        return item;
    }

    /**
     * Calculates priority score using weighted formula
     * @param {PriorityItem} item - The item to evaluate
     * @returns {number} The calculated priority score
     */
    calculatePriorityScore(item) {
        // Calculate impact score
        const impactScore = (
            item.businessImpact * this.impactWeights.businessImpact +
            item.userImpact * this.impactWeights.userImpact +
            item.strategicAlignment * this.impactWeights.strategicAlignment
        );

        // Calculate effort score (inverted - lower effort = higher score)
        const effortScore = (
            (10 - item.implementationComplexity) * this.effortWeights.implementationComplexity +
            (10 - item.resourceRequirements) * this.effortWeights.resourceRequirements +
            (10 - item.riskFactor) * this.effortWeights.riskFactor
        );

        // Calculate urgency score
        const urgencyScore = (
            item.timeSensitivity * this.urgencyWeights.timeSensitivity +
            item.dependencyImpact * this.urgencyWeights.dependencyImpact +
            item.opportunityWindow * this.urgencyWeights.opportunityWindow
        );

        // Apply main weights
        let totalScore = (
            impactScore * this.weights.impact +
            effortScore * this.weights.effort +
            urgencyScore * this.weights.urgency
        );

        // Apply contextual adjustments
        let contextMultiplier = 1.0;

        // Stakeholder importance adjustment
        if (item.stakeholderImportance > 7.0) {
            contextMultiplier *= 1.2;
        } else if (item.stakeholderImportance > 5.0) {
            contextMultiplier *= 1.1;
        }

        // Resource availability adjustment
        if (item.resourceAvailability > 8.0) {
            contextMultiplier *= 1.15;
        } else if (item.resourceAvailability < 4.0) {
            contextMultiplier *= 0.85;
        }

        // Strategic timing adjustment
        if (item.strategicTiming > 8.0) {
            contextMultiplier *= 1.25;
        } else if (item.strategicTiming < 3.0) {
            contextMultiplier *= 0.9;
        }

        const finalScore = totalScore * contextMultiplier;

        // Ensure score is within bounds
        return Math.max(0.0, Math.min(10.0, finalScore));
    }

    /**
     * Converts numeric score to priority level
     * @param {number} score - The score to convert
     * @returns {number} The corresponding priority level
     */
    scoreToPriorityLevel(score) {
        if (score >= 8.5) {
            return PriorityLevel.CRITICAL;
        } else if (score >= 7.0) {
            return PriorityLevel.HIGH;
        } else if (score >= 5.0) {
            return PriorityLevel.MEDIUM;
        } else if (score >= 3.0) {
            return PriorityLevel.LOW;
        } else {
            return PriorityLevel.MINIMAL;
        }
    }

    /**
     * Converts priority level number to string representation
     * @param {number} level - The priority level number
     * @returns {string} String representation of the priority level
     */
    priorityLevelToString(level) {
        switch (level) {
            case PriorityLevel.CRITICAL: return 'CRITICAL';
            case PriorityLevel.HIGH: return 'HIGH';
            case PriorityLevel.MEDIUM: return 'MEDIUM';
            case PriorityLevel.LOW: return 'LOW';
            case PriorityLevel.MINIMAL: return 'MINIMAL';
            default: return 'UNKNOWN';
        }
    }

    /**
     * Saves evaluation results to history
     * @param {PriorityItem} item - The item to save evaluation for
     * @returns {Promise<void>}
     */
    async saveEvaluationToHistory(item) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT INTO evaluation_history
                (item_id, evaluation_data_json, calculated_score, priority_level,
                 evaluator_notes, evaluation_timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            `);

            stmt.run([
                item.id,
                JSON.stringify({
                    businessImpact: item.businessImpact,
                    userImpact: item.userImpact,
                    strategicAlignment: item.strategicAlignment,
                    implementationComplexity: item.implementationComplexity,
                    resourceRequirements: item.resourceRequirements,
                    riskFactor: item.riskFactor,
                    timeSensitivity: item.timeSensitivity,
                    dependencyImpact: item.dependencyImpact,
                    opportunityWindow: item.opportunityWindow,
                    stakeholderImportance: item.stakeholderImportance,
                    resourceAvailability: item.resourceAvailability,
                    strategicTiming: item.strategicTiming,
                }),
                item.calculatedScore,
                item.priorityLevel,
                item.evaluatorNotes,
                item.evaluationTimestamp ? item.evaluationTimestamp.toISOString() : new Date().toISOString()
            ], function(err) {
                if (err) {
                    reject(err);
                } else {
                    resolve();
                }
            });

            stmt.finalize();
        });
    }

    /**
     * Retrieves an item by ID
     * @param {string} itemId - The ID of the item to retrieve
     * @returns {Promise<PriorityItem|null>} The retrieved item or null if not found
     */
    async getItem(itemId) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                SELECT id, name, description, item_type, created_at,
                       business_impact, user_impact, strategic_alignment,
                       implementation_complexity, resource_requirements, risk_factor,
                       time_sensitivity, dependency_impact, opportunity_window,
                       stakeholder_importance, resource_availability, strategic_timing,
                       calculated_score, priority_level, evaluator_notes, evaluation_timestamp
                FROM priority_items WHERE id = ?
            `);

            stmt.get([itemId], (err, row) => {
                if (err) {
                    reject(err);
                    return;
                }

                if (!row) {
                    resolve(null);
                    return;
                }

                resolve(new PriorityItem({
                    id: row.id,
                    name: row.name,
                    description: row.description,
                    itemType: row.item_type,
                    createdAt: new Date(row.created_at),
                    businessImpact: row.business_impact,
                    userImpact: row.user_impact,
                    strategicAlignment: row.strategic_alignment,
                    implementationComplexity: row.implementation_complexity,
                    resourceRequirements: row.resource_requirements,
                    riskFactor: row.risk_factor,
                    timeSensitivity: row.time_sensitivity,
                    dependencyImpact: row.dependency_impact,
                    opportunityWindow: row.opportunity_window,
                    stakeholderImportance: row.stakeholder_importance,
                    resourceAvailability: row.resource_availability,
                    strategicTiming: row.strategic_timing,
                    calculatedScore: row.calculated_score,
                    priorityLevel: row.priority_level,
                    evaluatorNotes: row.evaluator_notes,
                    evaluationTimestamp: row.evaluation_timestamp ? new Date(row.evaluation_timestamp) : null
                }));
            });

            stmt.finalize();
        });
    }

    /**
     * Evaluates multiple items and returns them sorted by priority
     * @param {string[]} itemIds - Array of item IDs to evaluate
     * @returns {Promise<PriorityItem[]>} Array of evaluated items sorted by priority
     */
    async evaluateMultipleItems(itemIds) {
        const evaluatedItems = [];

        for (const itemId of itemIds) {
            const evaluatedItem = await this.evaluateItem(itemId);
            evaluatedItems.push(evaluatedItem);
        }

        // Sort by calculated score (descending)
        evaluatedItems.sort((a, b) => b.calculatedScore - a.calculatedScore);

        return evaluatedItems;
    }

    /**
     * Gets the top N priority items
     * @param {number} count - Number of top items to return
     * @returns {Promise<PriorityItem[]>} Array of top priority items
     */
    async getTopPriorities(count = 10) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                SELECT id, name, description, item_type, created_at,
                       business_impact, user_impact, strategic_alignment,
                       implementation_complexity, resource_requirements, risk_factor,
                       time_sensitivity, dependency_impact, opportunity_window,
                       stakeholder_importance, resource_availability, strategic_timing,
                       calculated_score, priority_level, evaluator_notes, evaluation_timestamp
                FROM priority_items
                WHERE calculated_score IS NOT NULL
                ORDER BY calculated_score DESC
                LIMIT ?
            `);

            stmt.all([count], (err, rows) => {
                if (err) {
                    reject(err);
                    return;
                }

                const items = rows.map(row => new PriorityItem({
                    id: row.id,
                    name: row.name,
                    description: row.description,
                    itemType: row.item_type,
                    createdAt: new Date(row.created_at),
                    businessImpact: row.business_impact,
                    userImpact: row.user_impact,
                    strategicAlignment: row.strategic_alignment,
                    implementationComplexity: row.implementation_complexity,
                    resourceRequirements: row.resource_requirements,
                    riskFactor: row.risk_factor,
                    timeSensitivity: row.time_sensitivity,
                    dependencyImpact: row.dependency_impact,
                    opportunityWindow: row.opportunity_window,
                    stakeholderImportance: row.stakeholder_importance,
                    resourceAvailability: row.resource_availability,
                    strategicTiming: row.strategic_timing,
                    calculatedScore: row.calculated_score,
                    priorityLevel: row.priority_level,
                    evaluatorNotes: row.evaluator_notes,
                    evaluationTimestamp: row.evaluation_timestamp ? new Date(row.evaluation_timestamp) : null
                }));

                resolve(items);
            });

            stmt.finalize();
        });
    }

    /**
     * Records a manual comparison decision between two items
     * @param {string} item1Id - ID of the first item
     * @param {string} item2Id - ID of the second item
     * @param {string} preferredItemId - ID of the preferred item
     * @param {string} reason - Reason for preference
     * @param {string} decisionMaker - Person making the decision
     * @returns {Promise<void>}
     */
    async compareItems(item1Id, item2Id, preferredItemId, reason, decisionMaker) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT INTO priority_decisions
                (item1_id, item2_id, preferred_item_id, reason, decision_maker, decision_timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            `);

            stmt.run([item1Id, item2Id, preferredItemId, reason, decisionMaker, new Date().toISOString()], function(err) {
                if (err) {
                    reject(err);
                } else {
                    console.info(`Recorded manual priority decision: ${preferredItemId} preferred over ${item1Id === preferredItemId ? item2Id : item1Id}`);
                    resolve();
                }
            });

            stmt.finalize();
        });
    }

    /**
     * Gets evaluation history for an item
     * @param {string} itemId - The ID of the item
     * @param {number} limit - Maximum number of history records to return
     * @returns {Promise<Object[]>} Array of evaluation history records
     */
    async getEvaluationHistory(itemId, limit = 10) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                SELECT evaluation_data_json, calculated_score, priority_level,
                       evaluator_notes, evaluation_timestamp
                FROM evaluation_history
                WHERE item_id = ?
                ORDER BY evaluation_timestamp DESC
                LIMIT ?
            `);

            stmt.all([itemId, limit], (err, rows) => {
                if (err) {
                    reject(err);
                    return;
                }

                const history = rows.map(row => ({
                    evaluationData: JSON.parse(row.evaluation_data_json),
                    calculatedScore: row.calculated_score,
                    priorityLevel: this.priorityLevelToString(row.priority_level),
                    evaluatorNotes: row.evaluator_notes,
                    evaluationTimestamp: new Date(row.evaluation_timestamp)
                }));

                resolve(history);
            });

            stmt.finalize();
        });
    }

    /**
     * Adjusts the scoring weights
     * @param {Object} newWeights - New weights object
     */
    adjustWeights(newWeights) {
        // Validate weights sum to 1.0
        const totalWeight = Object.values(newWeights).reduce((sum, val) => sum + val, 0);
        if (Math.abs(totalWeight - 1.0) > 0.01) { // Allow small floating point errors
            throw new Error(`Weights must sum to 1.0, got ${totalWeight}`);
        }

        this.weights = newWeights;
        this.logger.info(`Updated priority weights: ${JSON.stringify(newWeights)}`);
    }

    /**
     * Gets a summary of priority distribution
     * @returns {Promise<Object>} Priority summary object
     */
    async getPrioritySummary() {
        return new Promise(async (resolve, reject) => {
            try {
                // Count items by priority level
                const priorityCounts = await new Promise((resolve, reject) => {
                    const stmt = this.db.prepare(`
                        SELECT priority_level, COUNT(*)
                        FROM priority_items
                        WHERE calculated_score IS NOT NULL
                        GROUP BY priority_level
                    `);

                    stmt.all([], (err, rows) => {
                        if (err) {
                            reject(err);
                            return;
                        }

                        const counts = {};
                        for (const row of rows) {
                            counts[this.priorityLevelToString(row['priority_level'])] = row['COUNT(*)'];
                        }

                        resolve(counts);
                    });

                    stmt.finalize();
                });

                // Get average scores by item type
                const typeScores = await new Promise((resolve, reject) => {
                    const stmt = this.db.prepare(`
                        SELECT item_type, AVG(calculated_score), COUNT(*)
                        FROM priority_items
                        WHERE calculated_score IS NOT NULL
                        GROUP BY item_type
                    `);

                    stmt.all([], (err, rows) => {
                        if (err) {
                            reject(err);
                            return;
                        }

                        const scores = {};
                        for (const row of rows) {
                            scores[row['item_type']] = {
                                avgScore: row['AVG(calculated_score)'],
                                count: row['COUNT(*)']
                            };
                        }

                        resolve(scores);
                    });

                    stmt.finalize();
                });

                resolve({
                    priorityDistribution: priorityCounts,
                    averageScoresByType: typeScores,
                    totalEvaluatedItems: Object.values(priorityCounts).reduce((sum, val) => sum + val, 0)
                });
            } catch (err) {
                reject(err);
            }
        });
    }

    /**
     * Closes the database connection
     */
    close() {
        if (this.db) {
            this.db.close();
        }
    }
}

module.exports = PriorityEvaluatorJS;

// If running as a standalone script
if (require.main === module) {
    const args = process.argv.slice(2);

    async function main() {
        const evaluator = new PriorityEvaluatorJS();

        if (args.includes('--demo')) {
            // Create demo items
            const demoItems = [
                new PriorityItem({
                    id: evaluator.generateId(),
                    name: "Fix Critical Security Bug",
                    description: "Address high-severity security vulnerability in authentication system",
                    itemType: ItemType.BUG,
                    businessImpact: 9.5,
                    userImpact: 9.0,
                    strategicAlignment: 8.0,
                    implementationComplexity: 7.0,
                    resourceRequirements: 6.0,
                    riskFactor: 3.0,
                    timeSensitivity: 10.0,
                    dependencyImpact: 9.0,
                    opportunityWindow: 9.5,
                    stakeholderImportance: 9.0,
                    resourceAvailability: 7.0,
                    strategicTiming: 8.5
                }),
                new PriorityItem({
                    id: evaluator.generateId(),
                    name: "New Feature Request - Mobile App",
                    description: "Implement mobile app for customer portal",
                    itemType: ItemType.FEATURE_REQUEST,
                    businessImpact: 8.0,
                    userImpact: 8.5,
                    strategicAlignment: 9.0,
                    implementationComplexity: 8.0,
                    resourceRequirements: 7.5,
                    riskFactor: 5.0,
                    timeSensitivity: 6.0,
                    dependencyImpact: 4.0,
                    opportunityWindow: 7.0,
                    stakeholderImportance: 7.5,
                    resourceAvailability: 6.0,
                    strategicTiming: 7.0
                }),
                new PriorityItem({
                    id: evaluator.generateId(),
                    name: "Performance Optimization",
                    description: "Optimize database queries to improve response times",
                    itemType: ItemType.TASK,
                    businessImpact: 7.0,
                    userImpact: 7.5,
                    strategicAlignment: 6.0,
                    implementationComplexity: 6.0,
                    resourceRequirements: 5.0,
                    riskFactor: 2.0,
                    timeSensitivity: 5.0,
                    dependencyImpact: 3.0,
                    opportunityWindow: 4.0,
                    stakeholderImportance: 6.5,
                    resourceAvailability: 8.0,
                    strategicTiming: 5.5
                })
            ];

            console.log("Adding demo items...");
            const itemIds = [];
            for (const item of demoItems) {
                const itemId = await evaluator.addItem(item);
                itemIds.push(itemId);
                console.log(`  Added: ${item.name} (ID: ${itemId})`);
            }

            console.log("\\nEvaluating items...");
            const evaluatedItems = await evaluator.evaluateMultipleItems(itemIds);

            console.log("\\nEvaluation Results (sorted by priority):");
            for (let i = 0; i < evaluatedItems.length; i++) {
                const item = evaluatedItems[i];
                console.log(`${i + 1}. ${item.name}`);
                console.log(`   Score: ${item.calculatedScore.toFixed(2)}`);
                console.log(`   Priority: ${evaluator.priorityLevelToString(item.priorityLevel)}`);
                console.log(`   Type: ${item.itemType}`);
                console.log(`   Business Impact: ${item.businessImpact}`);
                console.log(`   User Impact: ${item.userImpact}`);
                console.log(`   Urgency: ${item.timeSensitivity}`);
                console.log();
            }

            // Get top priorities
            const topItems = await evaluator.getTopPriorities(5);
            console.log(`Top ${topItems.length} Priority Items:`);
            for (let i = 0; i < topItems.length; i++) {
                const item = topItems[i];
                console.log(`${i + 1}. ${item.name} - Score: ${item.calculatedScore.toFixed(2)} (${evaluator.priorityLevelToString(item.priorityLevel)})`);
            }

            // Get summary
            const summary = await evaluator.getPrioritySummary();
            console.log(`\\nPriority Summary:`);
            console.log(`Total Evaluated Items: ${summary.totalEvaluatedItems}`);
            console.log("Distribution by Priority:");
            for (const [level, count] of Object.entries(summary.priorityDistribution)) {
                console.log(`  ${level}: ${count}`);
            }

        } else {
            console.log("Priority evaluator initialized. Use the API to evaluate items.");
        }

        evaluator.close();
    }

    main().catch(console.error);
}