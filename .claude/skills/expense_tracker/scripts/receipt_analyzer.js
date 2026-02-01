/**
 * Receipt Analyzer Module for Expense Tracker Skill
 */

const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const Tesseract = require('tesseract.js');

class ReceiptAnalyzer {
    constructor() {
        // Setup logging
        this.logFile = path.join('/Logs', `receipt_analyzer_${new Date().toISOString().split('T')[0]}.log`);

        // Database for receipt analysis
        this.dbPath = path.join('/Data', 'receipts.db');
        this.setupDatabase();

        // Expense categories
        this.expenseCategories = {
            'travel': ['airfare', 'lodging', 'meals', 'ground_transportation', 'parking', 'car_rental'],
            'office': ['rent', 'utilities', 'office_supplies', 'equipment', 'maintenance'],
            'meals_entertainment': ['business_meals', 'entertainment', 'gifts'],
            'marketing': ['online_ads', 'print_ads', 'trade_shows', 'promotional_items'],
            'professional_services': ['legal', 'accounting', 'consulting', 'recruitment'],
            'technology': ['software', 'hardware', 'cloud_services', 'telecom'],
            'insurance': ['general_liability', 'professional_liability', 'property_insurance', 'health_insurance'],
            'payroll_benefits': ['salaries', 'benefits', 'bonuses', 'payroll_taxes'],
            'banking_finance': ['bank_fees', 'loan_interest', 'credit_card_fees', 'investment_expenses'],
            'utilities_services': ['electricity', 'water_sewer', 'internet', 'phone']
        };

        // Common merchant categories
        this.merchantCategories = {
            'restaurants': ['restaurant', 'cafe', 'bar', 'diner', 'bistro', 'pub'],
            'hotels': ['hotel', 'motel', 'inn', 'lodge', 'resort'],
            'gas_stations': ['gas', 'fuel', 'petrol', 'shell', 'exxon', 'chevron', 'mobil'],
            'grocery': ['grocery', 'supermarket', 'market', 'whole foods', 'kroger', 'walmart'],
            'airlines': ['airlines', 'delta', 'american', 'united', 'southwest', 'jetblue'],
            'car_rental': ['enterprise', 'hertz', 'avis', 'budget', 'national'],
            'shopping': ['amazon', 'apple', 'best buy', 'target', 'costco', 'walgreens']
        };

        // Currency patterns
        this.currencyPatterns = [
            /\$([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?)/gi,
            /([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?)\s*(dollars|usd|us dollars)/gi,
            /([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?)\s*dol\./gi
        ];

        // Date patterns
        this.datePatterns = [
            /(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})/g,
            /(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})/g,
            /(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{2,4})/gi,
            /(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{2,4})/gi
        ];
    }

    /**
     * Log messages to file
     */
    log(level, message) {
        const timestamp = new Date().toISOString();
        const logEntry = `${timestamp} - ${level.toUpperCase()} - ${message}\n`;
        fs.appendFileSync(this.logFile, logEntry);
        console.log(logEntry.trim());
    }

    /**
     * Setup database for receipt analysis
     */
    setupDatabase() {
        this.db = new sqlite3.Database(this.dbPath);

        // Create receipts table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id TEXT UNIQUE NOT NULL,
                image_path TEXT NOT NULL,
                extracted_text TEXT,
                extracted_amount DECIMAL(10,2),
                extracted_date TEXT,
                extracted_merchant TEXT,
                suggested_category TEXT,
                suggested_subcategory TEXT,
                confidence_score REAL DEFAULT 0.0,
                analysis_complete BOOLEAN DEFAULT FALSE,
                analyzed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        `);

        // Create receipt validation results table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id TEXT NOT NULL,
                validation_rule TEXT NOT NULL,
                result TEXT NOT NULL,  -- pass, fail, warning
                message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (receipt_id) REFERENCES receipts (receipt_id)
            )
        `);

        // Create indexes for performance
        this.db.run('CREATE INDEX IF NOT EXISTS idx_receipt_id ON receipts(receipt_id)');
        this.db.run('CREATE INDEX IF NOT EXISTS idx_extracted_merchant ON receipts(extracted_merchant)');
        this.db.run('CREATE INDEX IF NOT EXISTS idx_suggested_category ON receipts(suggested_category)');
        this.db.run('CREATE INDEX IF NOT EXISTS idx_analysis_complete ON receipts(analysis_complete)');
    }

