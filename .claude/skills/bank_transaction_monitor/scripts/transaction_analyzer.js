/**
 * BankTransactionMonitorJS: JavaScript module for monitoring bank transactions and detecting anomalies.
 *
 * This module provides functionality to parse bank statements, categorize transactions,
 * and flag potential fraud or unusual spending patterns.
 */

const fs = require('fs').promises;
const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const csv = require('csv-parser'); // Assuming csv-parser is available
const { createReadStream } = require('fs');

class BankTransactionMonitorJS {
    /**
     * Creates a new BankTransactionMonitorJS instance
     * @param {string} dbPath - Path to the SQLite database file
     */
    constructor(dbPath = './bank_transactions.db') {
        this.dbPath = dbPath;
        this.db = null;
        this.avgSpending = {};
        this.merchantPatterns = {};
        this.locationHistory = [];
        this.setupDatabase();
    }

    /**
     * Sets up the database schema for transaction tracking
     */
    setupDatabase() {
        this.db = new sqlite3.Database(this.dbPath);

        // Create transactions table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                date DATETIME,
                amount REAL,
                description TEXT,
                merchant TEXT,
                category TEXT,
                account TEXT,
                transaction_type TEXT,
                status TEXT,
                location TEXT,
                currency TEXT,
                notes TEXT,
                user_category TEXT,
                is_business BOOLEAN,
                requires_review BOOLEAN,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        `);

        // Create alerts table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT,
                alert_level TEXT,
                rule_triggered TEXT,
                message TEXT,
                timestamp DATETIME,
                requires_action BOOLEAN,
                resolved BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (transaction_id) REFERENCES transactions (id)
            )
        `);

