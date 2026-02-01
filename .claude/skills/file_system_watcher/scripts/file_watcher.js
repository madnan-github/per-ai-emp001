/**
 * File System Watcher - JavaScript Implementation
 *
 * This script implements a file system watcher that monitors specified directories
 * for file system events (creation, modification, deletion, etc.) and processes
 * them according to the configured rules and priorities.
 */

const fs = require('fs');
const path = require('path');
const chokidar = require('chokidar');
const crypto = require('crypto');
const EventEmitter = require('events');

class FileWatcher extends EventEmitter {
    constructor(config = {}) {
        super();

        this.config = {
            watchedDirectories: [
                path.join(require('os').homedir(), 'Downloads'),
                path.join(require('os').homedir(), 'Documents'),
                path.join(require('os').homedir(), 'Desktop')
            ],
            ignorePatterns: [
                '**/*.tmp',
                '**/*.temp',
                '**/tmp/**',
                '**/cache/**',
                '**/.git/**',
                '**/*.log'
            ],
            includePatterns: ['**/*.*'],
            eventBatchSize: 10,
            batchInterval: 5000, // milliseconds
            rateLimitPerMinute: 1000,
            enableDeduplication: true,
            hashHistorySize: 1000,
            notificationChannels: ['console'],
            autoActionsEnabled: true,
            ...config
        };

        this.eventQueue = [];
        this.hashHistory = new Map();
        this.batchTimer = null;
        this.running = false;
        this.watcher = null;
        this.rateLimitCount = 0;
        this.rateLimitResetTime = Date.now() + 60000; // 1 minute
    }

    /**
     * Load configuration from file
     */
    async loadConfig(configPath) {
        if (!configPath || !fs.existsSync(configPath)) {
            return this.config;
        }

        try {
            const configData = JSON.parse(fs.readFileSync(configPath, 'utf8'));
            this.config = { ...this.config, ...configData };
        } catch (error) {
            console.error(`Warning: Could not load config ${configPath}:`, error.message);
        }

        return this.config;
    }

    /**
     * Calculate SHA-256 hash of a file
     */
    async calculateFileHash(filePath) {
        if (!fs.existsSync(filePath)) {
            return '';
        }

        try {
            const hash = crypto.createHash('sha256');
            const stream = fs.createReadStream(filePath);

            return new Promise((resolve, reject) => {
                stream.on('data', data => hash.update(data));
                stream.on('end', () => resolve(hash.digest('hex')));
                stream.on('error', reject);
            });
        } catch (error) {
            console.error(`Error calculating hash for ${filePath}:`, error.message);
            return '';
        }
    }

    /**
     * Get file size with error handling
     */
    getFileSize(filePath) {
        try {
            const stats = fs.statSync(filePath);
            return stats.size;
        } catch (error) {
            return 0;
        }
    }

    /**
     * Determine the priority of the event based on file type and location
     */
    determinePriority(eventType, filePath) {
        const extension = path.extname(filePath).toLowerCase();
        const lowerPath = filePath.toLowerCase();

        // Critical events (Priority 1)
        if (lowerPath.includes('malware') || lowerPath.includes('virus') ||
            lowerPath.includes('trojan') || lowerPath.includes('ransom')) {
            return 1;
        }
        if (lowerPath.includes('security') || lowerPath.includes('auth') ||
            lowerPath.includes('password') || lowerPath.includes('credential')) {
            return 1;
        }
        if (['.exe', '.dll', '.sys', '.bat', '.scr'].some(ext => extension.includes(ext))) {
            // Executables in unusual locations get higher priority
            if (lowerPath.includes('downloads') || lowerPath.includes('desktop') ||
                lowerPath.includes('temp')) {
                return 2;
            }
        }

        // High priority events (Priority 2)
        if (lowerPath.includes('finance') || lowerPath.includes('bank') ||
            lowerPath.includes('payment') || lowerPath.includes('invoice') ||
            lowerPath.includes('tax')) {
            return 2;
        }
        if (lowerPath.includes('confidential') || lowerPath.includes('private') ||
            lowerPath.includes('secret')) {
            return 2;
        }
        if (['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv'].some(ext => extension.includes(ext))) {
            return 2; // Business documents
        }

        // Medium priority events (Priority 3)
        if (['.txt', '.rtf', '.odt', '.ppt', '.pptx'].some(ext => extension.includes(ext))) {
            return 3;
        }

        // Low priority events (Priority 4) - default
        return 4;
    }

