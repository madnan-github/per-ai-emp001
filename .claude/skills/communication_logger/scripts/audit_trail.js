/**
 * Audit Trail Module for Communication Logger Skill
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const sqlite3 = require('sqlite3').verbose();

class AuditTrail {
    constructor() {
        // Setup logging
        this.logFile = path.join('/Logs', `audit_trail_${new Date().toISOString().split('T')[0]}.log`);

        // Database for audit records
        this.dbPath = path.join('/Data', 'audit_trail.db');
        this.setupDatabase();

        // Event types that require auditing
        this.auditEventTypes = [
            'communication_logged',
            'communication_retrieved',
            'communication_modified',
            'communication_deleted',
            'access_granted',
            'access_denied',
            'login_success',
            'login_failure',
            'permission_change',
            'configuration_change',
            'export_action',
            'backup_created',
            'backup_restored',
            'system_alert'
        ];

        // Sensitivity levels
        this.sensitivityLevels = {
            'public': 1,
            'internal': 2,
            'confidential': 3,
            'restricted': 4
        };
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
     * Setup database for audit records
     */
    setupDatabase() {
        this.db = new sqlite3.Database(this.dbPath);

        // Create audit trail table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS audit_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                user_id TEXT,
                session_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                resource_type TEXT,
                resource_id TEXT,
                action TEXT,
                details TEXT,
                sensitivity_level TEXT DEFAULT 'internal',
                status TEXT DEFAULT 'success',
                metadata TEXT,
                signature TEXT
            )
        `);

        // Create indexes for performance
        this.db.run('CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_trail(timestamp)');
        this.db.run('CREATE INDEX IF NOT EXISTS idx_event_type ON audit_trail(event_type)');
        this.db.run('CREATE INDEX IF NOT EXISTS idx_user_id ON audit_trail(user_id)');
        this.db.run('CREATE INDEX IF NOT EXISTS idx_resource_id ON audit_trail(resource_id)');

        // Create access log table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_event_id INTEGER,
                resource_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                access_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                access_type TEXT NOT NULL,
                purpose TEXT,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (audit_event_id) REFERENCES audit_trail(id)
            )
        `);
    }

    /**
     * Generate a unique event ID
     */
    generateEventId(eventType, userId, resourceId) {
        const timestamp = Date.now().toString();
        const combined = `${eventType}:${userId}:${resourceId}:${timestamp}`;
        return crypto.createHash('sha256').update(combined).digest('hex').substring(0, 32);
    }

    /**
     * Log an audit event
     */
    logEvent(eventType, userId, resourceType, resourceId, action, details, options = {}) {
        try {
            if (!this.auditEventTypes.includes(eventType)) {
                throw new Error(`Invalid audit event type: ${eventType}`);
            }

            const eventId = this.generateEventId(eventType, userId, resourceId);
            const timestamp = new Date().toISOString();
            const {
                ip_address = null,
                user_agent = null,
                sensitivity_level = 'internal',
                status = 'success',
                metadata = {},
                session_id = null
            } = options;

            // Create event record
            const eventRecord = {
                event_id: eventId,
                timestamp,
                event_type: eventType,
                user_id: userId,
                session_id,
                ip_address,
                user_agent,
                resource_type: resourceType,
                resource_id: resourceId,
                action,
                details: typeof details === 'object' ? JSON.stringify(details) : details,
                sensitivity_level,
                status,
                metadata: JSON.stringify(metadata)
            };

            // Create digital signature for integrity
            const signature = this.createSignature(eventRecord);
            eventRecord.signature = signature;

            // Insert into database
            const stmt = this.db.prepare(`
                INSERT INTO audit_trail (
                    event_id, timestamp, event_type, user_id, session_id, ip_address, user_agent,
                    resource_type, resource_id, action, details, sensitivity_level, status, metadata, signature
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `);

            stmt.run([
                eventRecord.event_id,
                eventRecord.timestamp,
                eventRecord.event_type,
                eventRecord.user_id,
                eventRecord.session_id,
                eventRecord.ip_address,
                eventRecord.user_agent,
                eventRecord.resource_type,
                eventRecord.resource_id,
                eventRecord.action,
                eventRecord.details,
                eventRecord.sensitivity_level,
                eventRecord.status,
                eventRecord.metadata,
                eventRecord.signature
            ]);

            stmt.finalize();

            this.log('INFO', `Audit event logged: ${eventId} (${eventType})`);
            return eventId;

        } catch (error) {
            this.log('ERROR', `Failed to log audit event: ${error.message}`);
            throw error;
        }
    }

    /**
     * Create a digital signature for audit integrity
     */
    createSignature(record) {
        const dataToSign = [
            record.event_id,
            record.timestamp,
            record.event_type,
            record.user_id,
            record.resource_id,
            record.action,
            record.details
        ].join('|');

        const secret = process.env.AUDIT_SIGNATURE_SECRET || 'default-secret-key';
        return crypto.createHmac('sha256', secret).update(dataToSign).digest('hex');
    }

    /**
     * Verify the integrity of an audit record
     */
    verifySignature(record) {
        const expectedSignature = this.createSignature(record);
        return record.signature === expectedSignature;
    }

    /**
     * Log access to a resource
     */
    logAccess(resourceId, userId, accessType, purpose, options = {}) {
        const {
            ip_address = null,
            user_agent = null,
            session_id = null
        } = options;

        // First, create the main audit event
        const eventId = this.logEvent(
            'access_granted',
            userId,
            'communication',
            resourceId,
            accessType,
            `Access granted to resource ${resourceId}`,
            { ip_address, user_agent, session_id }
        );

        // Then, create the access log record
        const stmt = this.db.prepare(`
            INSERT INTO access_log (
                audit_event_id, resource_id, user_id, access_type, purpose, ip_address, user_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        `);

        stmt.run([eventId, resourceId, userId, accessType, purpose, ip_address, user_agent]);
        stmt.finalize();

        this.log('INFO', `Access logged for user ${userId} to resource ${resourceId}`);
        return eventId;
    }

    /**
     * Search audit events
     */
    searchEvents(searchParams = {}) {
        try {
            let query = 'SELECT * FROM audit_trail WHERE 1=1';
            const params = [];

            if (searchParams.eventType) {
                query += ' AND event_type = ?';
                params.push(searchParams.eventType);
            }

            if (searchParams.userId) {
                query += ' AND user_id = ?';
                params.push(searchParams.userId);
            }

            if (searchParams.resourceId) {
                query += ' AND resource_id = ?';
                params.push(searchParams.resourceId);
            }

            if (searchParams.dateFrom) {
                query += ' AND timestamp >= ?';
                params.push(searchParams.dateFrom.toISOString());
            }

            if (searchParams.dateTo) {
                query += ' AND timestamp <= ?';
                params.push(searchParams.dateTo.toISOString());
            }

            if (searchParams.sensitivityLevel) {
                query += ' AND sensitivity_level = ?';
                params.push(searchParams.sensitivityLevel);
            }

            if (searchParams.status) {
                query += ' AND status = ?';
                params.push(searchParams.status);
            }

            query += ' ORDER BY timestamp DESC';

            if (searchParams.limit) {
                query += ' LIMIT ?';
                params.push(searchParams.limit);
            }

            const stmt = this.db.prepare(query);
            const results = stmt.all(params);
            stmt.finalize();

            return results;

        } catch (error) {
            this.log('ERROR', `Failed to search audit events: ${error.message}`);
            throw error;
        }
    }

    /**
     * Get audit statistics
     */
    getStatistics() {
        try {
            const stats = {};

            // Total events
            this.db.each('SELECT COUNT(*) as total FROM audit_trail', (err, row) => {
                if (err) throw err;
                stats.total_events = row.total;
            });

            // Events by type
            stats.by_type = {};
            this.db.each('SELECT event_type, COUNT(*) as count FROM audit_trail GROUP BY event_type', (err, row) => {
                if (err) throw err;
                stats.by_type[row.event_type] = row.count;
            });

            // Events by user
            stats.by_user = {};
            this.db.each('SELECT user_id, COUNT(*) as count FROM audit_trail GROUP BY user_id LIMIT 10', (err, row) => {
                if (err) throw err;
                stats.by_user[row.user_id] = row.count;
            });

            // Events by sensitivity
            stats.by_sensitivity = {};
            this.db.each('SELECT sensitivity_level, COUNT(*) as count FROM audit_trail GROUP BY sensitivity_level', (err, row) => {
                if (err) throw err;
                stats.by_sensitivity[row.sensitivity_level] = row.count;
            });

            // Recent events
            stats.recent_events = [];
            this.db.each('SELECT * FROM audit_trail ORDER BY timestamp DESC LIMIT 10', (err, row) => {
                if (err) throw err;
                stats.recent_events.push(row);
            });

            return stats;

        } catch (error) {
            this.log('ERROR', `Failed to get audit statistics: ${error.message}`);
            throw error;
        }
    }

    /**
     * Generate audit report
     */
    generateReport(reportType, startDate, endDate, options = {}) {
        try {
            const report = {
                report_type: reportType,
                generated_at: new Date().toISOString(),
                date_range: { start: startDate.toISOString(), end: endDate.toISOString() },
                data: {}
            };

            switch (reportType) {
                case 'access_summary':
                    report.data = this.getAccessSummary(startDate, endDate);
                    break;
                case 'user_activity':
                    report.data = this.getUserActivityReport(startDate, endDate, options.userId);
                    break;
                case 'sensitive_access':
                    report.data = this.getSensitiveAccessReport(startDate, endDate);
                    break;
                case 'compliance':
                    report.data = this.getComplianceReport(startDate, endDate);
                    break;
                default:
                    throw new Error(`Unknown report type: ${reportType}`);
            }

            // Create report directory if it doesn't exist
            const reportDir = path.join('/Reports', 'audit');
            if (!fs.existsSync(reportDir)) {
                fs.mkdirSync(reportDir, { recursive: true });
            }

            // Generate filename
            const filename = `audit_report_${reportType}_${startDate.toISOString().split('T')[0]}_to_${endDate.toISOString().split('T')[0]}.json`;
            const filepath = path.join(reportDir, filename);

            // Write report
            fs.writeFileSync(filepath, JSON.stringify(report, null, 2));

            this.log('INFO', `Audit report generated: ${filepath}`);
            return filepath;

        } catch (error) {
            this.log('ERROR', `Failed to generate audit report: ${error.message}`);
            throw error;
        }
    }

    /**
     * Get access summary for a date range
     */
    getAccessSummary(startDate, endDate) {
        const query = `
            SELECT
                user_id,
                COUNT(*) as total_accesses,
                COUNT(CASE WHEN event_type = 'communication_retrieved' THEN 1 END) as retrievals,
                COUNT(CASE WHEN event_type = 'communication_modified' THEN 1 END) as modifications,
                COUNT(CASE WHEN event_type = 'communication_deleted' THEN 1 END) as deletions
            FROM audit_trail
            WHERE timestamp BETWEEN ? AND ?
            AND event_type IN ('communication_retrieved', 'communication_modified', 'communication_deleted')
            GROUP BY user_id
            ORDER BY total_accesses DESC
        `;

        const stmt = this.db.prepare(query);
        const results = stmt.all([startDate.toISOString(), endDate.toISOString()]);
        stmt.finalize();

        return results;
    }

    /**
     * Get user activity report
     */
    getUserActivityReport(startDate, endDate, userId = null) {
        let query = `
            SELECT
                event_type,
                COUNT(*) as event_count,
                MIN(timestamp) as first_event,
                MAX(timestamp) as last_event
            FROM audit_trail
            WHERE timestamp BETWEEN ? AND ?
        `;
        const params = [startDate.toISOString(), endDate.toISOString()];

        if (userId) {
            query += ' AND user_id = ?';
            params.push(userId);
        }

        query += ' GROUP BY event_type ORDER BY event_count DESC';

        const stmt = this.db.prepare(query);
        const results = stmt.all(params);
        stmt.finalize();

        return results;
    }

    /**
     * Get sensitive access report
     */
    getSensitiveAccessReport(startDate, endDate) {
        const query = `
            SELECT
                user_id,
                resource_id,
                event_type,
                timestamp,
                details
            FROM audit_trail
            WHERE timestamp BETWEEN ? AND ?
            AND sensitivity_level IN ('confidential', 'restricted')
            ORDER BY timestamp DESC
        `;

        const stmt = this.db.prepare(query);
        const results = stmt.all([startDate.toISOString(), endDate.toISOString()]);
        stmt.finalize();

        return results;
    }

    /**
     * Get compliance report
     */
    getComplianceReport(startDate, endDate) {
        const report = {};

        // Count access to confidential/restricted data
        const sensitiveQuery = `
            SELECT
                user_id,
                COUNT(*) as sensitive_accesses
            FROM audit_trail
            WHERE timestamp BETWEEN ? AND ?
            AND sensitivity_level IN ('confidential', 'restricted')
            GROUP BY user_id
            HAVING COUNT(*) > 10  -- Threshold for review
        `;

        const sensitiveStmt = this.db.prepare(sensitiveQuery);
        report.high_volume_sensitive_access = sensitiveStmt.all([startDate.toISOString(), endDate.toISOString()]);
        sensitiveStmt.finalize();

        // Count after-hours access
        const offHoursQuery = `
            SELECT
                user_id,
                COUNT(*) as off_hours_accesses
            FROM audit_trail
            WHERE timestamp BETWEEN ? AND ?
            AND CAST(strftime('%H', timestamp) AS INTEGER) NOT BETWEEN 8 AND 18
            GROUP BY user_id
            HAVING COUNT(*) > 5  -- Threshold for review
        `;

        const offHoursStmt = this.db.prepare(offHoursQuery);
        report.after_hours_access = offHoursStmt.all([startDate.toISOString(), endDate.toISOString()]);
        offHoursStmt.finalize();

        return report;
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

module.exports = AuditTrail;

// Example usage
if (require.main === module) {
    const auditTrail = new AuditTrail();

    // Example: Log a communication access event
    const eventId = auditTrail.logEvent(
        'communication_retrieved',
        'user123',
        'communication',
        'comm_abc123',
        'read',
        'User retrieved communication record',
        {
            ip_address: '192.168.1.100',
            user_agent: 'Mozilla/5.0...',
            sensitivity_level: 'confidential',
            session_id: 'sess_xyz789'
        }
    );

    console.log(`Audit event logged with ID: ${eventId}`);

    // Example: Log access to a resource
    auditTrail.logAccess('comm_abc123', 'user123', 'view', 'Business review');

    // Example: Search events
    const searchResults = auditTrail.searchEvents({
        userId: 'user123',
        dateFrom: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)  // Last 7 days
    });
    console.log(`Found ${searchResults.length} events for user123`);

    // Example: Get statistics
    const stats = auditTrail.getStatistics();
    console.log('Audit statistics:', stats);

    // Example: Generate a report
    const reportPath = auditTrail.generateReport(
        'access_summary',
        new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),  // 30 days ago
        new Date()
    );
    console.log(`Report generated at: ${reportPath}`);

    // Close database connection
    auditTrail.close();
}