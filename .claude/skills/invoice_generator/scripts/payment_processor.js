/**
 * Payment Processing Module for Invoice Generator Skill
 */

const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();

class PaymentProcessor {
    constructor() {
        // Setup logging
        this.logFile = path.join('/Logs', `payment_processor_${new Date().toISOString().split('T')[0]}.log`);

        // Database for payment records
        this.dbPath = path.join('/Data', 'payments.db');
        this.setupDatabase();

        // Payment gateway configuration
        this.paymentGateways = {
            stripe: {
                apiKey: process.env.STRIPE_SECRET_KEY,
                webhookSecret: process.env.STRIPE_WEBHOOK_SECRET
            },
            paypal: {
                clientId: process.env.PAYPAL_CLIENT_ID,
                clientSecret: process.env.PAYPAL_CLIENT_SECRET
            }
        };

        // Payment statuses
        this.paymentStatuses = {
            pending: 'pending',
            processing: 'processing',
            completed: 'completed',
            failed: 'failed',
            refunded: 'refunded',
            cancelled: 'cancelled'
        };

        // Payment methods
        this.paymentMethods = [
            'credit_card',
            'debit_card',
            'bank_transfer',
            'paypal',
            'stripe',
            'check',
            'wire_transfer'
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
     * Setup database for payment records
     */
    setupDatabase() {
        this.db = new sqlite3.Database(this.dbPath);

        // Create payments table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_id TEXT UNIQUE NOT NULL,
                invoice_id TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                payment_method TEXT NOT NULL,
                payment_gateway TEXT,
                gateway_transaction_id TEXT,
                payer_info TEXT,  -- JSON of payer details
                status TEXT DEFAULT 'pending',
                processed_at DATETIME,
                completed_at DATETIME,
                refunded_at DATETIME,
                failure_reason TEXT,
                metadata TEXT,  -- Additional metadata
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        `);

        // Create payment history table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS payment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_id TEXT NOT NULL,
                status_from TEXT NOT NULL,
                status_to TEXT NOT NULL,
                changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                changed_by TEXT DEFAULT 'system',
                notes TEXT
            )
        `);

        // Create indexes for performance
        this.db.run('CREATE INDEX IF NOT EXISTS idx_payment_id ON payments(payment_id)');
        this.db.run('CREATE INDEX IF NOT EXISTS idx_invoice_id ON payments(invoice_id)');
        this.db.run('CREATE INDEX IF NOT EXISTS idx_status ON payments(status)');
        this.db.run('CREATE INDEX IF NOT EXISTS idx_gateway_transaction_id ON payments(gateway_transaction_id)');

        // Create invoice payments linking
        this.db.run(`
            CREATE TABLE IF NOT EXISTS invoice_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id TEXT NOT NULL,
                payment_id TEXT NOT NULL,
                amount_paid REAL NOT NULL,
                payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (payment_id) REFERENCES payments(id)
            )
        `);
    }

    /**
     * Generate a unique payment ID
     */
    generatePaymentId() {
        const timestamp = Date.now().toString(36);
        const randomPart = Math.random().toString(36).substr(2, 5);
        return `PAY-${timestamp}-${randomPart}`.toUpperCase();
    }

    /**
     * Process a payment for an invoice
     */
    async processPayment(invoiceId, amount, paymentMethod, payerInfo, options = {}) {
        try {
            const paymentId = this.generatePaymentId();
            const {
                currency = 'USD',
                paymentGateway = null,
                metadata = {},
                processImmediately = true
            } = options;

            // Validate inputs
            if (!this.paymentMethods.includes(paymentMethod)) {
                throw new Error(`Invalid payment method: ${paymentMethod}`);
            }

            if (amount <= 0) {
                throw new Error('Payment amount must be greater than zero');
            }

            // Insert payment record
            const stmt = this.db.prepare(`
                INSERT INTO payments (
                    payment_id, invoice_id, amount, currency, payment_method,
                    payment_gateway, payer_info, status, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            `);

            stmt.run([
                paymentId,
                invoiceId,
                amount,
                currency,
                paymentMethod,
                paymentGateway,
                JSON.stringify(payerInfo),
                this.paymentStatuses.pending,
                JSON.stringify(metadata)
            ]);

            stmt.finalize();

            this.log('INFO', `Payment record created: ${paymentId} for invoice ${invoiceId}`);

            // Update payment history
            this.updatePaymentStatusHistory(paymentId, 'none', this.paymentStatuses.pending, 'system', 'Payment record created');

            // Process payment immediately if requested
            if (processImmediately) {
                await this.executePayment(paymentId);
            }

            return {
                success: true,
                paymentId,
                status: this.paymentStatuses.pending,
                message: `Payment ${paymentId} created for invoice ${invoiceId}`
            };

        } catch (error) {
            this.log('ERROR', `Failed to process payment: ${error.message}`);
            return {
                success: false,
                error: error.message,
                paymentId: null
            };
        }
    }

    /**
     * Execute actual payment processing
     */
    async executePayment(paymentId) {
        try {
            // Get payment details
            const payment = await this.getPayment(paymentId);
            if (!payment) {
                throw new Error(`Payment ${paymentId} not found`);
            }

            if (payment.status !== this.paymentStatuses.pending) {
                throw new Error(`Payment ${paymentId} is not in pending status`);
            }

            // Update status to processing
            await this.updatePaymentStatus(paymentId, this.paymentStatuses.processing);

            // Process payment based on method
            let result;
            switch (payment.paymentMethod) {
                case 'credit_card':
                case 'debit_card':
                    result = await this.processCardPayment(payment);
                    break;
                case 'paypal':
                    result = await this.processPayPalPayment(payment);
                    break;
                case 'bank_transfer':
                case 'wire_transfer':
                    result = await this.processBankTransfer(payment);
                    break;
                case 'check':
                    result = await this.processCheckPayment(payment);
                    break;
                default:
                    result = await this.processGenericPayment(payment);
            }

            if (result.success) {
                // Update to completed status
                await this.completePayment(paymentId, result.transactionId);

                this.log('INFO', `Payment ${paymentId} completed successfully`);
                return { success: true, transactionId: result.transactionId };
            } else {
                // Update to failed status
                await this.failPayment(paymentId, result.error || 'Payment processing failed');

                this.log('ERROR', `Payment ${paymentId} failed: ${result.error}`);
                return { success: false, error: result.error };
            }

        } catch (error) {
            this.log('ERROR', `Error executing payment ${paymentId}: ${error.message}`);

            // Mark as failed
            await this.failPayment(paymentId, error.message);
            return { success: false, error: error.message };
        }
    }

    /**
     * Process card payment (Stripe integration)
     */
    async processCardPayment(payment) {
        // In a real implementation, this would integrate with Stripe or similar
        // For simulation purposes, we'll simulate the process
        try {
            // Simulate API call delay
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Simulate success/failure (95% success rate)
            const isSuccess = Math.random() > 0.05;

            if (isSuccess) {
                // Generate mock transaction ID
                const transactionId = `txn_${Math.random().toString(36).substr(2, 9)}`;
                return { success: true, transactionId };
            } else {
                return { success: false, error: 'Card declined by issuer' };
            }
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Process PayPal payment
     */
    async processPayPalPayment(payment) {
        // In a real implementation, this would integrate with PayPal API
        try {
            // Simulate API call delay
            await new Promise(resolve => setTimeout(resolve, 1500));

            // Simulate success/failure (98% success rate)
            const isSuccess = Math.random() > 0.02;

            if (isSuccess) {
                // Generate mock transaction ID
                const transactionId = `PP-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
                return { success: true, transactionId };
            } else {
                return { success: false, error: 'PayPal payment failed' };
            }
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Process bank transfer
     */
    async processBankTransfer(payment) {
        // For bank transfers, we typically can't process immediately
        // So we'll mark it as pending manual verification
        try {
            // Simulate processing delay
            await new Promise(resolve => setTimeout(resolve, 500));

            // For bank transfers, we usually need manual verification
            // So we'll return a success but mark for manual review
            const transactionId = `BT-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
            return {
                success: true,
                transactionId,
                requiresManualVerification: true,
                message: 'Bank transfer initiated, requires manual verification'
            };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Process check payment
     */
    async processCheckPayment(payment) {
        // Checks require manual processing
        try {
            // Generate mock check number
            const checkNumber = `CHK-${Date.now()}`;
            return {
                success: true,
                transactionId: checkNumber,
                requiresManualProcessing: true,
                message: 'Check payment received, requires manual processing'
            };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Process generic payment
     */
    async processGenericPayment(payment) {
        // For other payment methods
        try {
            // Simulate processing
            await new Promise(resolve => setTimeout(resolve, 1000));

            const isSuccess = Math.random() > 0.1; // 90% success rate

            if (isSuccess) {
                const transactionId = `GEN-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
                return { success: true, transactionId };
            } else {
                return { success: false, error: 'Payment method not supported or failed' };
            }
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Update payment status
     */
    async updatePaymentStatus(paymentId, newStatus, failureReason = null) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                UPDATE payments
                SET status = ?, updated_at = ?, failure_reason = ?
                WHERE payment_id = ?
            `);

            stmt.run([newStatus, new Date().toISOString(), failureReason, paymentId], function(err) {
                if (err) {
                    reject(err);
                } else if (this.changes === 0) {
                    reject(new Error(`Payment ${paymentId} not found`));
                } else {
                    resolve(true);
                }
            });

            stmt.finalize();
        });
    }

    /**
     * Complete a payment
     */
    async completePayment(paymentId, gatewayTransactionId) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                UPDATE payments
                SET status = ?, completed_at = ?, gateway_transaction_id = ?, updated_at = ?
                WHERE payment_id = ?
            `);

            stmt.run([
                this.paymentStatuses.completed,
                new Date().toISOString(),
                gatewayTransactionId,
                new Date().toISOString(),
                paymentId
            ], function(err) {
                if (err) {
                    reject(err);
                } else if (this.changes === 0) {
                    reject(new Error(`Payment ${paymentId} not found`));
                } else {
                    resolve(true);
                }
            });

            stmt.finalize();
        });
    }

    /**
     * Fail a payment
     */
    async failPayment(paymentId, failureReason) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                UPDATE payments
                SET status = ?, failure_reason = ?, updated_at = ?
                WHERE payment_id = ?
            `);

            stmt.run([
                this.paymentStatuses.failed,
                failureReason,
                new Date().toISOString(),
                paymentId
            ], function(err) {
                if (err) {
                    reject(err);
                } else if (this.changes === 0) {
                    reject(new Error(`Payment ${paymentId} not found`));
                } else {
                    resolve(true);
                }
            });

            stmt.finalize();
        });
    }

    /**
     * Update payment status history
     */
    updatePaymentStatusHistory(paymentId, statusFrom, statusTo, changedBy = 'system', notes = '') {
        const stmt = this.db.prepare(`
            INSERT INTO payment_history (payment_id, status_from, status_to, changed_by, notes)
            VALUES (?, ?, ?, ?, ?)
        `);

        stmt.run([paymentId, statusFrom, statusTo, changedBy, notes]);
        stmt.finalize();
    }

    /**
     * Get payment details
     */
    async getPayment(paymentId) {
        return new Promise((resolve, reject) => {
            this.db.get(`
                SELECT * FROM payments WHERE payment_id = ?
            `, [paymentId], (err, row) => {
                if (err) {
                    reject(err);
                } else {
                    if (row) {
                        // Parse JSON fields
                        row.payer_info = JSON.parse(row.payer_info);
                        row.metadata = JSON.parse(row.metadata);
                    }
                    resolve(row);
                }
            });
        });
    }

    /**
     * Get payments for an invoice
     */
    async getInvoicePayments(invoiceId) {
        return new Promise((resolve, reject) => {
            this.db.all(`
                SELECT * FROM payments WHERE invoice_id = ? ORDER BY created_at DESC
            `, [invoiceId], (err, rows) => {
                if (err) {
                    reject(err);
                } else {
                    // Parse JSON fields for each row
                    rows.forEach(row => {
                        row.payer_info = JSON.parse(row.payer_info);
                        row.metadata = JSON.parse(row.metadata);
                    });
                    resolve(rows);
                }
            });
        });
    }

    /**
     * Refund a payment
     */
    async refundPayment(paymentId, refundAmount = null, reason = 'General refund') {
        try {
            const payment = await this.getPayment(paymentId);
            if (!payment) {
                throw new Error(`Payment ${paymentId} not found`);
            }

            if (payment.status !== this.paymentStatuses.completed) {
                throw new Error(`Cannot refund payment ${paymentId} - status is ${payment.status}`);
            }

            // In a real implementation, this would call the payment gateway's refund API
            // For simulation, we'll just update the status

            // Update status to refunded
            await this.updatePaymentStatus(paymentId, this.paymentStatuses.refunded);

            // Update the refunded_at timestamp
            const stmt = this.db.prepare(`
                UPDATE payments
                SET refunded_at = ?, updated_at = ?
                WHERE payment_id = ?
            `);

            stmt.run([new Date().toISOString(), new Date().toISOString(), paymentId]);
            stmt.finalize();

            // Update payment history
            this.updatePaymentStatusHistory(paymentId, this.paymentStatuses.completed, this.paymentStatuses.refunded, 'system', reason);

            this.log('INFO', `Payment ${paymentId} refunded: ${reason}`);
            return { success: true, message: `Payment ${paymentId} refunded successfully` };

        } catch (error) {
            this.log('ERROR', `Failed to refund payment ${paymentId}: ${error.message}`);
            return { success: false, error: error.message };
        }
    }

    /**
     * Search payments with filters
     */
    async searchPayments(filters = {}) {
        return new Promise((resolve, reject) => {
            let query = 'SELECT * FROM payments WHERE 1=1';
            const params = [];

            if (filters.invoiceId) {
                query += ' AND invoice_id = ?';
                params.push(filters.invoiceId);
            }

            if (filters.status) {
                query += ' AND status = ?';
                params.push(filters.status);
            }

            if (filters.paymentMethod) {
                query += ' AND payment_method = ?';
                params.push(filters.paymentMethod);
            }

            if (filters.dateFrom) {
                query += ' AND created_at >= ?';
                params.push(filters.dateFrom);
            }

            if (filters.dateTo) {
                query += ' AND created_at <= ?';
                params.push(filters.dateTo);
            }

            if (filters.minAmount) {
                query += ' AND amount >= ?';
                params.push(filters.minAmount);
            }

            if (filters.maxAmount) {
                query += ' AND amount <= ?';
                params.push(filters.maxAmount);
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
                    // Parse JSON fields for each row
                    rows.forEach(row => {
                        try {
                            row.payer_info = JSON.parse(row.payer_info);
                            row.metadata = JSON.parse(row.metadata);
                        } catch (e) {
                            // If parsing fails, keep as-is
                        }
                    });
                    resolve(rows);
                }
            });
        });
    }

    /**
     * Get payment statistics
     */
    async getStatistics() {
        return new Promise((resolve, reject) => {
            const stats = {};

            // Total payments
            this.db.each('SELECT COUNT(*) as total FROM payments', (err, row) => {
                if (err) throw err;
                stats.total_payments = row.total;
            });

            // Payments by status
            stats.by_status = {};
            this.db.each('SELECT status, COUNT(*) as count FROM payments GROUP BY status', (err, row) => {
                if (err) throw err;
                stats.by_status[row.status] = row.count;
            });

            // Payments by method
            stats.by_method = {};
            this.db.each('SELECT payment_method, COUNT(*) as count FROM payments GROUP BY payment_method', (err, row) => {
                if (err) throw err;
                stats.by_method[row.payment_method] = row.count;
            });

            // Total amount processed
            this.db.each('SELECT SUM(amount) as total FROM payments WHERE status = ?', [this.paymentStatuses.completed], (err, row) => {
                if (err) throw err;
                stats.total_processed = parseFloat(row.total || 0);
            });

            // Average payment amount
            this.db.each('SELECT AVG(amount) as avg FROM payments WHERE status = ?', [this.paymentStatuses.completed], (err, row) => {
                if (err) throw err;
                stats.average_payment = parseFloat(row.avg || 0);
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

module.exports = PaymentProcessor;

// Example usage
if (require.main === module) {
    const processor = new PaymentProcessor();

    // Example: Process a payment
    (async () => {
        const result = await processor.processPayment(
            'INV-20231101-001',
            1500.00,
            'credit_card',
            {
                name: 'John Doe',
                email: 'john@example.com',
                billingAddress: '123 Main St, Anytown, USA'
            },
            {
                currency: 'USD',
                metadata: { source: 'web_portal' }
            }
        );

        console.log('Payment processing result:', result);

        // Get payment statistics
        const stats = await processor.getStatistics();
        console.log('Payment statistics:', stats);

        // Close database connection
        processor.close();
    })();
}