    /**
     * Check if an event should be processed based on filters
     */
    shouldProcessEvent(filePath) {
        const pathObj = path.resolve(filePath);

        // Check if path matches include patterns
        if (this.config.includePatterns.length > 0) {
            let matched = false;
            for (const pattern of this.config.includePatterns) {
                if (this.minimatch(pathObj, pattern)) {
                    matched = true;
                    break;
                }
            }
            if (!matched) {
                return false;
            }
        }

        // Check if path matches ignore patterns
        for (const pattern of this.config.ignorePatterns) {
            if (this.minimatch(pathObj, pattern)) {
                return false;
            }
        }

        return true;
    }

    /**
     * Simple minimatch implementation for pattern matching
     */
    minimatch(filePath, pattern) {
        const normalizedPath = filePath.replace(/\\/g, '/');
        const normalizedPattern = pattern.replace(/\\/g, '/');

        // Convert glob pattern to regex
        let regexPattern = normalizedPattern
            .replace(/\./g, '\\.')
            .replace(/\*/g, '.*')
            .replace(/\?/g, '.');

        if (regexPattern.startsWith('**')) {
            regexPattern = '.*' + regexPattern.substring(2);
        }

        const regex = new RegExp(`^${regexPattern}$`);
        return regex.test(normalizedPath);
    }

    /**
     * Add event to the queue for processing
     */
    async addEvent(eventType, filePath) {
        // Rate limiting
        if (Date.now() > this.rateLimitResetTime) {
            this.rateLimitCount = 0;
            this.rateLimitResetTime = Date.now() + 60000;
        }

        if (this.rateLimitCount >= this.config.rateLimitPerMinute) {
            console.warn(`Rate limit exceeded for ${eventType} event on ${filePath}`);
            return;
        }

        this.rateLimitCount++;

        if (!this.shouldProcessEvent(filePath)) {
            return;
        }

        const fileSize = this.getFileSize(filePath);
        const fileHash = await this.calculateFileHash(filePath);
        const priority = this.determinePriority(eventType, filePath);

        const fileEvent = {
            eventType,
            filePath,
            timestamp: Date.now(),
            fileSize,
            fileHash,
            eventPriority: priority,
            sourceDirectory: path.dirname(filePath),
            isSensitive: false
        };

        this.eventQueue.push(fileEvent);

        // Start batch timer if not already running
        if (!this.batchTimer) {
            this.batchTimer = setTimeout(() => {
                this.processEventsBatch();
                this.batchTimer = null;
            }, this.config.batchInterval);
        }

        // Process batch if it reaches the batch size
        if (this.eventQueue.length >= this.config.eventBatchSize) {
            clearTimeout(this.batchTimer);
            this.batchTimer = null;
            this.processEventsBatch();
        }
    }

    /**
     * Process a batch of events
     */
    async processEventsBatch() {
        if (this.eventQueue.length === 0) {
            return;
        }

        let events = [...this.eventQueue];
        this.eventQueue = [];

        // Filter out duplicates if deduplication is enabled
        if (this.config.enableDeduplication) {
            events = this.filterDuplicates(events);
        }

        // Sort events by priority (critical first)
        events.sort((a, b) => a.eventPriority - b.eventPriority);

        // Process each event according to its priority
        for (const event of events) {
            await this.processSingleEvent(event);
        }
    }

    /**
     * Filter out duplicate events based on file hash and path
     */
    filterDuplicates(events) {
        const filteredEvents = [];
        const currentTime = Date.now();

        for (const event of events) {
            // Create a unique identifier for the event
            const eventKey = `${event.filePath}_${event.eventType}`;
            const eventHash = crypto.createHash('md5').update(eventKey).digest('hex');

            // Check if this event has been seen recently
            if (!this.hashHistory.has(eventHash) ||
                (currentTime - this.hashHistory.get(eventHash)) > 300000) { // 5 minutes

                this.hashHistory.set(eventHash, currentTime);
                filteredEvents.push(event);

                // Clean up old entries from hash history
                for (const [key, timestamp] of this.hashHistory.entries()) {
                    if (currentTime - timestamp > 300000) { // 5 minutes
                        this.hashHistory.delete(key);
                    }
                }
            }
        }

        return filteredEvents;
    }

    /**
     * Process a single file event according to its priority and type
     */
    async processSingleEvent(event) {
        // Log the event
        this.logEvent(event);

        // Take action based on priority
        switch (event.eventPriority) {
            case 1: // Critical
                await this.handleCriticalEvent(event);
                break;
            case 2: // High
                await this.handleHighPriorityEvent(event);
                break;
            case 3: // Medium
                await this.handleMediumPriorityEvent(event);
                break;
            default: // Low
                await this.handleLowPriorityEvent(event);
                break;
        }
    }