        // Create categories table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                parent_category TEXT,
                is_business BOOLEAN DEFAULT FALSE
            )
        `);

        // Create merchant mappings table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS merchant_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_name TEXT,
                normalized_name TEXT,
                category TEXT,
                is_business BOOLEAN,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        `);
    }

    /**
     * Parses a bank statement file and returns an array of transactions
     * @param {string} statementPath - Path to the bank statement file
     * @returns {Promise<Array>} Array of transaction objects
     */
    async parseBankStatement(statementPath) {
        if (statementPath.endsWith('.csv')) {
            return await this.parseCsvStatement(statementPath);
        } else if (statementPath.endsWith('.ofx')) {
            return await this.parseOfxStatement(statementPath);
        } else {
            throw new Error(`Unsupported statement format: ${statementPath}`);
        }
    }

    /**
     * Parses a CSV bank statement file
     * @param {string} csvPath - Path to the CSV file
     * @returns {Promise<Array>} Array of transaction objects
     */
    async parseCsvStatement(csvPath) {
        return new Promise((resolve, reject) => {
            const transactions = [];
            const results = [];

            // First, read the file to get the raw content to process
            createReadStream(csvPath)
                .pipe(csv())
                .on('data', (row) => results.push(row))
                .on('end', () => {
                    results.forEach((row) => {
                        try {
                            // Parse date (try common formats)
                            const dateStr = row['Date'] || row['date'] || row['Transaction Date'];
                            const parsedDate = this.parseDate(dateStr);

                            // Parse amount (handle different formats)
                            let amountStr = (row['Amount'] || row['amount'] || row['Debit/Credit'] || '').toString();
                            amountStr = amountStr.replace(/[^\d.-]/g, ''); // Remove non-numeric characters except minus and dot
                            const amount = Math.abs(parseFloat(amountStr) || 0);

                            // Determine transaction type
                            let transType = 'debit';
                            if (amountStr.startsWith('-') || (row['Type'] && row['Type'].toLowerCase().includes('credit'))) {
                                transType = 'credit';
                            }

                            // Extract merchant name from description
                            const description = row['Description'] || row['description'] || row['Memo'] || '';
                            const merchant = this.extractMerchant(description);

                            const transaction = {
                                id: this.generateId(),
                                date: parsedDate,
                                amount: amount,
                                description: description,
                                merchant: merchant,
                                category: '', // Will categorize later
                                account: row['Account'] || row['account'] || 'primary',
                                transactionType: transType,
                                status: 'cleared',
                                location: null,
                                currency: 'USD',
                                notes: null,
                                userCategory: null,
                                isBusiness: false,
                                requiresReview: false
                            };

                            transactions.push(transaction);
                        } catch (error) {
                            console.warn(`Error parsing row: ${error.message}`, row);
                            // Continue processing other rows
                        }
                    });

                    resolve(transactions);
                })
                .on('error', reject);
        });
    }

    /**
     * Parses an OFX bank statement file
     * @param {string} ofxPath - Path to the OFX file
     * @returns {Promise<Array>} Array of transaction objects
     */
    async parseOfxStatement(ofxPath) {
        try {
            const content = await fs.readFile(ofxPath, 'utf8');
            const transactions = [];

            // Simplified OFX parsing (real implementation would be more robust)
            const matches = content.match(/<STMTTRN>[\s\S]*?<\/STMTTRN>/g) || [];

            for (const match of matches) {
                // Extract fields from OFX block
                const dateMatch = match.match(/<DTPOSTED>(\d{8})/);
                const amountMatch = match.match(/<TRNAMT>([-\d.]+)/);
                const nameMatch = match.match(/<NAME>([^<]+)/);

                if (dateMatch && amountMatch && nameMatch) {
                    const dateStr = dateMatch[1];
                    const parsedDate = new Date(
                        dateStr.substring(0, 4),  // year
                        parseInt(dateStr.substring(4, 6)) - 1,  // month (0-indexed)
                        dateStr.substring(6, 8)   // day
                    );

                    const amount = Math.abs(parseFloat(amountMatch[1]));
                    const merchant = nameMatch[1].trim();

                    const transaction = {
                        id: this.generateId(),
                        date: parsedDate,
                        amount: amount,
                        description: merchant,
                        merchant: merchant,
                        category: '',
                        account: 'primary',
                        transactionType: parseFloat(amountMatch[1]) >= 0 ? 'debit' : 'credit',
                        status: 'cleared',
                        location: null,
                        currency: 'USD',
                        notes: null,
                        userCategory: null,
                        isBusiness: false,
                        requiresReview: false
                    };

                    transactions.push(transaction);
                }
            }

            return transactions;
        } catch (error) {
            console.error('Error parsing OFX file:', error);
            throw error;
        }
    }

    /**
     * Parses a date string in various common formats
     * @param {string} dateStr - Date string to parse
     * @returns {Date} Parsed date object
     */
    parseDate(dateStr) {
        if (!dateStr) return new Date();

        // Try various common date formats
        const formats = [
            /\d{4}-\d{2}-\d{2}/,           // YYYY-MM-DD
            /\d{1,2}\/\d{1,2}\/\d{4}/,    // MM/DD/YYYY
            /\d{1,2}\/\d{1,2}\/\d{2}/,    // MM/DD/YY
            /\d{4}\d{2}\d{2}/              // YYYYMMDD
        ];

        for (const format of formats) {
            const match = dateStr.match(format);
            if (match) {
                const matchedStr = match[0];

                if (matchedStr.includes('-')) {
                    return new Date(matchedStr);
                } else if (matchedStr.includes('/')) {
                    return new Date(matchedStr);
                } else if (matchedStr.length === 8) {
                    // YYYYMMDD format
                    return new Date(
                        matchedStr.substring(0, 4),  // year
                        parseInt(matchedStr.substring(4, 6)) - 1,  // month (0-indexed)
                        matchedStr.substring(6, 8)   // day
                    );
                }
            }
        }

        // If no format matches, try the original string
        return new Date(dateStr);
    }

    /**
     * Extracts merchant name from transaction description
     * @param {string} description - Transaction description
     * @returns {string} Extracted merchant name
     */
    extractMerchant(description) {
        const descUpper = description.toUpperCase();

        // Common patterns in transaction descriptions
        const patterns = [
            /STARBUCKS.*/,
            /AMAZON.*/,
            /WALMART.*/,
            /WHOLEFDS.*/,
            /COSTCO.*/,
            /^([^,*]+)/,  // Take everything before first comma or asterisk
        ];

        for (const pattern of patterns) {
            const match = descUpper.match(pattern);
            if (match) {
                return match[0].trim();
            }
        }

        // If no pattern matches, return original description
        return description.trim();
    }

    /**
     * Generates a unique transaction ID
     * @returns {string} Unique ID
     */
    generateId() {
        return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    }

    /**
     * Adds transactions to the database
     * @param {Array} transactions - Array of transaction objects
     */
    async addTransactions(transactions) {
        return new Promise((resolve, reject) => {
            this.db.serialize(() => {
                const stmt = this.db.prepare(`
                    INSERT OR REPLACE INTO transactions
                    (id, date, amount, description, merchant, category, account,
                     transaction_type, status, location, currency, notes,
                     user_category, is_business, requires_review)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                `);

                for (const transaction of transactions) {
                    // Categorize the transaction if not already categorized
                    if (!transaction.category) {
                        transaction.category = this.categorizeTransaction(transaction);
                    }

                    // Determine if business based on category
                    if (transaction.category && transaction.category.toLowerCase().includes('business')) {
                        transaction.isBusiness = true;
                    }

                    stmt.run([
                        transaction.id,
                        transaction.date.toISOString(),
                        transaction.amount,
                        transaction.description,
                        transaction.merchant,
                        transaction.category,
                        transaction.account,
                        transaction.transactionType,
                        transaction.status,
                        transaction.location || null,
                        transaction.currency,
                        transaction.notes || null,
                        transaction.userCategory || null,
                        transaction.isBusiness,
                        transaction.requiresReview
                    ]);
                }

                stmt.finalize();
                resolve();
            });
        });
    }

    /**
     * Categorizes a transaction based on merchant and description
     * @param {Object} transaction - Transaction object to categorize
     * @returns {string} Category for the transaction
     */
    categorizeTransaction(transaction) {
        const descriptionLower = transaction.description.toLowerCase();
        const merchantLower = transaction.merchant.toLowerCase();

        // Define category mapping patterns
        const categoryMapping = {
            'groceries': ['grocery', 'market', 'food', 'whole', 'kroger', 'safeway', 'walmart'],
            'dining_out': ['restaurant', 'cafe', 'bar', 'pub', 'starbucks', 'mcdonalds', 'chipotle'],
            'transportation': ['gas', 'fuel', 'shell', 'chevron', 'uber', 'lyft', 'taxi'],
            'healthcare': ['hospital', 'clinic', 'drug', 'pharmacy', 'walgreens', 'cvs'],
            'entertainment': ['movie', 'cinema', 'netflix', 'spotify', 'itunes', 'ticketmaster'],
            'travel': ['airline', 'hotel', 'airbnb', 'expedia', 'uber'],
            'insurance': ['insurance', 'geico', 'progressive', 'aetna'],
            'utilities': ['electric', 'gas', 'water', 'comcast', 'verizon', 'att'],
            'rent/mortgage': ['rent', 'mortgage', 'property'],
            'education': ['school', 'university', 'college', 'textbook'],
            'charitable_giving': ['charity', 'donation', 'nonprofit'],
            'business_expenses': ['business', 'office', 'consulting', 'software', 'web', 'digital']
        };

        // Check merchant and description for category matches
        for (const [category, keywords] of Object.entries(categoryMapping)) {
            for (const keyword of keywords) {
                if (merchantLower.includes(keyword) || descriptionLower.includes(keyword)) {
                    return category;
                }
            }
        }

        // Default to shopping if nothing else matches
        return 'shopping';
    }

    /**
     * Detects anomalies in transaction patterns
     * @returns {Promise<Array>} Array of anomalies with transaction and alert info
     */
    async detectAnomalies() {
        const anomalies = [];

        // Get recent transactions for analysis
        const recentTransactions = await this.getRecentTransactions(30);

        // Calculate spending averages
        this.calculateSpendingAverages(recentTransactions);

        for (const transaction of recentTransactions) {
            const transactionAnomalies = await this.analyzeTransaction(transaction, recentTransactions);
            for (const anomaly of transactionAnomalies) {
                anomalies.push({ transaction, alert: anomaly });
            }
        }

        // Store detected anomalies in database
        await this.storeAlerts(anomalies.map(item => item.alert));

        return anomalies;
    }

    /**
     * Gets transactions from the past specified number of days
     * @param {number} days - Number of days to look back
     * @returns {Promise<Array>} Array of recent transactions
     */
    async getRecentTransactions(days = 30) {
        return new Promise((resolve, reject) => {
            const cutoffDate = new Date();
            cutoffDate.setDate(cutoffDate.getDate() - days);

            const sql = `
                SELECT id, date, amount, description, merchant, category, account,
                       transaction_type, status, location, currency, notes,
                       user_category, is_business, requires_review
                FROM transactions
                WHERE date >= ?
                ORDER BY date DESC
            `;

            this.db.all(sql, [cutoffDate.toISOString()], (err, rows) => {
                if (err) {
                    reject(err);
                    return;
                }

                const transactions = rows.map(row => ({
                    id: row.id,
                    date: new Date(row.date),
                    amount: parseFloat(row.amount),
                    description: row.description,
                    merchant: row.merchant,
                    category: row.category,
                    account: row.account,
                    transactionType: row.transaction_type,
                    status: row.status,
                    location: row.location,
                    currency: row.currency,
                    notes: row.notes,
                    userCategory: row.user_category,
                    isBusiness: !!row.is_business,
                    requiresReview: !!row.requires_review
                }));

                resolve(transactions);
            });
        });
    }

    /**
     * Calculates average spending patterns for anomaly detection
     * @param {Array} transactions - Array of transactions
     */
    calculateSpendingAverages(transactions) {
        if (!transactions || transactions.length === 0) {
            return;
        }

        // Group by category and calculate averages
        const categoryAmounts = {};
        const merchantAmounts = {};

        for (const transaction of transactions) {
            const cat = transaction.category || 'unknown';
            const merchant = transaction.merchant || 'unknown';

            if (!categoryAmounts[cat]) {
                categoryAmounts[cat] = [];
            }
            categoryAmounts[cat].push(transaction.amount);

            if (!merchantAmounts[merchant]) {
                merchantAmounts[merchant] = [];
            }
            merchantAmounts[merchant].push(transaction.amount);
        }

        // Calculate averages and standard deviations
        this.avgSpending = {};

        for (const [cat, amounts] of Object.entries(categoryAmounts)) {
            const mean = amounts.reduce((sum, val) => sum + val, 0) / amounts.length;
            const squaredDiffs = amounts.map(value => Math.pow(value - mean, 2));
            const avgSquaredDiff = squaredDiffs.reduce((sum, val) => sum + val, 0) / squaredDiffs.length;
            const stdDev = Math.sqrt(avgSquaredDiff);

            this.avgSpending[`avg_${cat}`] = {
                mean: mean,
                std: stdDev,
                count: amounts.length
            };
        }

        for (const [merch, amounts] of Object.entries(merchantAmounts)) {
            const mean = amounts.reduce((sum, val) => sum + val, 0) / amounts.length;
            const squaredDiffs = amounts.map(value => Math.pow(value - mean, 2));
            const avgSquaredDiff = squaredDiffs.reduce((sum, val) => sum + val, 0) / squaredDiffs.length;
            const stdDev = Math.sqrt(avgSquaredDiff);

            this.avgSpending[`avg_${merch}`] = {
                mean: mean,
                std: stdDev,
                count: amounts.length
            };
        }
    }

    /**
     * Analyzes a single transaction for anomalies
     * @param {Object} transaction - Transaction to analyze
     * @param {Array} allTransactions - All transactions for comparison
     * @returns {Promise<Array>} Array of alerts for this transaction
     */
    async analyzeTransaction(transaction, allTransactions) {
        const alerts = [];

        // Check for unusually large transactions
        const avgKey = `avg_${transaction.category || 'unknown'}`;
        if (this.avgSpending[avgKey]) {
            const avgData = this.avgSpending[avgKey];
            const meanAmount = avgData.mean;
            const stdAmount = avgData.std;

            if (stdAmount > 0 && transaction.amount > (meanAmount + 3 * stdAmount)) {
                alerts.push({
                    transactionId: transaction.id,
                    alertLevel: 'warning',
                    ruleTriggered: 'large_transaction',
                    message: `Transaction amount $${transaction.amount.toFixed(2)} is significantly higher than average $${meanAmount.toFixed(2)} for category ${transaction.category}`,
                    timestamp: new Date(),
                    requiresAction: true
                });
            }
        }

        // Check for round number amounts (potential fraud)
        if (Number.isInteger(transaction.amount) && transaction.amount > 50) {
            alerts.push({
                transactionId: transaction.id,
                alertLevel: 'info',
                ruleTriggered: 'round_number',
                message: `Transaction amount $${transaction.amount.toFixed(2)} is a round number, which may indicate potential fraud`,
                timestamp: new Date()
            });
        }

        // Check for small test charges (card testing)
        if (transaction.amount < 5) {
            const similarMerchantTransactions = allTransactions.filter(t =>
                t.merchant === transaction.merchant && t.amount < 5
            );

            if (similarMerchantTransactions.length > 2) {
                const recentSimilar = allTransactions.slice(0, 10).filter(t =>
                    t.merchant === transaction.merchant && t.amount < 5
                );

                if (recentSimilar.length > 2) {
                    alerts.push({
                        transactionId: transaction.id,
                        alertLevel: 'warning',
                        ruleTriggered: 'card_testing',
                        message: `Multiple small transactions detected with ${transaction.merchant}, possibly indicating card testing`,
                        timestamp: new Date(),
                        requiresAction: true
                    });
                }
            }
        }

        // Check for duplicate transactions
        const recentTransactions = allTransactions.filter(t =>
            (new Date() - new Date(t.date)) / (1000 * 60 * 60 * 24) <= 7
        );

        const duplicates = recentTransactions.filter(t =>
            t.merchant === transaction.merchant &&
            t.amount === transaction.amount &&
            t.id !== transaction.id
        );

        if (duplicates.length > 0) {
            alerts.push({
                transactionId: transaction.id,
                alertLevel: 'warning',
                ruleTriggered: 'duplicate_transaction',
                message: `Possible duplicate transaction detected with ${transaction.merchant} for $${transaction.amount.toFixed(2)}`,
                timestamp: new Date(),
                requiresAction: true
            });
        }

        return alerts;
    }

    /**
     * Stores alerts in the database
     * @param {Array} alerts - Array of alert objects to store
     */
    async storeAlerts(alerts) {
        return new Promise((resolve, reject) => {
            this.db.serialize(() => {
                const stmt = this.db.prepare(`
                    INSERT INTO alerts
                    (transaction_id, alert_level, rule_triggered, message, timestamp, requires_action)
                    VALUES (?, ?, ?, ?, ?, ?)
                `);

                for (const alert of alerts) {
                    stmt.run([
                        alert.transactionId,
                        alert.alertLevel,
                        alert.ruleTriggered,
                        alert.message,
                        alert.timestamp.toISOString(),
                        alert.requiresAction || false
                    ]);
                }

                stmt.finalize();
                resolve();
            });
        });
    }

    /**
     * Gets all alerts that require action
     * @returns {Promise<Array>} Array of unreviewed alerts
     */
    async getUnreviewedAlerts() {
        return new Promise((resolve, reject) => {
            const sql = `
                SELECT transaction_id, alert_level, rule_triggered, message, timestamp, requires_action
                FROM alerts
                WHERE resolved = FALSE AND requires_action = TRUE
                ORDER BY timestamp DESC
            `;

            this.db.all(sql, [], (err, rows) => {
                if (err) {
                    reject(err);
                    return;
                }

                const alerts = rows.map(row => ({
                    transactionId: row.transaction_id,
                    alertLevel: row.alert_level,
                    ruleTriggered: row.rule_triggered,
                    message: row.message,
                    timestamp: new Date(row.timestamp),
                    requiresAction: !!row.requires_action
                }));

                resolve(alerts);
            });
        });
    }

    /**
     * Generates a spending report for the specified period
     * @param {Date} startDate - Start date for the report
     * @param {Date} endDate - End date for the report
     * @returns {Promise<Object>} Spending report object
     */
    async generateSpendingReport(startDate, endDate) {
        return new Promise((resolve, reject) => {
            const sql = `
                SELECT category, SUM(amount) as total, COUNT(*) as count
                FROM transactions
                WHERE date BETWEEN ? AND ? AND transaction_type = 'debit'
                GROUP BY category
            `;

            this.db.all(sql, [startDate.toISOString(), endDate.toISOString()], (err, rows) => {
                if (err) {
                    reject(err);
                    return;
                }

                const categoryTotals = {};
                let totalSpending = 0;
                let transactionCount = 0;

                for (const row of rows) {
                    categoryTotals[row.category] = {
                        total: parseFloat(row.total),
                        count: row.count
                    };
                    totalSpending += parseFloat(row.total);
                    transactionCount += row.count;
                }

                // Calculate percentages
                const categoryPercentages = {};
                for (const [category, data] of Object.entries(categoryTotals)) {
                    categoryPercentages[category] = {
                        total: data.total,
                        percentage: totalSpending > 0 ? (data.total / totalSpending * 100) : 0,
                        count: data.count
                    };
                }

                const days = (endDate - startDate) / (1000 * 60 * 60 * 24);

                resolve({
                    periodStart: startDate,
                    periodEnd: endDate,
                    totalSpending: totalSpending,
                    transactionCount: transactionCount,
                    categoryBreakdown: categoryPercentages,
                    averageDailySpending: days > 0 ? totalSpending / days : 0
                });
            });
        });
    }

    /**
     * Gets transactions flagged with critical or warning alerts
     * @returns {Promise<Array>} Array of suspicious transactions
     */
    async getSuspiciousTransactions() {
        return new Promise((resolve, reject) => {
            // Get transaction IDs with critical or warning alerts
            const alertSql = `
                SELECT DISTINCT a.transaction_id
                FROM alerts a
                WHERE a.alert_level IN ('critical', 'warning') AND a.resolved = FALSE
            `;

            this.db.all(alertSql, [], (err, alertRows) => {
                if (err) {
                    reject(err);
                    return;
                }

                const suspiciousIds = alertRows.map(row => row.transaction_id);

                if (suspiciousIds.length === 0) {
                    resolve([]);
                    return;
                }

                // Build placeholder string for the IN clause
                const placeholders = suspiciousIds.map(() => '?').join(',');
                const transSql = `
                    SELECT id, date, amount, description, merchant, category, account,
                           transaction_type, status, location, currency, notes,
                           user_category, is_business, requires_review
                    FROM transactions
                    WHERE id IN (${placeholders})
                `;

                this.db.all(transSql, suspiciousIds, (err, transRows) => {
                    if (err) {
                        reject(err);
                        return;
                    }

                    const transactions = transRows.map(row => ({
                        id: row.id,
                        date: new Date(row.date),
                        amount: parseFloat(row.amount),
                        description: row.description,
                        merchant: row.merchant,
                        category: row.category,
                        account: row.account,
                        transactionType: row.transaction_type,
                        status: row.status,
                        location: row.location,
                        currency: row.currency,
                        notes: row.notes,
                        userCategory: row.user_category,
                        isBusiness: !!row.is_business,
                        requiresReview: !!row.requires_review
                    }));

                    resolve(transactions);
                });
            });
        });
    }

    /**
     * Exports all alerts to a CSV file
     * @param {string} outputPath - Path for the output CSV file
     */
    async exportAlertsToCsv(outputPath) {
        return new Promise((resolve, reject) => {
            const sql = `
                SELECT a.timestamp, a.alert_level, a.rule_triggered, a.message,
                       t.description, t.amount, t.merchant, t.category
                FROM alerts a
                JOIN transactions t ON a.transaction_id = t.id
                WHERE a.resolved = FALSE
                ORDER BY a.timestamp DESC
            `;

            this.db.all(sql, [], async (err, rows) => {
                if (err) {
                    reject(err);
                    return;
                }

                // Convert rows to CSV format
                let csvContent = 'timestamp,alert_level,rule_triggered,message,description,amount,merchant,category\n';

                for (const row of rows) {
                    // Escape quotes and create CSV row
                    const escapedRow = [
                        row.timestamp,
                        row.alert_level,
                        row.rule_triggered,
                        `"${(row.message || '').toString().replace(/"/g, '""')}"`,
                        `"${(row.description || '').toString().replace(/"/g, '""')}"`,
                        row.amount,
                        `"${(row.merchant || '').toString().replace(/"/g, '""')}"`,
                        `"${(row.category || '').toString().replace(/"/g, '""')}"`
                    ];

                    csvContent += escapedRow.join(',') + '\n';
                }

                try {
                    await fs.writeFile(outputPath, csvContent);
                    console.log(`Alerts exported to ${outputPath}`);
                    resolve();
                } catch (writeErr) {
                    reject(writeErr);
                }
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

module.exports = BankTransactionMonitorJS;

// If running as a standalone script
if (require.main === module) {
    const args = process.argv.slice(2);

    async function main() {
        const monitor = new BankTransactionMonitorJS();

        if (args.includes('--demo')) {
            // Create some demo transactions
            const demoTransactions = [
                {
                    id: monitor.generateId(),
                    date: new Date(Date.now() - 24 * 60 * 60 * 1000), // Yesterday
                    amount: 50.25,
                    description: 'Starbucks Coffee Purchase',
                    merchant: 'Starbucks',
                    category: 'dining_out',
                    account: 'checking',
                    transactionType: 'debit',
                    status: 'cleared'
                },
                {
                    id: monitor.generateId(),
                    date: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000), // 2 days ago
                    amount: 150.00,
                    description: 'Amazon Online Purchase',
                    merchant: 'Amazon',
                    category: 'shopping',
                    account: 'checking',
                    transactionType: 'debit',
                    status: 'cleared'
                },
                {
                    id: monitor.generateId(),
                    date: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000), // 3 days ago
                    amount: 2500.00, // Large amount for anomaly detection
                    description: 'Car Dealership Payment',
                    merchant: 'Car Dealership',
                    category: 'transportation',
                    account: 'checking',
                    transactionType: 'debit',
                    status: 'cleared'
                }
            ];

            await monitor.addTransactions(demoTransactions);
            console.log(`Added ${demoTransactions.length} demo transactions`);

            // Run anomaly detection
            const anomalies = await monitor.detectAnomalies();
            console.log(`Detected ${anomalies.length} potential anomalies`);

            // Generate a report
            const endDate = new Date();
            const startDate = new Date(endDate.getTime() - 30 * 24 * 60 * 60 * 1000); // 30 days ago
            const report = await monitor.generateSpendingReport(startDate, endDate);

            console.log('\n--- SPENDING REPORT ---');
            console.log(`Period: ${startDate.toDateString()} to ${endDate.toDateString()}`);
            console.log(`Total Spending: $${report.totalSpending.toFixed(2)}`);
            console.log(`Transaction Count: ${report.transactionCount}`);
            console.log(`Average Daily Spending: $${report.averageDailySpending.toFixed(2)}`);
            console.log('\nCategory Breakdown:');
            for (const [category, data] of Object.entries(report.categoryBreakdown)) {
                console.log(`  ${category}: $${data.total.toFixed(2)} (${data.percentage.toFixed(1)}%)`);
            }

            // Show unreviewed alerts
            const alerts = await monitor.getUnreviewedAlerts();
            console.log(`\nUnreviewed alerts: ${alerts.length}`);
            for (const alert of alerts) {
                console.log(`  ${alert.alertLevel.toUpperCase()}: ${alert.message}`);
            }
        }

        monitor.close();
    }

    main().catch(console.error);
}