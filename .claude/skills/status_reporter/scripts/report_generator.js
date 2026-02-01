/**
 * StatusReporterJS: JavaScript module for generating regular status reports for projects, teams, and business metrics.
 *
 * This module provides automated status reporting capabilities with customizable
 * templates, distribution options, and integration with various data sources.
 */

const fs = require('fs').promises;
const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const nodemailer = require('nodemailer'); // Assuming nodemailer is available
const puppeteer = require('puppeteer'); // For PDF generation if needed

// Report types
const ReportType = {
    DAILY: "daily",
    WEEKLY: "weekly",
    MONTHLY: "monthly",
    QUARTERLY: "quarterly",
    PROJECT: "project",
    TEAM: "team",
    BUSINESS: "business"
};

// Report formats
const ReportFormat = {
    EMAIL: "email",
    PDF: "pdf",
    HTML: "html",
    CSV: "csv",
    JSON: "json"
};

class StatusReport {
    constructor(options = {}) {
        this.id = options.id || this.generateId();
        this.title = options.title || 'Untitled Report';
        this.reportType = options.reportType || ReportType.WEEKLY;
        this.periodStart = options.periodStart || new Date();
        this.periodEnd = options.periodEnd || new Date();
        this.createdAt = options.createdAt || new Date();
        this.content = options.content || '';
        this.recipients = options.recipients || [];
        this.status = options.status || 'draft'; // draft, pending, sent, failed
        this.formatType = options.formatType || ReportFormat.EMAIL;
        this.metadata = options.metadata || {};
        this.charts = options.charts || []; // Base64 encoded chart images
    }

    generateId() {
        return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    }
}

class ReportTemplate {
    constructor(options = {}) {
        this.id = options.id || this.generateId();
        this.name = options.name || 'Untitled Template';
        this.reportType = options.reportType || ReportType.WEEKLY;
        this.contentTemplate = options.contentTemplate || '';
        this.variables = options.variables || [];
        this.createdAt = options.createdAt || new Date();
        this.isActive = options.isActive !== undefined ? options.isActive : true;
    }

    generateId() {
        return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    }
}

class StatusReporterJS {
    /**
     * Creates a new StatusReporterJS instance
     * @param {string} dbPath - Path to the SQLite database file
     * @param {Object} smtpConfig - SMTP configuration for email delivery
     */
    constructor(dbPath = './reports.db', smtpConfig = {}) {
        this.dbPath = dbPath;
        this.smtpConfig = smtpConfig;
        this.db = null;
        this.setupDatabase();

        // Configure logging
        this.logger = console;
    }