    /**
     * Generate a unique receipt ID
     */
    generateReceiptId() {
        const timestamp = Date.now().toString(36);
        const randomPart = Math.random().toString(36).substr(2, 8);
        return `RCPT-${timestamp}-${randomPart}`.toUpperCase();
    }

    /**
     * Analyze a receipt image
     */
    async analyzeReceipt(imagePath) {
        try {
            const receiptId = this.generateReceiptId();

            // First, create a record in the database
            await this.createReceiptRecord(receiptId, imagePath);

            this.log('INFO', `Starting analysis for receipt ${receiptId} from ${imagePath}`);

            // Extract text from image using OCR
            const extractedText = await this.extractTextFromImage(imagePath);

            // Analyze the extracted text
            const analysisResult = this.analyzeExtractedText(extractedText);

            // Update the database with analysis results
            await this.updateReceiptAnalysis(receiptId, {
                extracted_text: extractedText,
                extracted_amount: analysisResult.amount,
                extracted_date: analysisResult.date,
                extracted_merchant: analysisResult.merchant,
                suggested_category: analysisResult.category,
                suggested_subcategory: analysisResult.subcategory,
                confidence_score: analysisResult.confidence,
                analysis_complete: true,
                analyzed_at: new Date().toISOString()
            });

            this.log('INFO', `Analysis completed for receipt ${receiptId}`);

            return {
                success: true,
                receiptId,
                ...analysisResult
            };

        } catch (error) {
            this.log('ERROR', `Failed to analyze receipt from ${imagePath}: ${error.message}`);

            // Update with error status
            await this.updateReceiptAnalysis(this.generateReceiptId(), {
                analysis_complete: true,
                analyzed_at: new Date().toISOString()
            }).catch(() => {}); // Ignore error in error handling

            return {
                success: false,
                error: error.message,
                receiptId: null
            };
        }
    }

    /**
     * Create a receipt record in the database
     */
    async createReceiptRecord(receiptId, imagePath) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT INTO receipts (receipt_id, image_path) VALUES (?, ?)
            `);

            stmt.run([receiptId, imagePath], function(err) {
                if (err) {
                    reject(err);
                } else {
                    resolve(this.lastID);
                }
            });

            stmt.finalize();
        });
    }

    /**
     * Update receipt analysis results
     */
    async updateReceiptAnalysis(receiptId, analysisData) {
        return new Promise((resolve, reject) => {
            const columns = Object.keys(analysisData).join(', ');
            const placeholders = Object.keys(analysisData).map(() => '?').join(', ');
            const values = Object.values(analysisData);

            const stmt = this.db.prepare(`
                UPDATE receipts
                SET ${columns} = ${placeholders}
                WHERE receipt_id = ?
            `);

            stmt.run([...values, receiptId], function(err) {
                if (err) {
                    reject(err);
                } else {
                    resolve(this.changes > 0);
                }
            });

            stmt.finalize();
        });
    }

    /**
     * Extract text from image using OCR
     */
    async extractTextFromImage(imagePath) {
        try {
            // In a real implementation, this would use Tesseract.js
            // For simulation purposes, we'll return mock data
            // In practice: return (await Tesseract.recognize(imagePath)).data.text;

            // Simulate OCR processing time
            await new Promise(resolve => setTimeout(resolve, 1000));

            // For demonstration, we'll return sample text
            // In a real implementation, you'd actually call the OCR service
            this.log('INFO', `Simulated OCR processing for ${imagePath}`);

            // Return mock extracted text based on the image path
            if (imagePath.includes('restaurant') || imagePath.includes('meal')) {
                return `RESTAURANT RECEIPT
                John's Cafe
                123 Main Street
                City, State 12345

                Item                Price
                Lunch Special       $15.99
                Drink               $2.50
                Dessert             $4.99

                Subtotal: $23.48
                Tax:      $1.88
                Total:    $25.36

                Date: 03/15/2023
                Time: 12:45 PM
                `;
            } else if (imagePath.includes('hotel') || imagePath.includes('lodging')) {
                return `PRESTIGE HOTEL RECEIPT
                Prestige Hotel & Suites
                456 Business Ave
                Downtown, ST 54321

                Description           Amount
                Room Charge (3 nights) $450.00
                WiFi                  $15.00
                Breakfast             $36.00
                Parking               $30.00

                Subtotal: $531.00
                Tax:      $42.48
                Total:    $573.48

                Check-in: 03/10/2023
                Check-out: 03/13/2023
                `;
            } else {
                return `OFFICE SUPPLY RECEIPT
                OfficeMax
                789 Commercial Blvd
                Suite 100
                Business District, ST 98765

