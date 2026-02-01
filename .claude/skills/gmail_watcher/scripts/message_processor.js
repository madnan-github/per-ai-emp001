/**
 * GmailWatcherJS: JavaScript module for monitoring Gmail for important/unread messages using the Gmail API.
 *
 * This module watches a Gmail account for new messages, applies filtering rules
 * to identify important communications, and triggers appropriate actions based
 * on predefined criteria.
 */

const fs = require('fs').promises;
const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const { google } = require('googleapis'); // Assuming googleapis is available

// Priority levels for messages
const MessagePriority = {
    CRITICAL: 5,
    HIGH: 4,
    MEDIUM: 3,
    LOW: 2,
    TRIVIAL: 1
};

// Categories for classifying messages
const MessageCategory = {
    URGENT: "urgent",
    MEETING: "meeting",
    FINANCIAL: "financial",
    SECURITY: "security",
    BUSINESS: "business",
    CUSTOMER: "customer",
    PERSONAL: "personal",
    NEWSLETTER: "newsletter",
    SOCIAL: "social",
    NOTIFICATION: "notification",
    SPAM: "spam"
};

class WatchedMessage {
    constructor(options = {}) {
        this.id = options.id || this.generateId();
        this.threadId = options.threadId || '';
        this.subject = options.subject || 'No Subject';
        this.sender = options.sender || 'Unknown Sender';
        this.recipient = options.recipient || 'Unknown Recipient';
        this.date = options.date || new Date();
        this.snippet = options.snippet || '';
        this.body = options.body || '';
        this.labels = options.labels || [];
        this.attachments = options.attachments || [];
        this.priority = options.priority || MessagePriority.LOW;
        this.category = options.category || MessageCategory.PERSONAL;
        this.processed = options.processed || false;
        this.actionTaken = options.actionTaken || null;
        this.createdAt = options.createdAt || new Date();
    }

    generateId() {
        return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    }
}

class GmailWatcherJS {
    /**
     * Creates a new GmailWatcherJS instance
     * @param {string} credentialsPath - Path to credentials.json file
     * @param {string} tokenPath - Path to token file
     * @param {string} dbPath - Path to the SQLite database file
     */
    constructor(credentialsPath = 'credentials.json', tokenPath = 'token.json', dbPath = './gmail_watcher.db') {
        this.credentialsPath = credentialsPath;
        this.tokenPath = tokenPath;
        this.dbPath = dbPath;
        this.service = null;
        this.running = false;
        this.oauth2Client = null;

        // Initialize database
        this.setupDatabase();

        // Configure logging
        this.logger = console;

        // Define trigger patterns
        this.triggerKeywords = {
            [MessageCategory.URGENT]: [
                'urgent', 'asap', 'immediately', 'critical', 'emergency',
                'attention required', 'action required', 'high priority'
            ],
            [MessageCategory.MEETING]: [
                'calendar invitation', 'meeting request', 'schedule',
                'appointment', 'conference', 'call scheduled'
            ],
            [MessageCategory.FINANCIAL]: [
                'invoice', 'payment', 'billing', 'charge', 'receipt',
                'purchase', 'transaction', 'banking', 'account'
            ],
            [MessageCategory.SECURITY]: [
                'login', 'security', 'suspicious', 'unauthorized',
                'compromised', 'password', 'authentication'
            ],
            [MessageCategory.BUSINESS]: [
                'proposal', 'contract', 'agreement', 'partnership',
                'collaboration', 'deal', 'negotiation'
            ],
            [MessageCategory.CUSTOMER]: [
                'customer', 'client', 'support', 'feedback',
                'complaint', 'review', 'satisfaction'
            ]
        };

        // Define sender patterns
        this.senderPatterns = {
            vipContacts: [],  // Will be populated based on user config
            corporateDomains: ['.com', '.org', '.gov', '.edu'],  // Common corporate domains
            blacklistedSenders: []  // Will be populated based on user config
        };
    }