    /**
     * Sets up the database schema for report tracking
     */
    setupDatabase() {
        this.db = new sqlite3.Database(this.dbPath);

        // Create reports table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                report_type TEXT,
                period_start DATETIME,
                period_end DATETIME,
                created_at DATETIME,
                content TEXT,
                recipients_json TEXT,
                status TEXT,
                format_type TEXT,
                metadata_json TEXT,
                charts_json TEXT
            )
        `);

        // Create templates table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                report_type TEXT,
                content_template TEXT,
                variables_json TEXT,
                created_at DATETIME,
                is_active BOOLEAN
            )
        `);

        // Create metrics table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT,
                metric_name TEXT,
                metric_value REAL,
                unit TEXT,
                recorded_at DATETIME,
                FOREIGN KEY (report_id) REFERENCES reports (id)
            )
        `);

        // Create distribution_log table
        this.db.run(`
            CREATE TABLE IF NOT EXISTS distribution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT,
                recipient TEXT,
                status TEXT,
                sent_at DATETIME,
                error_message TEXT,
                FOREIGN KEY (report_id) REFERENCES reports (id)
            )
        `);
    }

    /**
     * Creates a new status report
     * @param {string} title - Report title
     * @param {string} reportType - Report type
     * @param {Date} periodStart - Start of reporting period
     * @param {Date} periodEnd - End of reporting period
     * @param {string[]} recipients - List of recipients
     * @param {string} content - Report content
     * @param {string} formatType - Report format
     * @param {Object} metadata - Additional metadata
     * @returns {Promise<string>} The ID of the created report
     */
    async createReport(title, reportType, periodStart, periodEnd, recipients,
                     content = '', formatType = ReportFormat.EMAIL, metadata = {}) {
        const report = new StatusReport({
            title,
            reportType,
            periodStart,
            periodEnd,
            recipients,
            content,
            formatType,
            metadata,
            status: 'draft'
        });

        await this.saveReportToDb(report);
        this.logger.info(`Created report '${title}' (ID: ${report.id})`);
        return report.id;
    }

    /**
     * Saves a report to the database
     * @param {StatusReport} report - The report to save
     * @returns {Promise<void>}
     */
    async saveReportToDb(report) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT INTO reports
                (id, title, report_type, period_start, period_end, created_at,
                 content, recipients_json, status, format_type, metadata_json, charts_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `);

            stmt.run([
                report.id, report.title, report.reportType,
                report.periodStart.toISOString(), report.periodEnd.toISOString(),
                report.createdAt.toISOString(), report.content,
                JSON.stringify(report.recipients), report.status, report.formatType,
                JSON.stringify(report.metadata), JSON.stringify(report.charts)
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
     * Generates report content using a template and variables
     * @param {string} reportId - The ID of the report
     * @param {string} templateId - Optional template ID to use
     * @param {Object} variables - Variables to substitute in the template
     * @returns {Promise<string>} The generated content
     */
    async generateReportContent(reportId, templateId = null, variables = {}) {
        const report = await this.getReport(reportId);
        if (!report) {
            throw new Error(`Report with ID ${reportId} not found`);
        }

        // Use provided template or find a default template for this report type
        let template;
        if (templateId) {
            template = await this.getTemplate(templateId);
        } else {
            template = await this.getDefaultTemplate(report.reportType);
        }

        if (!template) {
            throw new Error(`No template found for report type ${report.reportType}`);
        }

        // Prepare template variables
        const defaultVars = {
            title: report.title,
            reportType: report.reportType,
            periodStart: report.periodStart.toLocaleDateString(),
            periodEnd: report.periodEnd.toLocaleDateString(),
            currentDate: new Date().toLocaleDateString(),
            durationDays: Math.ceil((report.periodEnd - report.periodStart) / (1000 * 60 * 60 * 24))
        };

        // Merge provided variables with defaults (provided variables take precedence)
        const allVars = { ...defaultVars, ...variables };

        // Replace template variables
        let content = template.contentTemplate;
        for (const [varName, varValue] of Object.entries(allVars)) {
            const placeholder = `{{${varName}}}`;
            content = content.replace(new RegExp(placeholder, 'g'), varValue.toString());
        }

        // Add any dynamic content based on report type
        content = await this.addDynamicContent(content, report, allVars);

        report.content = content;
        report.status = 'pending'; // Ready for distribution

        await this.saveReportToDb(report);
        this.logger.info(`Generated content for report '${report.title}' (ID: ${report.id})`);
        return content;
    }

    /**
     * Adds dynamic content based on report type and variables
     * @param {string} content - Original content
     * @param {StatusReport} report - The report object
     * @param {Object} variables - Template variables
     * @returns {Promise<string>} Content with dynamic additions
     */
    async addDynamicContent(content, report, variables) {
        // Add metrics if they exist
        const metrics = await this.getReportMetrics(report.id);
        if (metrics.length > 0) {
            let metricsSection = "\\n## Key Metrics\\n";
            for (const metric of metrics) {
                metricsSection += `- ${metric.name}: ${metric.value} ${metric.unit}\\n`;
            }
            content += metricsSection;
        }

        // Add charts if they exist
        if (report.charts && report.charts.length > 0) {
            content += "\\n## Charts\\n";
            for (let i = 0; i < report.charts.length; i++) {
                content += `<img src="data:image/png;base64,${report.charts[i]}" alt="Chart ${i+1}">\\n`;
            }
        }

        // Customize based on report type
        if (report.reportType === ReportType.DAILY) {
            content += `\\n## Tomorrow's Priorities\\n${variables.nextPriorities || 'To be determined'}\\n`;
            content += `\\n## Blockers\\n${variables.blockers || 'None identified'}\\n`;
        } else if (report.reportType === ReportType.WEEKLY) {
            content += `\\n## This Week's Accomplishments\\n${variables.accomplishments || 'None reported'}\\n`;
            content += `\\n## Next Week's Focus\\n${variables.nextFocus || 'To be planned'}\\n`;
        } else if (report.reportType === ReportType.PROJECT) {
            content += `\\n## Milestone Progress\\n${variables.milestoneProgress || 'Not specified'}\\n`;
            content += `\\n## Resource Allocation\\n${variables.resources || 'Not specified'}\\n`;
        } else if (report.reportType === ReportType.BUSINESS) {
            content += `\\n## Financial Summary\\n${variables.financialSummary || 'Not specified'}\\n`;
            content += `\\n## Market Insights\\n${variables.marketInsights || 'Not specified'}\\n`;
        }

        return content;
    }

    /**
     * Creates a new report template
     * @param {string} name - Template name
     * @param {string} reportType - Report type
     * @param {string} contentTemplate - Template content with placeholders
     * @param {string[]} variables - List of variables in the template
     * @returns {Promise<string>} The ID of the created template
     */
    async createTemplate(name, reportType, contentTemplate, variables) {
        const template = new ReportTemplate({
            name,
            reportType,
            contentTemplate,
            variables
        });

        await this.saveTemplateToDb(template);
        this.logger.info(`Created template '${name}' for report type ${reportType}`);
        return template.id;
    }

    /**
     * Saves a template to the database
     * @param {ReportTemplate} template - The template to save
     * @returns {Promise<void>}
     */
    async saveTemplateToDb(template) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT INTO templates
                (id, name, report_type, content_template, variables_json, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            `);

            stmt.run([
                template.id, template.name, template.reportType,
                template.contentTemplate, JSON.stringify(template.variables),
                template.createdAt.toISOString(), template.isActive
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
     * Retrieves a template by ID
     * @param {string} templateId - The ID of the template
     * @returns {Promise<ReportTemplate|null>} The template or null if not found
     */
    async getTemplate(templateId) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                SELECT id, name, report_type, content_template, variables_json, created_at, is_active
                FROM templates WHERE id = ?
            `);

            stmt.get([templateId], (err, row) => {
                if (err) {
                    reject(err);
                    return;
                }

                if (!row) {
                    resolve(null);
                    return;
                }

                resolve(new ReportTemplate({
                    id: row.id,
                    name: row.name,
                    reportType: row.report_type,
                    contentTemplate: row.content_template,
                    variables: JSON.parse(row.variables_json || '[]'),
                    createdAt: new Date(row.created_at),
                    isActive: row.is_active
                }));
            });

            stmt.finalize();
        });
    }

    /**
     * Gets a default template for a report type
     * @param {string} reportType - The report type
     * @returns {Promise<ReportTemplate|null>} The default template or null if not found
     */
    async getDefaultTemplate(reportType) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                SELECT id, name, report_type, content_template, variables_json, created_at, is_active
                FROM templates WHERE report_type = ? AND is_active = 1
                ORDER BY created_at DESC LIMIT 1
            `);

            stmt.get([reportType], (err, row) => {
                if (err) {
                    reject(err);
                    return;
                }

                if (!row) {
                    resolve(null);
                    return;
                }

                resolve(new ReportTemplate({
                    id: row.id,
                    name: row.name,
                    reportType: row.report_type,
                    contentTemplate: row.content_template,
                    variables: JSON.parse(row.variables_json || '[]'),
                    createdAt: new Date(row.created_at),
                    isActive: row.is_active
                }));
            });

            stmt.finalize();
        });
    }

    /**
     * Retrieves a report by ID
     * @param {string} reportId - The ID of the report
     * @returns {Promise<StatusReport|null>} The report or null if not found
     */
    async getReport(reportId) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                SELECT id, title, report_type, period_start, period_end, created_at,
                       content, recipients_json, status, format_type, metadata_json, charts_json
                FROM reports WHERE id = ?
            `);

            stmt.get([reportId], (err, row) => {
                if (err) {
                    reject(err);
                    return;
                }

                if (!row) {
                    resolve(null);
                    return;
                }

                resolve(new StatusReport({
                    id: row.id,
                    title: row.title,
                    reportType: row.report_type,
                    periodStart: new Date(row.period_start),
                    periodEnd: new Date(row.period_end),
                    createdAt: new Date(row.created_at),
                    content: row.content,
                    recipients: JSON.parse(row.recipients_json || '[]'),
                    status: row.status,
                    formatType: row.format_type,
                    metadata: JSON.parse(row.metadata_json || '{}'),
                    charts: JSON.parse(row.charts_json || '[]')
                }));
            });

            stmt.finalize();
        });
    }

    /**
     * Distributes a report to its recipients
     * @param {string} reportId - The ID of the report
     * @returns {Promise<boolean>} Whether the distribution was successful
     */
    async distributeReport(reportId) {
        const report = await this.getReport(reportId);
        if (!report || report.status !== 'pending') {
            this.logger.error(`Report ${reportId} not found or not ready for distribution`);
            return false;
        }

        let success = true;
        for (const recipient of report.recipients) {
            try {
                let sent;
                if (report.formatType === ReportFormat.EMAIL) {
                    sent = await this.sendEmailReport(report, recipient);
                } else if (report.formatType === ReportFormat.HTML) {
                    sent = await this.saveHtmlReport(report, recipient);
                } else if (report.formatType === ReportFormat.PDF) {
                    sent = await this.savePdfReport(report, recipient);
                } else if (report.formatType === ReportFormat.CSV) {
                    sent = await this.saveCsvReport(report, recipient);
                } else if (report.formatType === ReportFormat.JSON) {
                    sent = await this.saveJsonReport(report, recipient);
                } else {
                    this.logger.error(`Unsupported format: ${report.formatType}`);
                    sent = false;
                }

                // Log distribution result
                await this.logDistributionResult(reportId, recipient, sent ? 'sent' : 'failed');

                if (!sent) {
                    success = false;
                    this.logger.error(`Failed to distribute report to ${recipient}`);
                }
            } catch (e) {
                this.logger.error(`Error distributing report to ${recipient}: ${e.message}`);
                await this.logDistributionResult(reportId, recipient, 'failed', e.message);
                success = false;
            }
        }

        if (success) {
            // Update report status to indicate it was sent
            await this.updateReportStatus(reportId, 'sent');
            this.logger.info(`Distributed report '${report.title}' to ${report.recipients.length} recipients`);
        } else {
            await this.updateReportStatus(reportId, 'failed');
            this.logger.error(`Failed to fully distribute report '${report.title}'`);
        }

        return success;
    }

    /**
     * Sends a report via email
     * @param {StatusReport} report - The report to send
     * @param {string} recipient - The recipient's email address
     * @returns {Promise<boolean>} Whether the email was sent successfully
     */
    async sendEmailReport(report, recipient) {
        if (!this.smtpConfig || !this.smtpConfig.host) {
            this.logger.error("SMTP configuration not provided");
            return false;
        }

        try {
            const transporter = nodemailer.createTransporter({
                host: this.smtpConfig.host,
                port: this.smtpConfig.port || 587,
                secure: this.smtpConfig.secure || false,
                auth: {
                    user: this.smtpConfig.auth.user,
                    pass: this.smtpConfig.auth.pass
                }
            });

            const mailOptions = {
                from: this.smtpConfig.from || 'noreply@example.com',
                to: recipient,
                subject: `Status Report: ${report.title}`,
                html: `
                    <html>
                    <head>
                        <style>
                            body { font-family: Arial, sans-serif; }
                            h1, h2 { color: #333; }
                            .section { margin: 20px 0; }
                            .metric { background-color: #f5f5f5; padding: 10px; border-radius: 5px; }
                        </style>
                    </head>
                    <body>
                        <h1>${report.title}</h1>
                        <p><strong>Reporting Period:</strong> ${report.periodStart.toLocaleDateString()} to ${report.periodEnd.toLocaleDateString()}</p>

                        ${report.content}

                        <hr>
                        <p><em>This report was automatically generated by StatusReporter</em></p>
                    </body>
                    </html>
                `
            };

            await transporter.sendMail(mailOptions);
            return true;
        } catch (e) {
            this.logger.error(`Failed to send email: ${e.message}`);
            return false;
        }
    }

    /**
     * Saves a report as HTML file
     * @param {StatusReport} report - The report to save
     * @param {string} recipient - The recipient identifier
     * @returns {Promise<boolean>} Whether the file was saved successfully
     */
    async saveHtmlReport(report, recipient) {
        try {
            const htmlContent = `
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Status Report: ${report.title}</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; }
                        h1, h2 { color: #333; }
                        .section { margin: 20px 0; }
                        .metric { background-color: #f5f5f5; padding: 10px; border-radius: 5px; }
                        table { border-collapse: collapse; width: 100%; }
                        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                        th { background-color: #f2f2f2; }
                    </style>
                </head>
                <body>
                    <h1>${report.title}</h1>
                    <p><strong>Reporting Period:</strong> ${report.periodStart.toLocaleDateString()} to ${report.periodEnd.toLocaleDateString()}</p>

                    ${report.content}

                    <hr>
                    <p><em>This report was automatically generated by StatusReporter</em></p>
                </body>
                </html>
            `;

            const filename = `report_${report.id}_${report.periodStart.toISOString().substring(0, 10)}_${recipient.replace('@', '_at_').replace('.', '_dot_')}.html`;
            const filepath = path.join(await this.getOutputDir(), filename);

            await fs.writeFile(filepath, htmlContent, 'utf8');
            this.logger.info(`Saved HTML report to ${filepath}`);
            return true;
        } catch (e) {
            this.logger.error(`Failed to save HTML report: ${e.message}`);
            return false;
        }
    }

    /**
     * Saves a report as PDF file
     * @param {StatusReport} report - The report to save
     * @param {string} recipient - The recipient identifier
     * @returns {Promise<boolean>} Whether the file was saved successfully
     */
    async savePdfReport(report, recipient) {
        try {
            // For simplicity, we'll create a text file that could be converted to PDF
            // In a real implementation, this would use a library like Puppeteer
            const content = `
STATUS REPORT: ${report.title}
Reporting Period: ${report.periodStart.toLocaleDateString()} to ${report.periodEnd.toLocaleDateString()}

${report.content}

This report was automatically generated by StatusReporter
`;

            const filename = `report_${report.id}_${report.periodStart.toISOString().substring(0, 10)}_${recipient.replace('@', '_at_').replace('.', '_dot_')}.txt`;
            const filepath = path.join(await this.getOutputDir(), filename);

            await fs.writeFile(filepath, content, 'utf8');
            this.logger.info(`Saved PDF-ready report to ${filepath}`);
            return true;
        } catch (e) {
            this.logger.error(`Failed to save PDF report: ${e.message}`);
            return false;
        }
    }

    /**
     * Saves report metrics as CSV file
     * @param {StatusReport} report - The report to save
     * @param {string} recipient - The recipient identifier
     * @returns {Promise<boolean>} Whether the file was saved successfully
     */
    async saveCsvReport(report, recipient) {
        try {
            const metrics = await this.getReportMetrics(report.id);
            if (metrics.length === 0) {
                this.logger.warning(`No metrics found for report ${report.id}`);
                return true;
            }

            let csvContent = 'metric_name,value,unit,recorded_at\\n';
            for (const metric of metrics) {
                csvContent += `${metric.name},${metric.value},"${metric.unit}",${metric.recordedAt}\\n`;
            }

            const filename = `report_metrics_${report.id}_${report.periodStart.toISOString().substring(0, 10)}_${recipient.replace('@', '_at_').replace('.', '_dot_')}.csv`;
            const filepath = path.join(await this.getOutputDir(), filename);

            await fs.writeFile(filepath, csvContent, 'utf8');
            this.logger.info(`Saved CSV report to ${filepath}`);
            return true;
        } catch (e) {
            this.logger.error(`Failed to save CSV report: ${e.message}`);
            return false;
        }
    }

    /**
     * Saves report as JSON file
     * @param {StatusReport} report - The report to save
     * @param {string} recipient - The recipient identifier
     * @returns {Promise<boolean>} Whether the file was saved successfully
     */
    async saveJsonReport(report, recipient) {
        try {
            const reportData = {
                id: report.id,
                title: report.title,
                reportType: report.reportType,
                periodStart: report.periodStart.toISOString(),
                periodEnd: report.periodEnd.toISOString(),
                createdAt: report.createdAt.toISOString(),
                content: report.content,
                recipients: report.recipients,
                status: report.status,
                formatType: report.formatType,
                metadata: report.metadata,
                chartsCount: report.charts ? report.charts.length : 0,
                metrics: await this.getReportMetrics(report.id)
            };

            const filename = `report_${report.id}_${report.periodStart.toISOString().substring(0, 10)}_${recipient.replace('@', '_at_').replace('.', '_dot_')}.json`;
            const filepath = path.join(await this.getOutputDir(), filename);

            await fs.writeFile(filepath, JSON.stringify(reportData, null, 2), 'utf8');
            this.logger.info(`Saved JSON report to ${filepath}`);
            return true;
        } catch (e) {
            this.logger.error(`Failed to save JSON report: ${e.message}`);
            return false;
        }
    }

    /**
     * Gets the output directory for reports
     * @returns {Promise<string>} The output directory path
     */
    async getOutputDir() {
        const outputDir = 'output_reports';
        try {
            await fs.access(outputDir);
        } catch {
            await fs.mkdir(outputDir, { recursive: true });
        }
        return outputDir;
    }

    /**
     * Logs the result of report distribution
     * @param {string} reportId - The report ID
     * @param {string} recipient - The recipient
     * @param {string} status - The distribution status
     * @param {string} errorMsg - Optional error message
     * @returns {Promise<void>}
     */
    async logDistributionResult(reportId, recipient, status, errorMsg = '') {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT INTO distribution_log
                (report_id, recipient, status, sent_at, error_message)
                VALUES (?, ?, ?, ?, ?)
            `);

            stmt.run([reportId, recipient, status, new Date().toISOString(), errorMsg], function(err) {
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
     * Updates the status of a report
     * @param {string} reportId - The report ID
     * @param {string} status - The new status
     * @returns {Promise<void>}
     */
    async updateReportStatus(reportId, status) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                UPDATE reports SET status = ?, updated_at = ?
                WHERE id = ?
            `);

            stmt.run([status, new Date().toISOString(), reportId], function(err) {
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
     * Adds a metric to a report
     * @param {string} reportId - The report ID
     * @param {string} metricName - Name of the metric
     * @param {number} metricValue - Value of the metric
     * @param {string} unit - Unit of measurement
     * @returns {Promise<void>}
     */
    async addReportMetric(reportId, metricName, metricValue, unit = '') {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                INSERT INTO metrics
                (report_id, metric_name, metric_value, unit, recorded_at)
                VALUES (?, ?, ?, ?, ?)
            `);

            stmt.run([reportId, metricName, metricValue, unit, new Date().toISOString()], function(err) {
                if (err) {
                    reject(err);
                } else {
                    console.info(`Added metric '${metricName}' to report ${reportId}`);
                    resolve();
                }
            });

            stmt.finalize();
        });
    }

    /**
     * Gets metrics for a report
     * @param {string} reportId - The report ID
     * @returns {Promise<Object[]>} Array of metrics
     */
    async getReportMetrics(reportId) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                SELECT metric_name, metric_value, unit, recorded_at
                FROM metrics
                WHERE report_id = ?
                ORDER BY recorded_at DESC
            `);

            stmt.all([reportId], (err, rows) => {
                if (err) {
                    reject(err);
                    return;
                }

                const metrics = rows.map(row => ({
                    name: row.metric_name,
                    value: row.metric_value,
                    unit: row.unit,
                    recordedAt: row.recorded_at
                }));

                resolve(metrics);
            });

            stmt.finalize();
        });
    }

    /**
     * Gets historical reports for a given period
     * @param {string} reportType - Optional report type filter
     * @param {number} daysBack - Number of days to look back
     * @returns {Promise<StatusReport[]>} Array of historical reports
     */
    async getHistoricalReports(reportType = null, daysBack = 30) {
        return new Promise(async (resolve, reject) => {
            const cutoffDate = new Date();
            cutoffDate.setDate(cutoffDate.getDate() - daysBack);

            let query = "SELECT id, title, report_type, period_start, period_end, created_at, content, recipients_json, status, format_type, metadata_json, charts_json FROM reports WHERE created_at >= ?";
            const params = [cutoffDate.toISOString()];

            if (reportType) {
                query += " AND report_type = ?";
                params.push(reportType);
            }

            query += " ORDER BY created_at DESC";

            const stmt = this.db.prepare(query);

            stmt.all(params, (err, rows) => {
                if (err) {
                    reject(err);
                    return;
                }

                const reports = rows.map(row => new StatusReport({
                    id: row.id,
                    title: row.title,
                    reportType: row.report_type,
                    periodStart: new Date(row.period_start),
                    periodEnd: new Date(row.period_end),
                    createdAt: new Date(row.created_at),
                    content: row.content,
                    recipients: JSON.parse(row.recipients_json || '[]'),
                    status: row.status,
                    formatType: row.format_type,
                    metadata: JSON.parse(row.metadata_json || '{}'),
                    charts: JSON.parse(row.charts_json || '[]')
                }));

                resolve(reports);
            });

            stmt.finalize();
        });
    }

    /**
     * Gets distribution statistics for a report
     * @param {string} reportId - The report ID
     * @returns {Promise<Object>} Distribution statistics
     */
    async getDistributionStats(reportId) {
        return new Promise((resolve, reject) => {
            const stmt = this.db.prepare(`
                SELECT status, COUNT(*) as count
                FROM distribution_log
                WHERE report_id = ?
                GROUP BY status
            `);

            stmt.all([reportId], (err, rows) => {
                if (err) {
                    reject(err);
                    return;
                }

                const stats = {};
                for (const row of rows) {
                    stats[row.status] = row['COUNT(*)'];
                }

                resolve(stats);
            });

            stmt.finalize();
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

module.exports = StatusReporterJS;

// If running as a standalone script
if (require.main === module) {
    const args = process.argv.slice(2);

    async function main() {
        const reporter = new StatusReporterJS();

        if (args.includes('--demo')) {
            // Create some demo templates
            const dailyTemplate = `
<h2>Daily Standup Report - {{{periodStart}}} to {{{periodEnd}}}</h2>

<h3>What I accomplished yesterday:</h3>
<ul>
<li>Task 1: {{{task1Yesterday}}}</li>
<li>Task 2: {{{task2Yesterday}}}</li>
</ul>

<h3>What I'm working on today:</h3>
<ul>
<li>Priority 1: {{{priority1Today}}}</li>
<li>Priority 2: {{{priority2Today}}}</li>
</ul>

<h3>Blockers/Challenges:</h3>
<ul>
<li>{{{blocker1}}}</li>
<li>{{{blocker2}}}</li>
</ul>

<p>Next priorities: {{{nextPriorities}}}</p>
`;

            const weeklyTemplate = `
<h2>Weekly Status Report - {{{periodStart}}} to {{{periodEnd}}}</h2>

<h3>Key Accomplishments:</h3>
<ul>
<li>{{{accomplishment1}}}</li>
<li>{{{accomplishment2}}}</li>
<li>{{{accomplishment3}}}</li>
</ul>

<h3>Current Priorities:</h3>
<ul>
<li>{{{priority1}}}</li>
<li>{{{priority2}}}</li>
<li>{{{priority3}}}</li>
</ul>

<h3>Risks & Concerns:</h3>
<ul>
<li>{{{risk1}}}</li>
<li>{{{risk2}}}</li>
</ul>

<h3>Next Week's Focus:</h3>
<p>{{{nextWeekFocus}}}</p>
`;

            // Create templates
            const dailyTemplateId = await reporter.createTemplate(
                "Daily Standup",
                ReportType.DAILY,
                dailyTemplate,
                ["task1Yesterday", "task2Yesterday", "priority1Today", "priority2Today",
                 "blocker1", "blocker2", "nextPriorities"]
            );

            const weeklyTemplateId = await reporter.createTemplate(
                "Weekly Status",
                ReportType.WEEKLY,
                weeklyTemplate,
                ["accomplishment1", "accomplishment2", "accomplishment3",
                 "priority1", "priority2", "priority3", "risk1", "risk2", "nextWeekFocus"]
            );

            console.log(`Created templates: Daily (${dailyTemplateId}), Weekly (${weeklyTemplateId})`);

            // Create a demo report
            const reportId = await reporter.createReport(
                "Week of February 1-5, 2026",
                ReportType.WEEKLY,
                new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // 7 days ago
                new Date(),
                ["manager@company.com", "team@company.com"],
                '',
                ReportFormat.EMAIL
            );

            console.log(`Created report: ${reportId}`);

            // Generate content with variables
            const content = await reporter.generateReportContent(
                reportId,
                null, // Use default template
                {
                    accomplishment1: "Completed API integration for customer portal",
                    accomplishment2: "Resolved critical security vulnerability",
                    accomplishment3: "Deployed new analytics dashboard",
                    priority1: "Finish user authentication system",
                    priority2: "Prepare for Q1 planning session",
                    priority3: "Review and refactor legacy code",
                    risk1: "Potential delay in third-party API availability",
                    risk2: "Resource constraint for upcoming sprint",
                    nextWeekFocus: "Focus on authentication system and sprint planning"
                }
            );

            console.log("Generated report content");

            // Add some metrics
            await reporter.addReportMetric(reportId, "Tasks Completed", 12, "tasks");
            await reporter.addReportMetric(reportId, "Bugs Resolved", 5, "bugs");
            await reporter.addReportMetric(reportId, "Hours Worked", 40, "hours");

            console.log("Added metrics to report");

            // Print the generated content
            const report = await reporter.getReport(reportId);
            console.log("\\n--- Generated Report Content ---");
            console.log(report.content);
            console.log("--- End Report Content ---");

            // Get historical reports
            const historical = await reporter.getHistoricalReports(null, 7);
            console.log(`\\nFound ${historical.length} historical reports`);

        } else {
            console.log("Status reporter initialized. Use the API to generate reports.");
        }

        reporter.close();
    }

    main().catch(console.error);
}