    /**
     * Log the event to console and/or file
     */
    logEvent(event) {
        const timestampStr = new Date(event.timestamp).toISOString();
        const priorityStr = {1: 'CRITICAL', 2: 'HIGH', 3: 'MEDIUM', 4: 'LOW'}[event.eventPriority] || 'UNKNOWN';

        console.log(`[${timestampStr}] [${priorityStr}] ${event.eventType.toUpperCase()}: ${event.filePath} (${event.fileSize} bytes)`);

        // Emit event for other listeners
        this.emit('fileEvent', event);

        // Additional logging could go here (to file, database, etc.)
    }

    /**
     * Handle critical priority events
     */
    async handleCriticalEvent(event) {
        console.log(`🚨 CRITICAL EVENT: ${event.eventType} - ${event.filePath}`);

        // Emit critical event
        this.emit('criticalEvent', event);

        // Take immediate action for critical events
        if (this.config.autoActionsEnabled) {
            // Quarantine suspicious files
            if (['.exe', '.dll', '.sys', '.bat', '.scr'].some(ext => event.filePath.toLowerCase().includes(ext))) {
                await this.quarantineFile(event.filePath);
            }

            // Send immediate notification
            await this.sendNotification(`Critical security event: ${event.eventType} ${event.filePath}`, 'critical');
        }
    }

    /**
     * Handle high priority events
     */
    async handleHighPriorityEvent(event) {
        console.log(`⚠️ HIGH PRIORITY: ${event.eventType} - ${event.filePath}`);

        // Emit high priority event
        this.emit('highPriorityEvent', event);

        if (this.config.autoActionsEnabled) {
            // Send notification for high priority events
            await this.sendNotification(`High priority event: ${event.eventType} ${event.filePath}`, 'high');
        }
    }

    /**
     * Handle medium priority events
     */
    async handleMediumPriorityEvent(event) {
        console.log(`📝 MEDIUM PRIORITY: ${event.eventType} - ${event.filePath}`);

        // Emit medium priority event
        this.emit('mediumPriorityEvent', event);

        // Medium priority events are typically logged but not acted upon automatically
    }

    /**
     * Handle low priority events
     */
    async handleLowPriorityEvent(event) {
        // Low priority events are just logged silently
        // Emit low priority event
        this.emit('lowPriorityEvent', event);
    }

    /**
     * Move suspicious file to quarantine location
     */
    async quarantineFile(filePath) {
        try {
            const quarantineDir = path.join(require('os').homedir(), '.quarantine');

            // Create quarantine directory if it doesn't exist
            if (!fs.existsSync(quarantineDir)) {
                fs.mkdirSync(quarantineDir, { recursive: true });
            }

            const filename = path.basename(filePath);
            const quarantinePath = path.join(quarantineDir, `quarantine_${Date.now()}_${filename}`);

            // Move file to quarantine
            fs.renameSync(filePath, quarantinePath);
            console.log(`File quarantined: ${filePath} -> ${quarantinePath}`);

            // Create incident report
            await this.createIncidentReport(filePath, quarantinePath);

            // Emit quarantine event
            this.emit('fileQuarantined', { originalPath: filePath, quarantinePath });
        } catch (error) {
            console.error(`Error quarantining file ${filePath}:`, error.message);
        }
    }

    /**
     * Create an incident report for quarantined files
     */
    async createIncidentReport(originalPath, quarantinePath) {
        try {
            const reportDir = path.join(require('os').homedir(), '.incident_reports');

            // Create incident reports directory if it doesn't exist
            if (!fs.existsSync(reportDir)) {
                fs.mkdirSync(reportDir, { recursive: true });
            }

            const reportPath = path.join(reportDir, `incident_${Date.now()}.json`);

            const reportData = {
                timestamp: new Date().toISOString(),
                originalPath,
                quarantinePath,
                actionTaken: 'file_quarantine',
                severity: 'critical'
            };

            fs.writeFileSync(reportPath, JSON.stringify(reportData, null, 2));

            console.log(`Incident report created: ${reportPath}`);

            // Emit incident report event
            this.emit('incidentReportCreated', reportData);
        } catch (error) {
            console.error(`Error creating incident report:`, error.message);
        }
    }