                Item                    Qty  Price   Total
                Printer Paper (8.5x11)   5   $8.99   $44.95
                Pens (Box of 12)         2   $5.49   $10.98
                Stapler                  1   $12.99  $12.99
                Notebook (Large)         3   $3.99   $11.97

                Subtotal: $80.89
                Tax:      $6.47
                Total:    $87.36

                Date: 03/12/2023
                `;
            }
        } catch (error) {
            this.log('ERROR', `OCR extraction failed: ${error.message}`);
            throw error;
        }
    }

    /**
     * Analyze extracted text and extract key information
     */
    analyzeExtractedText(text) {
        try {
            const result = {
                amount: null,
                date: null,
                merchant: '',
                category: 'office',  // default category
                subcategory: 'office_supplies',  // default subcategory
                confidence: 0.5  // default confidence
            };

            // Extract amount
            result.amount = this.extractAmount(text);

            // Extract date
            result.date = this.extractDate(text);

            // Extract merchant
            result.merchant = this.extractMerchant(text);

            // Determine category and subcategory
            const categoryInfo = this.categorizeReceipt(text, result.merchant);
            result.category = categoryInfo.category;
            result.subcategory = categoryInfo.subcategory;

            // Calculate confidence score
            result.confidence = this.calculateConfidence(result, text);

            return result;

        } catch (error) {
            this.log('ERROR', `Error analyzing text: ${error.message}`);
            return {
                amount: null,
                date: null,
                merchant: '',
                category: 'unknown',
                subcategory: 'unknown',
                confidence: 0.0
            };
        }
    }

    /**
     * Extract amount from text
     */
    extractAmount(text) {
        const lines = text.split('\n');

        // Look for common amount indicators
        const amountIndicators = ['total', 'amount', 'balance', 'due'];

        for (const line of lines) {
            const lowerLine = line.toLowerCase();

            // Check if line contains amount indicator
            for (const indicator of amountIndicators) {
                if (lowerLine.includes(indicator)) {
                    // Find currency amount in the line
                    const currencyMatch = line.match(/\$([0-9,]+\.?[0-9]*)/i);
                    if (currencyMatch) {
                        return parseFloat(currencyMatch[1].replace(/,/g, ''));
                    }

                    // Alternative pattern
                    const altMatch = line.match(/([0-9,]+\.?[0-9]*)\s*(dollars|usd|us dollars)/i);
                    if (altMatch) {
                        return parseFloat(altMatch[1].replace(/,/g, ''));
                    }
                }
            }
        }

        // If no specific indicator found, look for the largest amount
        let amounts = [];
        for (const pattern of this.currencyPatterns) {
            let match;
            while ((match = pattern.exec(text)) !== null) {
                amounts.push(parseFloat(match[1].replace(/,/g, '')));
            }
        }

        if (amounts.length > 0) {
            // Return the largest amount (usually the total)
            return Math.max(...amounts);
        }

        return null;
    }

    /**
     * Extract date from text
     */
    extractDate(text) {
        const lines = text.split('\n');

        // Look for common date indicators
        const dateIndicators = ['date', 'time', 'issued', 'printed'];

        for (const line of lines) {
            const lowerLine = line.toLowerCase();

            // Check if line contains date indicator
            for (const indicator of dateIndicators) {
                if (lowerLine.includes(indicator)) {
                    // Find date pattern in the line
                    for (const pattern of this.datePatterns) {
                        const dateMatch = line.match(pattern);
                        if (dateMatch) {
                            return dateMatch[0];
                        }
                    }
                }
            }
        }

        // If no specific indicator found, look for any date
        for (const pattern of this.datePatterns) {
            const dateMatch = text.match(pattern);
            if (dateMatch) {
                return dateMatch[0];
            }
        }

        return null;
    }

    /**
     * Extract merchant name from text
     */
    extractMerchant(text) {
        const lines = text.split('\n');

        // Common merchant name locations (top of receipt)
        const topLines = lines.slice(0, 5);

        // Look for the first non-empty line that looks like a business name
        for (const line of topLines) {
            const cleanLine = line.trim();

            // Skip lines that are obviously not merchant names
            if (!cleanLine ||
                cleanLine.toLowerCase().includes('receipt') ||
                cleanLine.toLowerCase().includes('thank you') ||
                cleanLine.toLowerCase().includes('register') ||
                /^\d+$/.test(cleanLine) ||  // Just numbers
                cleanLine.startsWith('$')) {  // Starts with currency
                continue;
            }

            // Check if line contains common business indicators
            if (cleanLine.length > 3 && !cleanLine.includes(':')) {  // Likely a business name
                return cleanLine;
            }
        }

        return '';
    }

    /**
     * Categorize receipt based on content and merchant
     */
    categorizeReceipt(text, merchant) {
        const lowerText = text.toLowerCase();
        const lowerMerchant = merchant.toLowerCase();

        // Check merchant against known categories
        for (const [category, merchants] of Object.entries(this.merchantCategories)) {
            if (merchants.some(m => lowerMerchant.includes(m))) {
                // Determine subcategory based on merchant
                return {
                    category: category.includes('restaurant') || category.includes('bar') || category.includes('cafe') ? 'meals_entertainment' :
                             category.includes('hotel') || category.includes('motel') ? 'travel' :
                             category.includes('airlines') ? 'travel' :
                             category.includes('car_rental') ? 'travel' :
                             category.includes('gas') ? 'travel' : 'office',
                    subcategory: category
                };
            }
        }

        // Check content for category keywords
        for (const [category, subcategories] of Object.entries(this.expenseCategories)) {
            for (const subcategory of subcategories) {
                if (lowerText.includes(subcategory.replace('_', ' '))) {
                    return { category, subcategory };
                }
            }
        }

        // Default category based on amount and common patterns
        if (lowerText.includes('meal') || lowerText.includes('lunch') || lowerText.includes('dinner') ||
            lowerText.includes('breakfast') || lowerText.includes('restaurant') || lowerText.includes('cafe')) {
            return { category: 'meals_entertainment', subcategory: 'business_meals' };
        }

        if (lowerText.includes('hotel') || lowerText.includes('motel') || lowerText.includes('inn') ||
            lowerText.includes('airline') || lowerText.includes('flight') || lowerText.includes('airport')) {
            return { category: 'travel', subcategory: 'lodging' }; // or airfare based on content
        }

        if (lowerText.includes('office') || lowerText.includes('supply') || lowerText.includes('paper') ||
            lowerText.includes('pen') || lowerText.includes('printer')) {
            return { category: 'office', subcategory: 'office_supplies' };
        }

        // Default to office supplies if nothing specific is found
        return { category: 'office', subcategory: 'office_supplies' };
    }

    /**
     * Calculate confidence score for analysis
     */
    calculateConfidence(result, text) {
        let score = 0.5; // Base score

        // Increase score if key information is found
        if (result.amount !== null) score += 0.15;
        if (result.date !== null) score += 0.15;
        if (result.merchant && result.merchant.length > 3) score += 0.15;

        // Increase score if category seems appropriate
        if (result.category && result.category !== 'unknown') score += 0.1;

        // Additional scoring based on text quality
        const lines = text.split('\n');
        const nonEmptyLines = lines.filter(line => line.trim().length > 0);

        if (nonEmptyLines.length > 5) {  // Receipt appears to have substantial content
            score += 0.1;
        }

        // Cap at 0.95 for imperfect OCR
        return Math.min(score, 0.95);
    }

    /**
     * Validate receipt information
     */
    validateReceipt(receiptInfo) {
        const errors = [];
        const warnings = [];

        // Validate amount
        if (receiptInfo.amount === null || isNaN(receiptInfo.amount) || receiptInfo.amount <= 0) {
            errors.push("Amount could not be extracted or is invalid");
        } else if (receiptInfo.amount > 10000) {
            warnings.push("Amount seems unusually high, please verify");
        }

        // Validate date
        if (!receiptInfo.date) {
            errors.push("Date could not be extracted");
        } else {
            // Try to parse the date to ensure it's valid
            const parsedDate = new Date(receiptInfo.date);
            if (isNaN(parsedDate.getTime())) {
                errors.push("Date format is invalid");
            } else {
                const today = new Date();
                const ninetyDaysAgo = new Date();
                ninetyDaysAgo.setDate(today.getDate() - 90);

                if (parsedDate > today) {
                    errors.push("Receipt date is in the future");
                } else if (parsedDate < ninetyDaysAgo) {
                    warnings.push("Receipt date is more than 90 days old");
                }
            }
        }

        // Validate merchant
        if (!receiptInfo.merchant || receiptInfo.merchant.length < 3) {
            errors.push("Merchant name could not be extracted or is too short");
        }

        // Validate category
        if (!receiptInfo.category || !Object.keys(this.expenseCategories).includes(receiptInfo.category)) {
            warnings.push("Category could not be determined, using default");
        }

        // Validate confidence score
        if (receiptInfo.confidence < 0.6) {
            warnings.push(`Low confidence in extraction (${(receiptInfo.confidence * 100).toFixed(1)}%), please review`);
        }

        return {
            isValid: errors.length === 0,
            errors,
            warnings,
            confidence: receiptInfo.confidence
        };
    }

    /**
     * Get receipt analysis by ID
     */
    async getReceiptAnalysis(receiptId) {
        return new Promise((resolve, reject) => {
            this.db.get(`
                SELECT * FROM receipts WHERE receipt_id = ?
            `, [receiptId], (err, row) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(row);
                }
            });
        });
    }

    /**
     * Search receipts with filters
     */
    async searchReceipts(filters = {}) {
        return new Promise((resolve, reject) => {
            let query = 'SELECT * FROM receipts WHERE 1=1';
            const params = [];

            if (filters.merchant) {
                query += ' AND extracted_merchant LIKE ?';
                params.push(`%${filters.merchant}%`);
            }

            if (filters.category) {
                query += ' AND suggested_category = ?';
                params.push(filters.category);
            }

            if (filters.dateFrom) {
                query += ' AND extracted_date >= ?';
                params.push(filters.dateFrom);
            }

            if (filters.dateTo) {
                query += ' AND extracted_date <= ?';
                params.push(filters.dateTo);
            }

            if (filters.minAmount) {
                query += ' AND extracted_amount >= ?';
                params.push(filters.minAmount);
            }

            if (filters.maxAmount) {
                query += ' AND extracted_amount <= ?';
                params.push(filters.maxAmount);
            }

            if (typeof filters.analysisComplete === 'boolean') {
                query += ' AND analysis_complete = ?';
                params.push(filters.analysisComplete ? 1 : 0);
            }

            query += ' ORDER BY created_at DESC';

            if (filters.limit) {
                query += ' LIMIT ?';
                params.push(filters.limit);
            }

            this.db.all(query, params, (err, rows) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(rows);
                }
            });
        });
    }

    /**
     * Get receipt statistics
     */
    async getStatistics() {
        return new Promise((resolve, reject) => {
            const stats = {};

            // Total receipts analyzed
            this.db.each('SELECT COUNT(*) as total FROM receipts', (err, row) => {
                if (err) throw err;
                stats.total_receipts = row.total;
            });

            // Receipts by category
            stats.by_category = {};
            this.db.each('SELECT suggested_category, COUNT(*) as count FROM receipts GROUP BY suggested_category', (err, row) => {
                if (err) throw err;
                stats.by_category[row.suggested_category] = row.count;
            });

            // Receipts by merchant
            stats.top_merchants = [];
            this.db.each('SELECT extracted_merchant, COUNT(*) as count FROM receipts GROUP BY extracted_merchant ORDER BY count DESC LIMIT 10', (err, row) => {
                if (err) throw err;
                stats.top_merchants.push({ merchant: row.extracted_merchant, count: row.count });
            });

            // Average confidence score
            this.db.each('SELECT AVG(confidence_score) as avg_confidence FROM receipts', (err, row) => {
                if (err) throw err;
                stats.average_confidence = parseFloat(row.avg_confidence || 0);
            });

            // Successfully analyzed receipts
            this.db.each('SELECT COUNT(*) as complete FROM receipts WHERE analysis_complete = 1', (err, row) => {
                if (err) throw err;
                stats.analyzed_receipts = row.complete;
            });

            resolve(stats);
        });
    }

    /**
     * Close the database connection
     */
    close() {
        if (this.db) {
            this.db.close();
        }
    }
}

module.exports = ReceiptAnalyzer;

// Example usage
if (require.main === module) {
    const analyzer = new ReceiptAnalyzer();

    // Example: Analyze a receipt
    (async () => {
        try {
            const result = await analyzer.analyzeReceipt('/path/to/receipt.jpg');
            console.log('Receipt analysis result:', result);

            // Validate the result
            const validation = analyzer.validateReceipt(result);
            console.log('Validation result:', validation);

            // Get statistics
            const stats = await analyzer.getStatistics();
            console.log('Receipt statistics:', stats);

            // Close database connection
            analyzer.close();
        } catch (error) {
            console.error('Error in receipt analysis:', error);
        }
    })();
}