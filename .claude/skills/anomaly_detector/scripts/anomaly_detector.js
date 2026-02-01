/**
 * Anomaly Detector - JavaScript Implementation
 *
 * This script implements an anomaly detection system that monitors various data sources
 * for unusual patterns using statistical analysis, machine learning algorithms, and
 * rule-based detection to identify deviations from established baselines.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const EventEmitter = require('events');

class AnomalySeverity {
    static CRITICAL = 1;
    static HIGH = 2;
    static MEDIUM = 3;
    static LOW = 4;

    static toString(severity) {
        switch (severity) {
            case AnomalySeverity.CRITICAL: return 'critical';
            case AnomalySeverity.HIGH: return 'high';
            case AnomalySeverity.MEDIUM: return 'medium';
            case AnomalySeverity.LOW: return 'low';
            default: return 'unknown';
        }
    }
}

class AnomalyType {
    static POINT_ANOMALY = 'point_anomaly';
    static CONTEXTUAL_ANOMALY = 'contextual_anomaly';
    static COLLECTIVE_ANOMALY = 'collective_anomaly';
    static STATISTICAL_OUTLIER = 'statistical_outlier';
    static ML_PREDICTED = 'ml_predicted';
}

class Anomaly {
    constructor(options = {}) {
        this.id = options.id || this.generateId();
        this.timestamp = options.timestamp || Date.now();
        this.entityId = options.entityId || 'unknown';
        this.entityType = options.entityType || 'generic';
        this.anomalyType = options.anomalyType || AnomalyType.POINT_ANOMALY;
        this.severity = options.severity || AnomalySeverity.LOW;
        this.score = options.score || 0.0;
        this.confidence = options.confidence || 0.0;
        this.description = options.description || 'Anomaly detected';
        this.dataPoint = options.dataPoint || {};
        this.detectionMethod = options.detectionMethod || 'unknown';
        this.metadata = options.metadata || {};
        this.acknowledged = options.acknowledged || false;
    }

    generateId() {
        const content = `${this.entityId}:${this.detectionMethod}:${this.timestamp}`;
        return crypto.createHash('sha256').update(content).digest('hex').substring(0, 16);
    }

    toJSON() {
        return {
            id: this.id,
            timestamp: this.timestamp,
            entityId: this.entityId,
            entityType: this.entityType,
            anomalyType: this.anomalyType,
            severity: this.severity,
            score: this.score,
            confidence: this.confidence,
            description: this.description,
            dataPoint: this.dataPoint,
            detectionMethod: this.detectionMethod,
            metadata: this.metadata,
            acknowledged: this.acknowledged
        };
    }
}

class AnomalyStore {
    constructor(dbPath = './anomalies.json') {
        this.dbPath = dbPath;
        this.anomalies = this.loadAnomalies();
    }

    loadAnomalies() {
        try {
            if (fs.existsSync(this.dbPath)) {
                const data = fs.readFileSync(this.dbPath, 'utf8');
                return JSON.parse(data);
            }
        } catch (error) {
            console.error('Error loading anomalies:', error.message);
        }
        return [];
    }

    saveAnomalies() {
        try {
            fs.writeFileSync(this.dbPath, JSON.stringify(this.anomalies, null, 2));
        } catch (error) {
            console.error('Error saving anomalies:', error.message);
        }
    }

    saveAnomaly(anomaly) {
        // Check if anomaly already exists
        const existingIndex = this.anomalies.findIndex(a => a.id === anomaly.id);

        if (existingIndex !== -1) {
            this.anomalies[existingIndex] = { ...anomaly.toJSON() };
        } else {
            this.anomalies.push({ ...anomaly.toJSON() });
        }

        this.saveAnomalies();
    }

    getUnacknowledgedAnomalies(limit = 100) {
        return this.anomalies
            .filter(a => !a.acknowledged)
            .sort((a, b) => a.severity - b.severity || b.timestamp - a.timestamp)
            .slice(0, limit)
            .map(data => new Anomaly(data));
    }

    acknowledgeAnomaly(anomalyId) {
        const anomaly = this.anomalies.find(a => a.id === anomalyId);
        if (anomaly) {
            anomaly.acknowledged = true;
            this.saveAnomalies();
        }
    }
}

class StatisticalAnomalyDetector {
    constructor(config = {}) {
        this.config = config;
        this.zScoreConfig = config.zScore || {};
        this.grubbsConfig = config.grubbsTest || {};
        this.iqrConfig = config.iqrMethod || {};
    }

    detectZScore(data, threshold = 3.0) {
        if (data.length < 3) return []; // Need at least 3 points for meaningful z-score

        // Calculate mean and standard deviation
        const mean = data.reduce((sum, value) => sum + value, 0) / data.length;
        const squaredDiffs = data.map(value => Math.pow(value - mean, 2));
        const stdDev = Math.sqrt(squaredDiffs.reduce((sum, value) => sum + value, 0) / data.length);

        if (stdDev === 0) return []; // Avoid division by zero

        const anomalies = [];
        data.forEach((value, index) => {
            const zScore = Math.abs((value - mean) / stdDev);
            if (zScore > threshold) {
                anomalies.push({ index, score: zScore });
            }
        });

        return anomalies;
    }

    detectModifiedZScore(data, threshold = 3.5) {
        if (data.length < 3) return [];

        // Calculate median
        const sortedData = [...data].sort((a, b) => a - b);
        const median = sortedData[Math.floor(sortedData.length / 2)];

        // Calculate median absolute deviation
        const absoluteDeviations = data.map(value => Math.abs(value - median));
        const mad = absoluteDeviations.sort((a, b) => a - b)[Math.floor(absoluteDeviations.length / 2)];

        if (mad === 0) return []; // Avoid division by zero

        const anomalies = [];
        data.forEach((value, index) => {
            const modifiedZScore = 0.6745 * (value - median) / mad;
            if (Math.abs(modifiedZScore) > threshold) {
                anomalies.push({ index, score: Math.abs(modifiedZScore) });
            }
        });

        return anomalies;
    }

    detectIQR(data, multiplier = 1.5) {
        if (data.length < 4) return []; // Need at least 4 points for quartiles

        const sortedData = [...data].sort((a, b) => a - b);
        const q1 = sortedData[Math.floor(sortedData.length * 0.25)];
        const q3 = sortedData[Math.floor(sortedData.length * 0.75)];
        const iqr = q3 - q1;

        const lowerBound = q1 - multiplier * iqr;
        const upperBound = q3 + multiplier * iqr;

        const anomalies = [];
        data.forEach((value, index) => {
            if (value < lowerBound || value > upperBound) {
                // Calculate how far out of bounds the value is
                const distance = Math.max(Math.abs(value - lowerBound), Math.abs(value - upperBound));
                anomalies.push({ index, score: distance });
            }
        });

        return anomalies;
    }

    detectGrubbsTest(data, significanceLevel = 0.05) {
        if (data.length < 3) return [];

        const n = data.length;
        const mean = data.reduce((sum, value) => sum + value, 0) / n;
        const variance = data.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / (n - 1);
        const stdDev = Math.sqrt(variance);

        if (stdDev === 0) return []; // Avoid division by zero

        // Find the point furthest from the mean
        let maxResidual = -Infinity;
        let maxResidualIdx = -1;
        data.forEach((value, index) => {
            const residual = Math.abs(value - mean);
            if (residual > maxResidual) {
                maxResidual = residual;
                maxResidualIdx = index;
            }
        });

        // Calculate Grubbs' test statistic
        const gStatistic = maxResidual / stdDev;

        // Approximate critical value (for large n, use simplified formula)
        // In practice, you'd want to use a more precise critical value lookup
        const criticalValue = (n - 1) / Math.sqrt(n) * Math.sqrt(
            Math.pow(getCriticalTValue(significanceLevel / (2 * n), n - 2), 2) /
            (n - 2 + Math.pow(getCriticalTValue(significanceLevel / (2 * n), n - 2), 2))
        );

        const anomalies = [];
        if (gStatistic > criticalValue) {
            anomalies.push({ index: maxResidualIdx, score: gStatistic });
        }

        return anomalies;
    }
}

// Helper function for Grubbs test (simplified T-value approximation)
function getCriticalTValue(alpha, df) {
    // Simplified approximation - in practice, use a proper T-distribution lookup
    // This is a rough approximation for demonstration purposes
    return 1.96; // Approximation for large degrees of freedom
}

class BusinessRuleEngine {
    constructor(config = {}) {
        this.config = config;
        this.rules = config.rules || [];
        this.compoundRules = config.compoundRules || [];
    }

    evaluateRules(dataPoint) {
        const triggeredRules = [];

        for (const rule of this.rules) {
            if (this.evaluateSingleRule(rule, dataPoint)) {
                triggeredRules.push(rule);
            }
        }

        return triggeredRules;
    }

    evaluateSingleRule(rule, dataPoint) {
        const conditions = rule.conditions || [];

        for (const condition of conditions) {
            const field = condition.field;
            const operator = condition.operator;
            const value = condition.value;

            if (!(field in dataPoint)) {
                return false;
            }

            const actualValue = dataPoint[field];

            // Evaluate condition based on operator
            switch (operator) {
                case '>':
                    if (!(actualValue > value)) return false;
                    break;
                case '<':
                    if (!(actualValue < value)) return false;
                    break;
                case '>=':
                    if (!(actualValue >= value)) return false;
                    break;
                case '<=':
                    if (!(actualValue <= value)) return false;
                    break;
                case '=':
                case '==':
                    if (actualValue != value) return false;
                    break;
                case '!=':
                    if (actualValue == value) return false;
                    break;
                case 'in':
                    if (!value.includes(actualValue)) return false;
                    break;
                case 'not_in':
                    if (value.includes(actualValue)) return false;
                    break;
                case 'contains':
                    if (typeof actualValue !== 'string' || !actualValue.includes(value)) return false;
                    break;
                case 'startsWith':
                    if (typeof actualValue !== 'string' || !actualValue.startsWith(value)) return false;
                    break;
                case 'endsWith':
                    if (typeof actualValue !== 'string' || !actualValue.endsWith(value)) return false;
                    break;
                default:
                    // Unsupported operator
                    return false;
            }
        }

        // All conditions passed
        return true;
    }
}

class AnomalyDetector extends EventEmitter {
    constructor(configPath = null) {
        super();
        this.config = this.loadConfig(configPath);
        this.store = new AnomalyStore();
        this.statisticalDetector = new StatisticalAnomalyDetector(
            this.config.detectionAlgorithms?.statistical || {}
        );
        this.ruleEngine = new BusinessRuleEngine(
            this.config.businessRules || {}
        );
        this.dataSources = {};
        this.running = false;
        this.intervalId = null;
    }

    loadConfig(configPath = null) {
        const defaultConfig = {
            processing: {
                batchSize: 1000,
                batchInterval: 30000, // milliseconds
                maxWorkers: 8
            },
            storage: {
                retentionDays: 90
            },
            detectionAlgorithms: {
                statistical: {
                    zScore: {
                        enabled: true,
                        threshold: 3.0,
                        useModifiedZScore: false,
                        madThreshold: 3.5
                    },
                    grubbsTest: {
                        enabled: true,
                        significanceLevel: 0.05
                    },
                    iqrMethod: {
                        enabled: true,
                        multiplier: 1.5
                    }
                }
            },
            businessRules: {
                enabled: true,
                rules: [],
                compoundRules: []
            },
            alerts: {
                thresholds: {
                    critical: { minConfidence: 0.95, minMagnitude: 3.0 },
                    high: { minConfidence: 0.80, minMagnitude: 2.0 },
                    medium: { minConfidence: 0.60, minMagnitude: 1.5 },
                    low: { minConfidence: 0.40, minMagnitude: 1.0 }
                }
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

    registerDataSource(name, sourceFunc) {
        this.dataSources[name] = sourceFunc;
    }

    detectStatisticalAnomalies(dataPoints, fieldName) {
        const anomalies = [];

        // Extract values for the specified field
        const values = [];
        const indicesToData = new Map();

        dataPoints.forEach((dp, i) => {
            if (fieldName in dp) {
                const val = dp[fieldName];
                // Only include numeric values
                if (typeof val === 'number') {
                    values.push(val);
                    indicesToData.set(values.length - 1, { originalIndex: i, originalData: dp });
                }
            }
        });

        if (values.length < 3) { // Need at least 3 points for statistical analysis
            return anomalies;
        }

        // Apply statistical detection methods
        const config = this.config.detectionAlgorithms?.statistical || {};

        // Z-score detection
        if (config.zScore?.enabled !== false) {
            const threshold = config.zScore?.threshold || 3.0;
            const zAnomalies = this.statisticalDetector.detectZScore(values, threshold);

            for (const { index, score } of zAnomalies) {
                const { originalIndex, originalData } = indicesToData.get(index);
                const anomaly = this.createAnomaly(
                    originalData, fieldName, values[index], 'z_score', score, AnomalyType.STATISTICAL_OUTLIER
                );
                anomalies.push(anomaly);
            }
        }

        // Modified Z-score detection
        if (config.zScore?.useModifiedZScore) {
            const threshold = config.zScore?.madThreshold || 3.5;
            const mzAnomalies = this.statisticalDetector.detectModifiedZScore(values, threshold);

            for (const { index, score } of mzAnomalies) {
                const { originalIndex, originalData } = indicesToData.get(index);
                const anomaly = this.createAnomaly(
                    originalData, fieldName, values[index], 'modified_z_score', score, AnomalyType.STATISTICAL_OUTLIER
                );
                anomalies.push(anomaly);
            }
        }

        // IQR detection
        if (config.iqrMethod?.enabled !== false) {
            const multiplier = config.iqrMethod?.multiplier || 1.5;
            const iqrAnomalies = this.statisticalDetector.detectIQR(values, multiplier);

            for (const { index, score } of iqrAnomalies) {
                const { originalIndex, originalData } = indicesToData.get(index);
                const anomaly = this.createAnomaly(
                    originalData, fieldName, values[index], 'iqr_method', score, AnomalyType.STATISTICAL_OUTLIER
                );
                anomalies.push(anomaly);
            }
        }

        // Grubbs' test
        if (config.grubbsTest?.enabled !== false) {
            const sigLevel = config.grubbsTest?.significanceLevel || 0.05;
            const grubbsAnomalies = this.statisticalDetector.detectGrubbsTest(values, sigLevel);

            for (const { index, score } of grubbsAnomalies) {
                const { originalIndex, originalData } = indicesToData.get(index);
                const anomaly = this.createAnomaly(
                    originalData, fieldName, values[index], 'grubbs_test', score, AnomalyType.STATISTICAL_OUTLIER
                );
                anomalies.push(anomaly);
            }
        }

        return anomalies;
    }

    detectRuleBasedAnomalies(dataPoints) {
        const anomalies = [];

        for (const dp of dataPoints) {
            const triggeredRules = this.ruleEngine.evaluateRules(dp);

            for (const rule of triggeredRules) {
                const severityStr = rule.severity || 'medium';
                const severityMap = {
                    'critical': AnomalySeverity.CRITICAL,
                    'high': AnomalySeverity.HIGH,
                    'medium': AnomalySeverity.MEDIUM,
                    'low': AnomalySeverity.LOW
                };
                const severity = severityMap[severityStr] || AnomalySeverity.MEDIUM;

                const anomaly = new Anomaly({
                    entityId: dp.id || dp.entityId || 'unknown',
                    entityType: dp.entityType || 'generic',
                    anomalyType: AnomalyType.POINT_ANOMALY,
                    severity: severity,
                    score: 1.0, // Rules have binary outcome
                    confidence: 0.9, // High confidence in rule-based detection
                    description: `Business rule '${rule.name}' triggered: ${rule.description || ''}`,
                    dataPoint: dp,
                    detectionMethod: 'business_rule',
                    metadata: { ruleName: rule.name, ruleDescription: rule.description || '' }
                });

                anomalies.push(anomaly);
            }
        }

        return anomalies;
    }

    createAnomaly(dataPoint, fieldName, value, method, score, anomalyType) {
        // Determine severity based on score
        let severity, confidence;
        if (score > 3.0) {
            severity = AnomalySeverity.CRITICAL;
            confidence = Math.min(0.95, score / 5.0); // Cap confidence
        } else if (score > 2.0) {
            severity = AnomalySeverity.HIGH;
            confidence = Math.min(0.85, score / 4.0);
        } else if (score > 1.5) {
            severity = AnomalySeverity.MEDIUM;
            confidence = Math.min(0.70, score / 3.0);
        } else {
            severity = AnomalySeverity.LOW;
            confidence = Math.min(0.50, score / 2.0);
        }

        return new Anomaly({
            entityId: dataPoint.id || dataPoint.entityId || 'unknown',
            entityType: dataPoint.entityType || 'generic',
            anomalyType: anomalyType,
            severity: severity,
            score: score,
            confidence: confidence,
            description: `Anomaly detected in field '${fieldName}' with value ${value} using ${method}`,
            dataPoint: dataPoint,
            detectionMethod: method,
            metadata: { fieldName: fieldName, fieldValue: value }
        });
    }

    async processDataBatch(dataPoints) {
        const allAnomalies = [];

        // Detect statistical anomalies for each numeric field
        const numericFields = new Set();
        for (const dp of dataPoints) {
            for (const [key, value] of Object.entries(dp)) {
                if (typeof value === 'number') {
                    numericFields.add(key);
                }
            }
        }

        for (const field of numericFields) {
            const statAnomalies = this.detectStatisticalAnomalies(dataPoints, field);
            allAnomalies.push(...statAnomalies);
        }

        // Detect rule-based anomalies
        const ruleAnomalies = this.detectRuleBasedAnomalies(dataPoints);
        allAnomalies.push(...ruleAnomalies);

        // Remove duplicates based on data point and detection method
        const uniqueAnomalies = new Map();
        for (const anomaly of allAnomalies) {
            const key = `${anomaly.entityId}:${anomaly.detectionMethod}:${anomaly.description}`;
            if (!uniqueAnomalies.has(key) || uniqueAnomalies.get(key).confidence < anomaly.confidence) {
                uniqueAnomalies.set(key, anomaly);
            }
        }

        // Save anomalies to store
        for (const anomaly of uniqueAnomalies.values()) {
            this.store.saveAnomaly(anomaly);
        }

        console.log(`Detected and saved ${uniqueAnomalies.size} unique anomalies from ${dataPoints.length} data points`);

        // Emit event
        this.emit('anomaliesDetected', {
            timestamp: Date.now(),
            count: uniqueAnomalies.size,
            dataPointsProcessed: dataPoints.length
        });

        return Array.from(uniqueAnomalies.values());
    }

    async ingestData() {
        const allDataPoints = [];

        for (const [sourceName, sourceFunc] of Object.entries(this.dataSources)) {
            try {
                const sourceData = await sourceFunc();

                if (Array.isArray(sourceData)) {
                    allDataPoints.push(...sourceData);
                    console.log(`Ingested ${sourceData.length} data points from ${sourceName}`);
                }
            } catch (error) {
                console.error(`Error ingesting data from ${sourceName}:`, error.message);
            }
        }

        return allDataPoints;
    }

    async runPipeline() {
        // Ingest data from all sources
        const dataPoints = await this.ingestData();

        if (dataPoints.length > 0) {
            // Process through anomaly detection
            await this.processDataBatch(dataPoints);
            console.log(`Completed anomaly detection for ${dataPoints.length} data points`);
        } else {
            console.log("No new data to process");
        }
    }

    async runContinuous() {
        if (this.running) {
            throw new Error('Anomaly detector is already running');
        }

        this.running = true;
        console.log('Starting anomaly detector...');

        const runOnce = async () => {
            if (this.running) {
                try {
                    await this.runPipeline();

                    // Schedule next run
                    this.intervalId = setTimeout(runOnce, this.config.processing.batchInterval);
                } catch (error) {
                    console.error('Error in main loop:', error.message);
                    // Schedule retry after delay
                    this.intervalId = setTimeout(runOnce, 5000);
                }
            }
        };

        // Start the first run
        await runOnce();
    }

    async stop() {
        if (!this.running) {
            return;
        }

        this.running = false;

        if (this.intervalId) {
            clearTimeout(this.intervalId);
            this.intervalId = null;
        }

        console.log('Anomaly detector stopped');
        this.emit('stopped');
    }

    async getStatus() {
        return {
            running: this.running,
            sources: Object.keys(this.dataSources),
            unacknowledgedAnomalies: this.store.getUnacknowledgedAnomalies().length,
            config: {
                batchInterval: this.config.processing.batchInterval,
                batchSize: this.config.processing.batchSize
            }
        };
    }
}

// If running directly, start the detector
if (require.main === module) {
    const args = process.argv.slice(2);

    // Parse command line arguments
    const configIndex = args.indexOf('--config');
    const configPath = configIndex !== -1 ? args[configIndex + 1] : null;

    const testModeIndex = args.indexOf('--test-mode');
    const testMode = testModeIndex !== -1;

    const detector = new AnomalyDetector(configPath);

    if (testMode) {
        // Register sample data source for testing
        const mockDataSource = async () => {
            const dataPoints = [];
            const count = Math.floor(Math.random() * 50) + 50; // 50-100 data points

            for (let i = 0; i < count; i++) {
                // Generate normal data
                let baseValue = Math.random() * 30 + 85; // Mean ~100, std dev ~15

                // Occasionally inject anomalies (5% of the time)
                if (Math.random() < 0.05) {
                    baseValue = Math.random() * 50 + 150; // Much higher than normal
                }

                dataPoints.push({
                    id: `mock_${i}`,
                    timestamp: Date.now() - Math.floor(Math.random() * 3600000), // Within last hour
                    entity_type: 'test_metric',
                    value: baseValue,
                    category: Math.random() > 0.5 ? 'performance' : 'financial'
                });
            }

            return dataPoints;
        };

        detector.registerDataSource('mock_source', mockDataSource);
    }

    // Handle shutdown gracefully
    const shutdown = async () => {
        console.log('\nReceived interrupt signal, stopping detector...');
        await detector.stop();
        process.exit(0);
    };

    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);

    // Start detector
    detector.runContinuous().catch(err => {
        console.error('Error starting detector:', err);
        process.exit(1);
    });

    // Listen for events
    detector.on('anomaliesDetected', (data) => {
        console.log(`Anomalies detected at ${new Date(data.timestamp).toISOString()}: ${data.count} anomalies from ${data.dataPointsProcessed} data points`);
    });

    detector.on('stopped', () => {
        console.log('Detector stopped successfully');
    });
}

module.exports = {
    AnomalyDetector,
    Anomaly,
    AnomalySeverity,
    AnomalyType
};