    /**
     * Send notification through configured channels
     */
    async sendNotification(message, priority = 'normal') {
        for (const channel of this.config.notificationChannels) {
            switch (channel) {
                case 'console':
                    console.log(`NOTIFICATION (${priority}): ${message}`);
                    break;
                // Additional notification channels could be implemented here
                // (email, SMS, Slack, etc.)
                default:
                    console.log(`[Channel: ${channel}] NOTIFICATION (${priority}): ${message}`);
                    break;
            }
        }

        // Emit notification event
        this.emit('notificationSent', { message, priority, channels: this.config.notificationChannels });
    }

    /**
     * Start monitoring the specified directories
     */
    async start(watchedDirs = null) {
        if (this.running) {
            throw new Error('File watcher is already running');
        }

        this.running = true;

        // Use provided directories or fall back to config
        const dirs = watchedDirs || this.config.watchedDirectories;

        // Initialize chokidar watcher
        this.watcher = chokidar.watch(dirs, {
            ignored: this.config.ignorePatterns,
            persistent: true,
            ignoreInitial: false,
            followSymlinks: false,
            depth: 99,
            interval: 100,
            binaryInterval: 300
        });

        // Set up event handlers
        this.watcher
            .on('add', async (filePath) => {
                await this.addEvent('created', filePath);
            })
            .on('change', async (filePath) => {
                await this.addEvent('modified', filePath);
            })
            .on('unlink', async (filePath) => {
                await this.addEvent('deleted', filePath);
            })
            .on('addDir', async (dirPath) => {
                await this.addEvent('directoryCreated', dirPath);
            })
            .on('unlinkDir', async (dirPath) => {
                await this.addEvent('directoryDeleted', dirPath);
            })
            .on('error', (error) => {
                console.error('File watcher error:', error);
                this.emit('error', error);
            })
            .on('ready', () => {
                console.log(`File watcher started. Watching ${dirs.length} directories.`);
                this.emit('started', { directories: dirs });
            });

        return new Promise((resolve, reject) => {
            this.watcher.on('ready', resolve);
            this.watcher.on('error', reject);
        });
    }

    /**
     * Stop monitoring
     */
    async stop() {
        if (!this.running) {
            return;
        }

        this.running = false;

        // Clear batch timer
        if (this.batchTimer) {
            clearTimeout(this.batchTimer);
            this.batchTimer = null;
        }

        // Process remaining events
        if (this.eventQueue.length > 0) {
            await this.processEventsBatch();
        }

        // Close the watcher
        if (this.watcher) {
            await this.watcher.close();
            this.watcher = null;
        }

        console.log('File watcher stopped.');
        this.emit('stopped');
    }

    /**
     * Toggle auto-actions on/off
     */
    setAutoActions(enabled) {
        this.config.autoActionsEnabled = enabled;
        console.log(`Auto-actions ${enabled ? 'enabled' : 'disabled'}`);
    }

    /**
     * Get current statistics
     */
    getStats() {
        return {
            running: this.running,
            queuedEvents: this.eventQueue.length,
            hashHistorySize: this.hashHistory.size,
            rateLimitCount: this.rateLimitCount,
            rateLimitRemaining: Math.max(0, this.config.rateLimitPerMinute - this.rateLimitCount),
            rateLimitResetTime: this.rateLimitResetTime
        };
    }
}

module.exports = FileWatcher;

// If running directly, start the watcher
if (require.main === module) {
    const args = process.argv.slice(2);

    // Parse command line arguments
    const configIndex = args.indexOf('--config');
    const configPath = configIndex !== -1 ? args[configIndex + 1] : null;

    const dryRunIndex = args.indexOf('--dry-run');
    const dryRun = dryRunIndex !== -1;

    const watcher = new FileWatcher();

    if (dryRun) {
        watcher.setAutoActions(false);
        console.log('Running in DRY RUN mode - no actions will be taken');
    }

    // Load config if provided
    if (configPath) {
        watcher.loadConfig(configPath).then(() => {
            console.log(`Loaded config from: ${configPath}`);
        }).catch(err => {
            console.error('Error loading config:', err);
        });
    }

    console.log('Starting file system watcher...');

    // Handle shutdown gracefully
    const shutdown = async () => {
        console.log('\nReceived interrupt signal, stopping watcher...');
        await watcher.stop();
        process.exit(0);
    };

    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);

    // Start watching
    watcher.start().catch(err => {
        console.error('Error starting watcher:', err);
        process.exit(1);
    });

    // Listen for events
    watcher.on('fileEvent', (event) => {
        console.log(`Event: ${event.eventType} - ${event.filePath}`);
    });

    watcher.on('criticalEvent', (event) => {
        console.log(`Critical event: ${event.eventType} - ${event.filePath}`);
    });
}