    /**
     * Sets up the database schema for message tracking
     */
    setupDatabase() {
        this.db = new sqlite3.Database(this.dbPath);

        // Create messages table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS watched_messages (
                id TEXT PRIMARY KEY,
                thread_id TEXT,
                subject TEXT,
                sender TEXT,
                recipient TEXT,
                date DATETIME,
                snippet TEXT,
                body TEXT,
                labels_json TEXT,
                attachments_json TEXT,
                priority INTEGER,
                category TEXT,
                processed BOOLEAN DEFAULT FALSE,
                action_taken TEXT,
                created_at DATETIME,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        `);

        // Create processing_rules table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS processing_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                condition_json TEXT,
                action_json TEXT,
                priority INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        `);

        // Create message_history table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS message_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT,
                action_taken TEXT,
                result TEXT,
                executed_at DATETIME,
                FOREIGN KEY (message_id) REFERENCES watched_messages (id)
            )
        `);
    }

    /**
     * Authenticates with Gmail API using OAuth 2.0
     * @returns {Promise<void>}
     */
    async authenticate() {
        try {
            // Load client secrets
            const content = await fs.readFile(this.credentialsPath);
            const credentials = JSON.parse(content);

            const { client_secret, client_id, redirect_uris } = credentials.installed;

            // Create OAuth2 client
            this.oauth2Client = new google.auth.OAuth2(
                client_id, client_secret, redirect_uris[0]
            );

            // Check if token exists
            let token;
            try {
                token = await fs.readFile(this.tokenPath, 'utf8');
            } catch (err) {
                // Token doesn't exist, need to authorize
                token = await this.getNewToken();
            }

            this.oauth2Client.setCredentials(JSON.parse(token));
            this.service = google.gmail({ version: 'v1', auth: this.oauth2Client });

            this.logger.info("Successfully authenticated with Gmail API");
        } catch (error) {
            this.logger.error(`Authentication error: ${error.message}`);
            throw error;
        }
    }

    /**
     * Gets a new token after prompting for authorization
     * @returns {Promise<string>} The new token
     */
    async getNewToken() {
        const authUrl = this.oauth2Client.generateAuthUrl({
            access_type: 'offline',
            scope: [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.modify'
            ],
        });

        console.log('Authorize this app by visiting this url:', authUrl);

        // In a real implementation, you'd handle the callback from the redirect
        // This is simplified for the example
        const readline = require('readline');
        const rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });

        return new Promise((resolve) => {
            rl.question('Enter the code from that page here: ', async (code) => {
                rl.close();

                const { tokens } = await this.oauth2Client.getToken(code);
                this.oauth2Client.setCredentials(tokens);

                // Save the token to disk for later program executions
                await fs.writeFile(this.tokenPath, JSON.stringify(tokens));
                console.log('Token stored to', this.tokenPath);

                resolve(JSON.stringify(tokens));
            });
        });
    }

    /**
     * Gets recent unread messages from Gmail
     * @param {number} maxResults - Maximum number of results to return
     * @param {number} daysBack - Number of days back to search
     * @returns {Promise<Array>} Array of message objects
     */
    async getRecentMessages(maxResults = 10, daysBack = 1) {
        if (!this.service) {
            await this.authenticate();
        }

        try {
            // Calculate date threshold
            const sinceDate = new Date();
            sinceDate.setDate(sinceDate.getDate() - daysBack);
            const dateString = sinceDate.toISOString().split('T')[0]; // Format as YYYY-MM-DD

            // Query for unread messages
            const query = `is:unread after:${dateString}`;

            const res = await this.service.users.messages.list({
                userId: 'me',
                q: query,
                maxResults: maxResults
            });

            const messages = res.data.messages || [];
            const detailedMessages = [];

            for (const msg of messages) {
                try {
                    // Get full message details
                    const fullMsg = await this.service.users.messages.get({
                        userId: 'me',
                        id: msg.id,
                        format: 'full'
                    });

                    detailedMessages.push(fullMsg.data);
                } catch (error) {
                    this.logger.error(`Failed to retrieve message ${msg.id}: ${error.message}`);
                    continue;
                }
            }

            this.logger.info(`Retrieved ${detailedMessages.length} recent messages`);
            return detailedMessages;

        } catch (error) {
            this.logger.error(`Gmail API error: ${error.message}`);
            return [];
        }
    }

    /**
     * Extracts relevant details from a Gmail message
     * @param {Object} msg - The message object from Gmail API
     * @returns {Promise<WatchedMessage|null>} The extracted message or null if error
     */
    async extractMessageDetails(msg) {
        try {
            const headers = {};
            if (msg.payload && msg.payload.headers) {
                for (const header of msg.payload.headers) {
                    headers[header.name.toLowerCase()] = header.value;
                }
            }

            // Extract basic information
            const msgId = msg.id;
            const threadId = msg.threadId;
            const subject = headers['subject'] || 'No Subject';
            const sender = headers['from'] || 'Unknown Sender';
            const recipient = headers['to'] || 'Unknown Recipient';
            const dateStr = headers['date'] || '';

            let dateObj = new Date(); // default to now
            if (dateStr) {
                try {
                    // Parse date - Gmail date format: "Mon, 2 Sep 2024 10:30:00 +0000"
                    dateObj = new Date(dateStr);
                    if (isNaN(dateObj.getTime())) {
                        // Fallback if date parsing fails
                        dateObj = new Date();
                    }
                } catch (e) {
                    dateObj = new Date();
                }
            }

            const snippet = msg.snippet || '';

            // Extract body content
            const body = await this.extractBodyContent(msg);

            // Extract labels
            const labels = msg.labelIds || [];

            // Extract attachments
            const attachments = await this.extractAttachment(msg);

            // Categorize and prioritize the message
            const category = this.categorizeMessage(subject, body, sender);
            const priority = this.determinePriority(category, subject, body, sender);

            return new WatchedMessage({
                id: msgId,
                threadId: threadId,
                subject: subject,
                sender: sender,
                recipient: recipient,
                date: dateObj,
                snippet: snippet,
                body: body,
                labels: labels,
                attachments: attachments,
                priority: priority,
                category: category
            });

        } catch (error) {
            this.logger.error(`Error extracting message details: ${error.message}`);
            return null;
        }
    }

    /**
     * Extracts body content from message payload
     * @param {Object} msg - The message object
     * @returns {Promise<string>} The extracted body content
     */
    async extractBodyContent(msg) {
        let body = "";

        // Handle different message payload structures
        const payload = msg.payload || {};

        // If it's a multipart message
        if (payload.parts && Array.isArray(payload.parts)) {
            for (const part of payload.parts) {
                if (part.mimeType === 'text/plain' && part.body && part.body.data) {
                    // Decode base64 content
                    const bodyData = part.body.data;
                    body = Buffer.from(bodyData, 'base64').toString('utf-8');
                    break;
                } else if (part.mimeType === 'text/html' && part.body && part.body.data) {
                    // Fallback to HTML if plain text not available
                    const bodyData = part.body.data;
                    const htmlContent = Buffer.from(bodyData, 'base64').toString('utf-8');

                    // Remove HTML tags to get plain text
                    body = htmlContent.replace(/<[^>]*>/g, '');
                }
            }
        } else if (payload.body && payload.body.data) {
            // Simple message
            const bodyData = payload.body.data;
            body = Buffer.from(bodyData, 'base64').toString('utf-8');
        }

        return body;
    }

    /**
     * Extracts attachment information from message
     * @param {Object} msg - The message object
     * @returns {Promise<Array>} Array of attachment objects
     */
    async extractAttachment(msg) {
        const attachments = [];
        const payload = msg.payload || {};

        if (payload.parts && Array.isArray(payload.parts)) {
            for (const part of payload.parts) {
                if (part.filename) { // This indicates an attachment
                    const attachment = {
                        filename: part.filename,
                        mimeType: part.mimeType || 'application/octet-stream',
                        size: part.body ? part.body.size : 0,
                        attachmentId: part.body ? part.body.attachmentId : null
                    };
                    attachments.push(attachment);
                }
            }
        }

        return attachments;
    }

    /**
     * Categorizes a message based on its content
     * @param {string} subject - The subject of the message
     * @param {string} body - The body of the message
     * @param {string} sender - The sender of the message
     * @returns {string} The category
     */
    categorizeMessage(subject, body, sender) {
        const content = `${subject} ${body}`.toLowerCase();

        // Check for each category based on keywords
        for (const [category, keywords] of Object.entries(this.triggerKeywords)) {
            for (const keyword of keywords) {
                if (content.includes(keyword.toLowerCase())) {
                    return category;
                }
            }
        }

        // Check for VIP senders
        if (this.senderPatterns.vipContacts.some(vip => sender.toLowerCase().includes(vip))) {
            return MessageCategory.BUSINESS; // Or another high-priority category
        }

        // Check for corporate domains
        const senderDomain = sender.includes('@') ? sender.split('@')[1].toLowerCase() : '';
        if (this.senderPatterns.corporateDomains.some(domain => senderDomain.includes(domain))) {
            return MessageCategory.BUSINESS;
        }

        // Default categories based on common patterns
        if (content.includes('newsletter') || content.includes('unsubscribe')) {
            return MessageCategory.NEWSLETTER;
        }

        if (['facebook', 'twitter', 'linkedin', 'instagram'].some(social => content.includes(social))) {
            return MessageCategory.SOCIAL;
        }

        if (['update', 'alert', 'notification'].some(notification => content.includes(notification))) {
            return MessageCategory.NOTIFICATION;
        }

        // Default to personal if no other category matches
        return MessageCategory.PERSONAL;
    }

    /**
     * Determines priority level for a message
     * @param {string} category - The category of the message
     * @param {string} subject - The subject of the message
     * @param {string} body - The body of the message
     * @param {string} sender - The sender of the message
     * @returns {number} The priority level
     */
    determinePriority(category, subject, body, sender) {
        // Start with category-based priority
        const categoryPriority = {
            [MessageCategory.URGENT]: MessagePriority.CRITICAL,
            [MessageCategory.SECURITY]: MessagePriority.HIGH,
            [MessageCategory.FINANCIAL]: MessagePriority.HIGH,
            [MessageCategory.MEETING]: MessagePriority.MEDIUM,
            [MessageCategory.BUSINESS]: MessagePriority.MEDIUM,
            [MessageCategory.CUSTOMER]: MessagePriority.MEDIUM,
            [MessageCategory.PERSONAL]: MessagePriority.LOW,
            [MessageCategory.NEWSLETTER]: MessagePriority.TRIVIAL,
            [MessageCategory.SOCIAL]: MessagePriority.TRIVIAL,
            [MessageCategory.NOTIFICATION]: MessagePriority.LOW,
            [MessageCategory.SPAM]: MessagePriority.TRIVIAL
        };

        let priority = categoryPriority[category] || MessagePriority.LOW;

        // Boost priority based on specific content
        const content = `${subject} ${body}`.toLowerCase();

        // Critical keywords boost to highest priority
        if (['breach', 'security incident', 'compromise', 'attack', 'malware'].some(word => content.includes(word))) {
            return MessagePriority.CRITICAL;
        }

        if (['payment failure', 'account suspended', 'service interruption'].some(word => content.includes(word))) {
            priority = Math.max(priority, MessagePriority.HIGH);
        }

        // VIP sender gets priority boost
        if (this.senderPatterns.vipContacts.some(vip => sender.toLowerCase().includes(vip))) {
            priority = Math.max(priority, MessagePriority.HIGH);
        }

        return priority;
    }

    /**
     * Processes a message according to rules and returns action taken
     * @param {WatchedMessage} message - The message to process
     * @returns {Promise<string>} The action taken
     */
    async processMessage(message) {
        // Check if already processed
        if (await this.isMessageProcessed(message.id)) {
            return "already_processed";
        }

        // Apply processing rules
        const actionTaken = await this.applyProcessingRules(message);

        // Mark as processed
        await this.markMessageProcessed(message.id, actionTaken);

        this.logger.info(`Processed message '${message.subject}' with action: ${actionTaken}`);
        return actionTaken;
    }

    /**
     * Applies configured processing rules to a message
     * @param {WatchedMessage} message - The message to process
     * @returns {Promise<string>} The action taken
     */
    async applyProcessingRules(message) {
        // Default actions based on priority and category
        if (message.priority === MessagePriority.CRITICAL) {
            return await this.handleCriticalMessage(message);
        } else if (message.category === MessageCategory.SECURITY) {
            return await this.handleSecurityMessage(message);
        } else if (message.category === MessageCategory.FINANCIAL) {
            return await this.handleFinancialMessage(message);
        } else if (message.category === MessageCategory.MEETING) {
            return await this.handleMeetingMessage(message);
        } else {
            return await this.handleStandardMessage(message);
        }
    }

    /**
     * Handles critical priority messages
     * @param {WatchedMessage} message - The message to handle
     * @returns {Promise<string>} The action taken
     */
    async handleCriticalMessage(message) {
        // For critical messages, always flag and notify
        await this.addLabelToMessage(message.id, 'IMPORTANT');
        this.logger.warning(`Critical message detected: ${message.subject}`);
        return "flagged_and_notified";
    }

    /**
     * Handles security-related messages
     * @param {WatchedMessage} message - The message to handle
     * @returns {Promise<string>} The action taken
     */
    async handleSecurityMessage(message) {
        // Flag for security review
        await this.addLabelToMessage(message.id, 'IMPORTANT');
        this.logger.warning(`Security-related message: ${message.subject}`);
        return "security_review";
    }

    /**
     * Handles financial messages
     * @param {WatchedMessage} message - The message to handle
     * @returns {Promise<string>} The action taken
     */
    async handleFinancialMessage(message) {
        // Flag for financial review
        await this.addLabelToMessage(message.id, 'FINANCE');
        this.logger.info(`Financial message: ${message.subject}`);
        return "finance_review";
    }

    /**
     * Handles meeting invitations
     * @param {WatchedMessage} message - The message to handle
     * @returns {Promise<string>} The action taken
     */
    async handleMeetingMessage(message) {
        // Add to calendar processing queue
        await this.addLabelToMessage(message.id, 'MEETING');
        this.logger.info(`Meeting invitation: ${message.subject}`);
        return "calendar_invite";
    }

    /**
     * Handles standard messages
     * @param {WatchedMessage} message - The message to handle
     * @returns {Promise<string>} The action taken
     */
    async handleStandardMessage(message) {
        // Apply standard processing based on category
        if (message.category === MessageCategory.NEWSLETTER) {
            // Auto-archive newsletters
            await this.addLabelToMessage(message.id, 'CATEGORY_UPDATES');
            return "archived";
        } else if (message.category === MessageCategory.SOCIAL) {
            // Mark social notifications appropriately
            await this.addLabelToMessage(message.id, 'CATEGORY_SOCIAL');
            return "labeled_social";
        } else {
            // Standard processing - just mark as read
            return "marked_read";
        }
    }

    /**
     * Adds a label to a message
     * @param {string} msgId - The message ID
     * @param {string} labelName - The label name
     * @returns {Promise<boolean>} Whether the operation succeeded
     */
    async addLabelToMessage(msgId, labelName) {
        if (!this.service) {
            await this.authenticate();
        }

        try {
            // First, get the label ID
            const labelsRes = await this.service.users.labels.list({
                userId: 'me'
            });

            let labelId = null;
            const labels = labelsRes.data.labels || [];

            for (const label of labels) {
                if (label.name === labelName) {
                    labelId = label.id;
                    break;
                }
            }

            // If label doesn't exist, create it
            if (!labelId) {
                const labelRes = await this.service.users.labels.create({
                    userId: 'me',
                    requestBody: {
                        name: labelName,
                        messageListVisibility: 'show',
                        labelListVisibility: 'labelShow'
                    }
                });
                labelId = labelRes.data.id;
            }

            // Add the label to the message
            await this.service.users.messages.modify({
                userId: 'me',
                id: msgId,
                requestBody: {
                    addLabelIds: [labelId]
                }
            });

            return true;

        } catch (error) {
            this.logger.error(`Failed to add label to message ${msgId}: ${error.message}`);
            return false;
        }
    }

    /**
     * Checks if a message has already been processed
     * @param {string} msgId - The message ID
     * @returns {Promise<boolean>} Whether the message has been processed
     */
    async isMessageProcessed(msgId) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare('SELECT COUNT(*) as count FROM watched_messages WHERE id = ? AND processed = 1');
            stmt.get([msgId], (err, row) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(row.count > 0);
                }
            });
            stmt.finalize();
        });
    }

    /**
     * Marks a message as processed in the database
     * @param {string} msgId - The message ID
     * @param {string} actionTaken - The action taken
     * @returns {Promise<boolean>} Whether the operation succeeded
     */
    async markMessageProcessed(msgId, actionTaken) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                UPDATE watched_messages
                SET processed = 1, action_taken = ?, updated_at = ?
                WHERE id = ?
            `);

            stmt.run([actionTaken, new Date().toISOString(), msgId], function(err) {
                if (err) {
                    reject(err);
                    return;
                }

                // Also log to message history
                const historyStmt = this.db.prepare(`
                    INSERT INTO message_history (message_id, action_taken, result, executed_at)
                    VALUES (?, ?, ?, ?)
                `);

                historyStmt.run([msgId, actionTaken, 'success', new Date().toISOString()], function(err) {
                    if (err) {
                        console.error('Error logging message history:', err);
                    }
                    historyStmt.finalize();
                });

                resolve(true);
            });

            stmt.finalize();
        });
    }

    /**
     * Saves a watched message to the database
     * @param {WatchedMessage} message - The message to save
     * @returns {Promise<boolean>} Whether the operation succeeded
     */
    async saveWatchedMessage(message) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT OR REPLACE INTO watched_messages
                (id, thread_id, subject, sender, recipient, date, snippet, body,
                 labels_json, attachments_json, priority, category, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `);

            stmt.run([
                message.id, message.threadId, message.subject, message.sender,
                message.recipient, message.date.toISOString(), message.snippet,
                message.body, JSON.stringify(message.labels), JSON.stringify(message.attachments),
                message.priority, message.category,
                message.createdAt.toISOString()
            ], function(err) {
                if (err) {
                    reject(err);
                } else {
                    resolve(true);
                }
            });

            stmt.finalize();
        });
    }

    /**
     * Starts monitoring Gmail for new messages
     * @param {number} pollInterval - Interval between polls in seconds
     * @param {number} maxMessages - Maximum messages to process per poll
     */
    async startMonitoring(pollInterval = 60, maxMessages = 10) {
        this.running = true;
        this.logger.info(`Starting Gmail monitoring (polling every ${pollInterval}s)`);

        const process = async () => {
            if (!this.running) return;

            try {
                // Get recent messages
                const messages = await this.getRecentMessages(maxResults = maxMessages);

                for (const msgData of messages) {
                    // Extract message details
                    const message = await this.extractMessageDetails(msgData);

                    if (message) {
                        // Save to database
                        await this.saveWatchedMessage(message);

                        // Process the message
                        const action = await this.processMessage(message);

                        this.logger.debug(`Action taken for '${message.subject}': ${action}`);
                    }
                }

                // Schedule next poll
                setTimeout(process, pollInterval * 1000);

            } catch (error) {
                this.logger.error(`Error during monitoring: ${error.message}`);
                // Retry after a shorter interval on error
                setTimeout(process, Math.min(pollInterval * 1000, 30000)); // Max 30 sec delay
            }
        };

        // Start the monitoring process
        await process();
    }

    /**
     * Stops monitoring Gmail
     */
    stopMonitoring() {
        this.running = false;
        this.logger.info("Gmail monitoring stopped");
    }

    /**
     * Gets all unprocessed messages from the database
     * @returns {Promise<WatchedMessage[]>} Array of unprocessed messages
     */
    async getUnprocessedMessages() {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                SELECT id, thread_id, subject, sender, recipient, date, snippet, body,
                       labels_json, attachments_json, priority, category, processed, action_taken, created_at
                FROM watched_messages
                WHERE processed = 0
                ORDER BY date DESC
            `);

            stmt.all([], (err, rows) => {
                if (err) {
                    reject(err);
                    return;
                }

                const messages = [];
                for (const row of rows) {
                    try {
                        const message = new WatchedMessage({
                            id: row.id,
                            threadId: row.thread_id,
                            subject: row.subject,
                            sender: row.sender,
                            recipient: row.recipient,
                            date: new Date(row.date),
                            snippet: row.snippet,
                            body: row.body,
                            labels: JSON.parse(row.labels_json || '[]'),
                            attachments: JSON.parse(row.attachments_json || '[]'),
                            priority: row.priority,
                            category: row.category,
                            processed: Boolean(row.processed),
                            actionTaken: row.action_taken,
                            createdAt: row.created_at ? new Date(row.created_at) : new Date()
                        });
                        messages.push(message);
                    } catch (e) {
                        this.logger.error(`Error parsing message from DB: ${e.message}`);
                        continue;
                    }
                }

                resolve(messages);
            });

            stmt.finalize();
        });
    }

    /**
     * Gets statistics about processed messages
     * @returns {Promise<Object>} Statistics object
     */
    async getMessageStatistics() {
        return new Promise((resolve, reject) => {
            // Total messages
            const totalStmt = this.db.prepare('SELECT COUNT(*) as count FROM watched_messages');
            totalStmt.get([], (err, totalRow) => {
                if (err) {
                    reject(err);
                    return;
                }

                // Processed messages
                const processedStmt = this.db.prepare('SELECT COUNT(*) as count FROM watched_messages WHERE processed = 1');
                processedStmt.get([], (err, processedRow) => {
                    if (err) {
                        reject(err);
                        return;
                    }

                    // Messages by category
                    const categoryStmt = this.db.prepare(`
                        SELECT category, COUNT(*) as count
                        FROM watched_messages
                        GROUP BY category
                    `);
                    categoryStmt.all([], (err, categoryRows) => {
                        if (err) {
                            reject(err);
                            return;
                        }

                        const categoryCounts = {};
                        for (const row of categoryRows) {
                            categoryCounts[row.category] = row.count;
                        }

                        // Messages by priority
                        const priorityStmt = this.db.prepare(`
                            SELECT priority, COUNT(*) as count
                            FROM watched_messages
                            GROUP BY priority
                        `);
                        priorityStmt.all([], (err, priorityRows) => {
                            if (err) {
                                reject(err);
                                return;
                            }

                            const priorityCounts = {};
                            for (const row of priorityRows) {
                                priorityCounts[row.priority] = row.count;
                            }

                            resolve({
                                totalMessages: totalRow.count,
                                processedMessages: processedRow.count,
                                unprocessedMessages: totalRow.count - processedRow.count,
                                categoryBreakdown: categoryCounts,
                                priorityBreakdown: priorityCounts
                            });

                            priorityStmt.finalize();
                        });

                        categoryStmt.finalize();
                    });

                    processedStmt.finalize();
                });

                totalStmt.finalize();
            });
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

module.exports = GmailWatcherJS;

// If running as a standalone script
if (require.main === module) {
    const args = process.argv.slice(2);

    async function main() {
        const credentialsPath = args.find(arg => arg.startsWith('--credentials='))?.split('=')[1] || 'credentials.json';
        const tokenPath = args.find(arg => arg.startsWith('--token='))?.split('=')[1] || 'token.json';
        const dbPath = args.find(arg => arg.startsWith('--db-path='))?.split('=')[1] || './gmail_watcher.db';
        const pollInterval = parseInt(args.find(arg => arg.startsWith('--poll-interval='))?.split('=')[1] || '60', 10);
        const maxMessages = parseInt(args.find(arg => arg.startsWith('--max-messages='))?.split('=')[1] || '10', 10);
        const demoMode = args.includes('--demo');

        if (demoMode) {
            // Demo mode - just show the structure without connecting to Gmail
            console.log("Gmail Watcher Demo Mode");
            console.log("=" * 30);
            console.log(`Credentials file: ${credentialsPath}`);
            console.log(`Token file: ${tokenPath}`);
            console.log(`Database: ${dbPath}`);
            console.log(`Poll interval: ${pollInterval}s`);
            console.log(`Max messages: ${maxMessages}`);
            console.log("\\nThis would monitor your Gmail account for important messages");
            console.log("and apply processing rules based on content and sender.");

            // Create a sample message for demonstration
            const watcher = new GmailWatcherJS(credentialsPath, tokenPath, dbPath);

            console.log("\\nSample message processing:");
            console.log("- Categorizing messages based on content");
            console.log("- Applying priority levels (Critical, High, Medium, Low, Trivial)");
            console.log("- Taking actions based on message category");
            console.log("- Tracking processed messages in database");

        } else {
            // Initialize and start the watcher
            const watcher = new GmailWatcherJS(credentialsPath, tokenPath, dbPath);

            try {
                await watcher.startMonitoring(pollInterval, maxMessages);

                // Handle shutdown gracefully
                process.on('SIGINT', () => {
                    console.log('\\nStopping Gmail watcher...');
                    watcher.stopMonitoring();
                    watcher.close();
                    process.exit(0);
                });

                process.on('SIGTERM', () => {
                    console.log('\\nStopping Gmail watcher...');
                    watcher.stopMonitoring();
                    watcher.close();
                    process.exit(0);
                });

            } catch (error) {
                console.error(`Error starting Gmail watcher: ${error.message}`);
                process.exit(1);
            }
        }
    }

    main().catch(console.error);
}