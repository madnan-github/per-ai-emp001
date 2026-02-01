/**
 * Notification Aggregator - JavaScript Implementation
 *
 * This script implements a notification aggregator that collects, processes, and
 * delivers notifications from multiple sources to create a unified, prioritized feed
 * of alerts for the AI employee to process.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const EventEmitter = require('events');
const { spawn } = require('child_process');

class NotificationSeverity {
    static CRITICAL = 1;
    static HIGH = 2;
    static MEDIUM = 3;
    static LOW = 4;

    static toString(severity) {
        switch (severity) {
            case NotificationSeverity.CRITICAL: return 'critical';
            case NotificationSeverity.HIGH: return 'high';
            case NotificationSeverity.MEDIUM: return 'medium';
            case NotificationSeverity.LOW: return 'low';
            default: return 'unknown';
        }
    }
}

class NotificationCategory {
    static SYSTEM = 'system';
    static BUSINESS = 'business';
    static COMMUNICATION = 'communication';
    static MONITORING = 'monitoring';
    static SECURITY = 'security';
}

class Notification {
    constructor(options = {}) {
        this.id = options.id || this.generateId();
        this.source = options.source || 'unknown';
        this.timestamp = options.timestamp || Date.now();
        this.category = options.category || NotificationCategory.SYSTEM;
        this.severity = options.severity || NotificationSeverity.LOW;
        this.title = options.title || 'Untitled Notification';
        this.description = options.description || '';
        this.correlationId = options.correlationId || null;
        this.metadata = options.metadata || {};
        this.acknowledged = options.acknowledged || false;
        this.delivered = options.delivered || false;
    }

    generateId() {
        const content = `${this.source}:${this.title}:${this.timestamp}`;
        return crypto.createHash('sha256').update(content).digest('hex').substring(0, 16);
    }

    toJSON() {
        return {
            id: this.id,
            source: this.source,
            timestamp: this.timestamp,
            category: this.category,
            severity: this.severity,
            title: this.title,
            description: this.description,
            correlationId: this.correlationId,
            metadata: this.metadata,
            acknowledged: this.acknowledged,
            delivered: this.delivered
        };
    }
}

class NotificationStore {
    constructor(dbPath = './notifications.json') {
        this.dbPath = dbPath;
        this.notifications = this.loadNotifications();
    }

    loadNotifications() {
        try {
            if (fs.existsSync(this.dbPath)) {
                const data = fs.readFileSync(this.dbPath, 'utf8');
                return JSON.parse(data);
            }
        } catch (error) {
            console.error('Error loading notifications:', error.message);
        }
        return [];
    }

    saveNotifications() {
        try {
            fs.writeFileSync(this.dbPath, JSON.stringify(this.notifications, null, 2));
        } catch (error) {
            console.error('Error saving notifications:', error.message);
        }
    }

    saveNotification(notification) {
        // Check if notification already exists
        const existingIndex = this.notifications.findIndex(n => n.id === notification.id);

        if (existingIndex !== -1) {
            this.notifications[existingIndex] = { ...notification.toJSON() };
        } else {
            this.notifications.push({ ...notification.toJSON() });
        }

        this.saveNotifications();
    }

    getUnprocessedNotifications(limit = 100) {
        return this.notifications
            .filter(n => !n.acknowledged && !n.delivered)
            .sort((a, b) => a.severity - b.severity || b.timestamp - a.timestamp)
            .slice(0, limit)
            .map(data => new Notification(data));
    }

    acknowledgeNotification(notificationId) {
        const notification = this.notifications.find(n => n.id === notificationId);
        if (notification) {
            notification.acknowledged = true;
            this.saveNotifications();
        }
    }

    markAsDelivered(notificationId) {
        const notification = this.notifications.find(n => n.id === notificationId);
        if (notification) {
            notification.delivered = true;
            this.saveNotifications();
        }
    }
}

class NotificationClassifier {
    constructor(config = {}) {
        this.config = config;
        this.severityMapping = config.classification?.severityMapping || {};
    }

    classifyNotification(rawNotification) {
        const source = rawNotification.source || 'unknown';
        const title = rawNotification.title || 'Untitled Notification';
        const description = rawNotification.description || '';
        const timestamp = rawNotification.timestamp || Date.now();

        // Determine category
        const category = this.determineCategory(rawNotification);

        // Determine severity
        const severity = this.determineSeverity(rawNotification, source, title, description);

        // Generate unique ID
        const notificationId = this.generateNotificationId(source, title, timestamp);

        // Determine correlation ID
        const correlationId = this.determineCorrelationId(rawNotification);

        // Prepare metadata
        const metadata = { ...rawNotification.metadata };
        metadata.originalSource = source;
        metadata.classificationMethod = 'automatic';

        return new Notification({
            id: notificationId,
            source,
            timestamp,
            category,
            severity,
            title,
            description,
            correlationId,
            metadata
        });
    }

    determineCategory(notification) {
        // Check explicit category
        if (notification.category) {
            return notification.category;
        }

        // Determine category based on source
        const source = (notification.source || '').toLowerCase();

        if (source.includes('system') || source.includes('os') || source.includes('hardware') || source.includes('network')) {
            return NotificationCategory.SYSTEM;
        } else if (source.includes('email') || source.includes('slack') || source.includes('teams') || source.includes('chat')) {
            return NotificationCategory.COMMUNICATION;
        } else if (source.includes('monitor') || source.includes('alert') || source.includes('prometheus') || source.includes('datadog')) {
            return NotificationCategory.MONITORING;
        } else if (source.includes('security') || source.includes('firewall') || source.includes('intrusion')) {
            return NotificationCategory.SECURITY;
        } else {
            return NotificationCategory.BUSINESS;
        }
    }

    determineSeverity(notification, source, title, description) {
        // Check explicit severity
        if ('severity' in notification) {
            const severityVal = notification.severity;
            if (typeof severityVal === 'string') {
                const severityMap = {
                    'critical': NotificationSeverity.CRITICAL,
                    'high': NotificationSeverity.HIGH,
                    'medium': NotificationSeverity.MEDIUM,
                    'low': NotificationSeverity.LOW
                };
                return severityMap[severityVal.toLowerCase()] || NotificationSeverity.LOW;
            }
            return Math.min(Math.max(severityVal, 1), 4); // Ensure it's between 1-4
        }

        // Apply classification rules based on content
        const titleLower = title.toLowerCase();
        const descLower = description.toLowerCase();

        // Check for critical keywords
        const criticalKeywords = ['critical', 'crucial', 'emergency', 'outage', 'breach', 'attack'];
        if (criticalKeywords.some(keyword => titleLower.includes(keyword) || descLower.includes(keyword))) {
            return NotificationSeverity.CRITICAL;
        }

        const highKeywords = ['high', 'urgent', 'important', 'failure', 'error'];
        if (highKeywords.some(keyword => titleLower.includes(keyword) || descLower.includes(keyword))) {
            return NotificationSeverity.HIGH;
        }

        const mediumKeywords = ['medium', 'moderate', 'warning', 'caution'];
        if (mediumKeywords.some(keyword => titleLower.includes(keyword) || descLower.includes(keyword))) {
            return NotificationSeverity.MEDIUM;
        }

        return NotificationSeverity.LOW;
    }

    generateNotificationId(source, title, timestamp) {
        const content = `${source}:${title}:${timestamp}`;
        return crypto.createHash('sha256').update(content).digest('hex').substring(0, 16);
    }

    determineCorrelationId(notification) {
        // Check for explicit correlation ID
        for (const field of ['correlationId', 'groupId', 'threadId']) {
            if (field in notification) {
                return String(notification[field]);
            }
        }

        // Generate correlation ID based on content similarity
        const title = notification.title || '';
        const source = notification.source || '';

        if (title.length > 10) { // Only for reasonably long titles
            const titleBase = title.toLowerCase().replace(/\d+/g, '#'); // Replace numbers with #
            const content = `${source}:${titleBase}`;
            return crypto.createHash('md5').update(content).digest('hex').substring(0, 12);
        }

        return null;
    }
}

class NotificationCorrelator {
    constructor(config = {}) {
        this.config = config;
        this.correlationRules = config.correlation?.rules || {};
        this.activeGroups = {}; // Store ongoing correlation groups
    }

    correlateNotifications(notifications) {
        // Group notifications by potential correlation factors
        const correlationBuckets = new Map();

        for (const notification of notifications) {
            let bucketKey;

            if (notification.correlationId) {
                bucketKey = notification.correlationId;
            } else {
                // Create a correlation key based on source and content similarity
                bucketKey = this.createCorrelationKey(notification);
            }

            if (!correlationBuckets.has(bucketKey)) {
                correlationBuckets.set(bucketKey, []);
            }
            correlationBuckets.get(bucketKey).push(notification);
        }

        // Apply correlation rules to each bucket
        const correlatedNotifications = [];
        for (const [bucketKey, bucketNotifications] of correlationBuckets) {
            if (bucketNotifications.length === 1) {
                // Single notification, no correlation needed
                correlatedNotifications.push(...bucketNotifications);
            } else {
                // Apply correlation rules
                const correlatedGroup = this.applyCorrelationRules(bucketNotifications);
                correlatedNotifications.push(...correlatedGroup);
            }
        }

        return correlatedNotifications;
    }

    createCorrelationKey(notification) {
        // Use source and first 50 characters of title for grouping
        const titlePrefix = notification.title.substring(0, 50).toLowerCase().replace(/\s+/g, '_');
        return `${notification.source}:${titlePrefix}`;
    }

    applyCorrelationRules(notifications) {
        if (notifications.length < 2) {
            return notifications;
        }

        // For now, create a summary notification for groups with more than 2 notifications
        if (notifications.length > 2) {
            // Create a summary notification
            const summaryTitle = `Grouped Alert: ${notifications.length} related notifications`;
            let summaryDesc = `Multiple notifications from ${notifications[0].source}:\n`;

            for (let i = 0; i < Math.min(notifications.length, 5); i++) { // Show first 5
                summaryDesc += `- ${notifications[i].title}\n`;
            }

            if (notifications.length > 5) {
                summaryDesc += `\nAnd ${notifications.length - 5} more...`;
            }

            // Use the highest severity in the group
            const maxSeverity = Math.min(...notifications.map(n => n.severity));

            const summaryNotification = new Notification({
                id: `group_${crypto.createHash('md5').update(summaryTitle).digest('hex').substring(0, 8)}`,
                source: notifications[0].source,
                timestamp: Math.max(...notifications.map(n => n.timestamp)),
                category: notifications[0].category,
                severity: maxSeverity,
                title: summaryTitle,
                description: summaryDesc,
                correlationId: notifications[0].correlationId,
                metadata: {
                    groupSize: notifications.length,
                    individualIds: notifications.map(n => n.id),
                    originalSeverities: notifications.map(n => n.severity)
                }
            });

            return [summaryNotification];
        } else {
            return notifications;
        }
    }
}

class NotificationSuppressor {
    constructor(config = {}) {
        this.config = config;
        this.suppressionRules = config.suppression?.rules || {};
        this.recentNotifications = new Map(); // Cache of recent notifications
        this.suppressionCache = new Map(); // Cache of suppressed notifications
    }

    filterNotifications(notifications) {
        const filteredNotifications = [];

        for (const notification of notifications) {
            if (!this.shouldSuppress(notification)) {
                filteredNotifications.push(notification);
                // Add to recent notifications cache
                this.addToRecentCache(notification);
            }
        }

        return filteredNotifications;
    }

    shouldSuppress(notification) {
        // Check against recent notifications to prevent duplicates
        const fingerprint = this.createFingerprint(notification);

        // Check if this notification is a duplicate within the suppression window
        if (this.recentNotifications.has(fingerprint)) {
            const lastSeen = this.recentNotifications.get(fingerprint);
            const suppressionWindow = (this.config.suppressionWindowSizeMinutes || 10) * 60 * 1000; // Convert to ms

            if (Date.now() - lastSeen < suppressionWindow) {
                return true;
            }
        }

        // Check against configured suppression rules
        for (const [ruleName, ruleConfig] of Object.entries(this.suppressionRules)) {
            if (this.matchesSuppressionRule(notification, ruleConfig)) {
                return true;
            }
        }

        return false;
    }

    createFingerprint(notification) {
        const content = `${notification.source}:${notification.title}:${notification.description.substring(0, 100)}`;
        return crypto.createHash('md5').update(content).digest('hex');
    }

    matchesSuppressionRule(notification, ruleConfig) {
        // For now, implement basic condition matching
        const conditions = ruleConfig.conditions || [];

        for (const condition of conditions) {
            const field = condition.field;
            const operator = condition.operator;
            const value = condition.value;

            if (field === 'category' && operator === '=') {
                if (notification.category !== value) {
                    return false;
                }
            } else if (field === 'severity' && operator === '>=') {
                if (notification.severity > value) {
                    return false;
                }
            }
        }

        // If all conditions match, this notification should be suppressed
        return conditions.length > 0;
    }

    addToRecentCache(notification) {
        const fingerprint = this.createFingerprint(notification);
        this.recentNotifications.set(fingerprint, Date.now());

        // Clean up old entries
        const currentTime = Date.now();
        for (const [key, timestamp] of this.recentNotifications) {
            if (currentTime - timestamp > 3600 * 1000) { // Keep for 1 hour
                this.recentNotifications.delete(key);
            }
        }
    }
}

class NotificationDeliveryManager {
    constructor(config = {}, notificationStore) {
        this.config = config;
        this.store = notificationStore;
        this.deliveryChannels = {};
        this.setupDeliveryChannels();
    }

    setupDeliveryChannels() {
        const deliveryConfig = this.config.delivery?.channels || {};

        if (deliveryConfig.email?.enabled) {
            this.deliveryChannels.email = this.setupEmailDelivery(
                deliveryConfig.email
            );
        }

        if (deliveryConfig.chat?.slack?.webhookUrls) {
            this.deliveryChannels.chat = this.setupChatDelivery(
                deliveryConfig.chat.slack
            );
        }
    }

    setupEmailDelivery(config) {
        return async (notification) => {
            try {
                // In a real implementation, this would connect to an SMTP server
                console.log(`Email sent for notification ${notification.id}`);

                // For demonstration purposes, we'll just log the email content
                const emailBody = `
Notification Alert
==================

Source: ${notification.source}
Category: ${notification.category}
Severity: ${NotificationSeverity.toString(notification.severity)}

Title: ${notification.title}

Description:
${notification.description}

Timestamp: ${new Date(notification.timestamp)}
ID: ${notification.id}

This is an automated notification from the AI Employee Notification System.
                `;

                console.log('Email content:', emailBody);
                return true;
            } catch (error) {
                console.error(`Failed to send email for notification ${notification.id}:`, error.message);
                return false;
            }
        };
    }

    setupChatDelivery(config) {
        return async (notification) => {
            try {
                const webhookUrls = config.webhookUrls || {};

                // Determine appropriate webhook based on severity
                let webhookUrl;
                if (notification.severity === NotificationSeverity.CRITICAL) {
                    webhookUrl = webhookUrls.critical;
                } else if (notification.severity <= NotificationSeverity.HIGH) {
                    webhookUrl = webhookUrls.high;
                } else {
                    webhookUrl = webhookUrls.medium || webhookUrls.critical;
                }

                if (webhookUrl) {
                    const payload = {
                        text: `*[${NotificationSeverity.toString(notification.severity)}]* ${notification.title}`,
                        blocks: [
                            {
                                type: 'section',
                                text: {
                                    type: 'mrkdwn',
                                    text: `*[${NotificationSeverity.toString(notification.severity)}]* ${notification.title}\n${notification.description}`
                                }
                            },
                            {
                                type: 'context',
                                elements: [
                                    {
                                        type: 'mrkdwn',
                                        text: `Source: ${notification.source} | Time: ${new Date(notification.timestamp)}`
                                    }
                                ]
                            }
                        ]
                    };

                    const response = await fetch(webhookUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(payload)
                    });

                    if (response.ok) {
                        console.log(`Chat notification sent for ${notification.id}`);
                        return true;
                    } else {
                        console.error(`Failed to send chat notification: ${response.status}`);
                        return false;
                    }
                } else {
                    console.log('No appropriate webhook URL found for notification severity');
                    return false;
                }
            } catch (error) {
                console.error(`Failed to send chat notification for ${notification.id}:`, error.message);
                return false;
            }
        };
    }

    async deliverNotification(notification) {
        let successCount = 0;
        const totalChannels = Object.keys(this.deliveryChannels).length;

        for (const [channelName, deliveryFunc] of Object.entries(this.deliveryChannels)) {
            try {
                const result = await deliveryFunc(notification);
                if (result) {
                    successCount++;
                }
            } catch (error) {
                console.error(`Error delivering notification ${notification.id} via ${channelName}:`, error.message);
            }
        }

        // Mark as delivered if at least one channel succeeded
        if (successCount > 0) {
            this.store.markAsDelivered(notification.id);
            return true;
        }

        return false;
    }
}

class NotificationAggregator extends EventEmitter {
    constructor(configPath = null) {
        super();
        this.config = this.loadConfig(configPath);
        this.store = new NotificationStore();
        this.classifier = new NotificationClassifier(this.config);
        this.correlator = new NotificationCorrelator(this.config);
        this.suppressor = new NotificationSuppressor(this.config);
        this.deliveryManager = new NotificationDeliveryManager(this.config, this.store);
        this.sources = {};
        this.running = false;
        this.intervalId = null;
    }

    loadConfig(configPath = null) {
        const defaultConfig = {
            processing: {
                batchSize: 100,
                batchInterval: 5000, // milliseconds
                maxWorkers: 10
            },
            storage: {
                retentionDays: 30
            },
            classification: {
                severityMapping: {},
                categoryMapping: {}
            },
            correlation: {
                rules: {},
                windowSize: 300 // seconds
            },
            suppression: {
                rules: {},
                windowSize: 600 // seconds
            },
            delivery: {
                channels: {
                    email: { enabled: false },
                    push: { enabled: false },
                    chat: { enabled: false }
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

    registerSource(name, sourceFunc) {
        this.sources[name] = sourceFunc;
    }

    async ingestNotifications() {
        const allNotifications = [];

        for (const [sourceName, sourceFunc] of Object.entries(this.sources)) {
            try {
                const sourceNotifications = await sourceFunc();

                if (Array.isArray(sourceNotifications)) {
                    allNotifications.push(...sourceNotifications);
                    console.log(`Ingested ${sourceNotifications.length} notifications from ${sourceName}`);
                }
            } catch (error) {
                console.error(`Error ingesting notifications from ${sourceName}:`, error.message);
            }
        }

        return allNotifications;
    }

    processNotifications(rawNotifications) {
        // Classify notifications
        const classifiedNotifications = [];
        for (const rawNote of rawNotifications) {
            try {
                const classified = this.classifier.classifyNotification(rawNote);
                classifiedNotifications.push(classified);
            } catch (error) {
                console.error('Error classifying notification:', error.message);
            }
        }

        // Apply suppression rules
        const filteredNotifications = this.suppressor.filterNotifications(classifiedNotifications);

        // Apply correlation rules
        const correlatedNotifications = this.correlator.correlateNotifications(filteredNotifications);

        // Save to store
        for (const notification of correlatedNotifications) {
            this.store.saveNotification(notification);
        }

        return correlatedNotifications;
    }

    async deliverNotifications(notifications) {
        for (const notification of notifications) {
            await this.deliveryManager.deliverNotification(notification);
        }
    }

    async runPipeline() {
        // Ingest notifications from all sources
        const rawNotifications = await this.ingestNotifications();

        if (rawNotifications.length > 0) {
            // Process through pipeline
            const processedNotifications = this.processNotifications(rawNotifications);

            // Deliver notifications
            await this.deliverNotifications(processedNotifications);

            console.log(`Processed and delivered ${processedNotifications.length} notifications`);

            // Emit event
            this.emit('pipelineComplete', {
                timestamp: Date.now(),
                processedCount: processedNotifications.length
            });
        } else {
            console.log('No new notifications to process');
        }
    }

    async runContinuous() {
        if (this.running) {
            throw new Error('Notification aggregator is already running');
        }

        this.running = true;
        console.log('Starting notification aggregator...');

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

        console.log('Notification aggregator stopped');
        this.emit('stopped');
    }

    async getStatus() {
        return {
            running: this.running,
            sources: Object.keys(this.sources),
            unprocessedNotifications: this.store.getUnprocessedNotifications().length,
            config: {
                batchInterval: this.config.processing.batchInterval,
                batchSize: this.config.processing.batchSize
            }
        };
    }
}

// If running directly, start the aggregator
if (require.main === module) {
    const args = process.argv.slice(2);

    // Parse command line arguments
    const configIndex = args.indexOf('--config');
    const configPath = configIndex !== -1 ? args[configIndex + 1] : null;

    const testModeIndex = args.indexOf('--test-mode');
    const testMode = testModeIndex !== -1;

    const aggregator = new NotificationAggregator(configPath);

    if (testMode) {
        // Register sample sources for testing
        const mockSource = async () => {
            const mockNotifications = [];
            const count = Math.floor(Math.random() * 6); // Random 0-5 notifications

            for (let i = 0; i < count; i++) {
                mockNotifications.push({
                    source: 'mock_source',
                    title: `Mock Alert ${i}`,
                    description: `This is a mock notification #${i}`,
                    timestamp: Date.now(),
                    category: Math.random() > 0.5 ? 'system' : 'monitoring',
                    severity: ['low', 'medium', 'high', 'critical'][Math.floor(Math.random() * 4)]
                });
            }
            return mockNotifications;
        };

        aggregator.registerSource('mock_source', mockSource);
    }

    // Handle shutdown gracefully
    const shutdown = async () => {
        console.log('\nReceived interrupt signal, stopping aggregator...');
        await aggregator.stop();
        process.exit(0);
    };

    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);

    // Start aggregator
    aggregator.runContinuous().catch(err => {
        console.error('Error starting aggregator:', err);
        process.exit(1);
    });

    // Listen for events
    aggregator.on('pipelineComplete', (data) => {
        console.log(`Pipeline completed at ${new Date(data.timestamp).toISOString()}, processed ${data.processedCount} notifications`);
    });

    aggregator.on('stopped', () => {
        console.log('Aggregator stopped successfully');
    });
}

module.exports = {
    NotificationAggregator,
    Notification,
    NotificationSeverity,
    NotificationCategory
};