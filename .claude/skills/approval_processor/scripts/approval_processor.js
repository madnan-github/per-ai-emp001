/**
 * Approval Processor - JavaScript Implementation
 *
 * This script implements an approval processing system that manages approval workflows
 * for sensitive operations, payments, communications, and other business-critical
 * actions, ensuring appropriate governance and security controls.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const EventEmitter = require('events');
const { spawn } = require('child_process');

class ApprovalStatus {
    static PENDING = 'pending';
    static APPROVED = 'approved';
    static REJECTED = 'rejected';
    static CANCELLED = 'cancelled';
    static ESCALATED = 'escalated';

    static toString(status) {
        switch (status) {
            case ApprovalStatus.PENDING: return 'pending';
            case ApprovalStatus.APPROVED: return 'approved';
            case ApprovalStatus.REJECTED: return 'rejected';
            case ApprovalStatus.CANCELLED: return 'cancelled';
            case ApprovalStatus.ESCALATED: return 'escalated';
            default: return 'unknown';
        }
    }
}

class ApprovalPriority {
    static LOW = 1;
    static NORMAL = 2;
    static HIGH = 3;
    static CRITICAL = 4;

    static toString(priority) {
        switch (priority) {
            case ApprovalPriority.LOW: return 'low';
            case ApprovalPriority.NORMAL: return 'normal';
            case ApprovalPriority.HIGH: return 'high';
            case ApprovalPriority.CRITICAL: return 'critical';
            default: return 'unknown';
        }
    }
}

class ApprovalRequest {
    constructor(options = {}) {
        this.id = options.id || this.generateId();
        this.requestorId = options.requestorId || 'unknown';
        this.requestorName = options.requestorName || 'Unknown';
        this.requestorEmail = options.requestorEmail || '';
        this.approvalType = options.approvalType || 'general';
        this.category = options.category || 'general';
        this.requestDate = options.requestDate || Date.now();
        this.dueDate = options.dueDate || (Date.now() + 7 * 24 * 60 * 60 * 1000); // Default: 1 week
        this.priority = options.priority || ApprovalPriority.NORMAL;
        this.amount = options.amount || 0.0;
        this.currency = options.currency || 'USD';
        this.description = options.description || '';
        this.justification = options.justification || '';
        this.associatedDocuments = options.associatedDocuments || [];
        this.riskLevel = options.riskLevel || 'medium';
        this.currentApproverId = options.currentApproverId || '';
        this.currentApproverName = options.currentApproverName || '';
        this.currentApproverEmail = options.currentApproverEmail || '';
        this.approvalChain = options.approvalChain || [];
        this.currentLevel = options.currentLevel || 0;
        this.status = options.status || ApprovalStatus.PENDING;
        this.createdBy = options.createdBy || 'unknown';
        this.metadata = options.metadata || {};
        this.approvalHistory = options.approvalHistory || [];
        this.cancellationReason = options.cancellationReason || null;
    }

    generateId() {
        const content = `${this.requestorId}:${this.description}:${this.requestDate}`;
        return crypto.createHash('sha256').update(content).digest('hex').substring(0, 16);
    }

    toJSON() {
        return {
            id: this.id,
            requestorId: this.requestorId,
            requestorName: this.requestorName,
            requestorEmail: this.requestorEmail,
            approvalType: this.approvalType,
            category: this.category,
            requestDate: this.requestDate,
            dueDate: this.dueDate,
            priority: this.priority,
            amount: this.amount,
            currency: this.currency,
            description: this.description,
            justification: this.justification,
            associatedDocuments: this.associatedDocuments,
            riskLevel: this.riskLevel,
            currentApproverId: this.currentApproverId,
            currentApproverName: this.currentApproverName,
            currentApproverEmail: this.currentApproverEmail,
            approvalChain: this.approvalChain,
            currentLevel: this.currentLevel,
            status: this.status,
            createdBy: this.createdBy,
            metadata: this.metadata,
            approvalHistory: this.approvalHistory,
            cancellationReason: this.cancellationReason
        };
    }
}

class ApprovalAction {
    constructor(options = {}) {
        this.requestId = options.requestId;
        this.approverId = options.approverId;
        this.approverName = options.approverName;
        this.approverEmail = options.approverEmail;
        this.action = options.action; // 'approve', 'reject', 'request_info', 'escalate'
        this.timestamp = options.timestamp || Date.now();
        this.comments = options.comments || '';
        this.nextApproverId = options.nextApproverId || null;
        this.nextApproverName = options.nextApproverName || null;
        this.nextApproverEmail = options.nextApproverEmail || null;
    }

    toJSON() {
        return {
            requestId: this.requestId,
            approverId: this.approverId,
            approverName: this.approverName,
            approverEmail: this.approverEmail,
            action: this.action,
            timestamp: this.timestamp,
            comments: this.comments,
            nextApproverId: this.nextApproverId,
            nextApproverName: this.nextApproverName,
            nextApproverEmail: this.nextApproverEmail
        };
    }
}

class ApprovalStore {
    constructor(dbPath = './approvals.json') {
        this.dbPath = dbPath;
        this.requests = this.loadRequests();
        this.actions = this.loadActions();
    }

    loadRequests() {
        try {
            if (fs.existsSync(this.dbPath)) {
                const data = fs.readFileSync(this.dbPath, 'utf8');
                return JSON.parse(data).requests || [];
            }
        } catch (error) {
            console.error('Error loading approval requests:', error.message);
        }
        return [];
    }

    loadActions() {
        try {
            if (fs.existsSync(this.dbPath)) {
                const data = fs.readFileSync(this.dbPath, 'utf8');
                return JSON.parse(data).actions || [];
            }
        } catch (error) {
            console.error('Error loading approval actions:', error.message);
        }
        return [];
    }

    saveData() {
        try {
            const data = {
                requests: this.requests,
                actions: this.actions
            };
            fs.writeFileSync(this.dbPath, JSON.stringify(data, null, 2));
        } catch (error) {
            console.error('Error saving approval data:', error.message);
        }
    }

    saveApprovalRequest(request) {
        // Check if request already exists
        const existingIndex = this.requests.findIndex(r => r.id === request.id);

        if (existingIndex !== -1) {
            this.requests[existingIndex] = { ...request.toJSON() };
        } else {
            this.requests.push({ ...request.toJSON() });
        }

        this.saveData();
    }

    saveApprovalAction(action) {
        this.actions.push({ ...action.toJSON() });
        this.saveData();
    }

    getPendingApprovals(approverId) {
        return this.requests
            .filter(r => r.currentApproverId === approverId && r.status === ApprovalStatus.PENDING)
            .sort((a, b) => b.priority - a.priority || a.requestDate - b.requestDate)
            .map(data => new ApprovalRequest(data));
    }

    getApprovalRequest(requestId) {
        const request = this.requests.find(r => r.id === requestId);
        return request ? new ApprovalRequest(request) : null;
    }

    getApprovalHistory(requestId) {
        return this.actions
            .filter(a => a.requestId === requestId)
            .sort((a, b) => a.timestamp - b.timestamp)
            .map(data => new ApprovalAction(data));
    }
}

class ApprovalChainEvaluator {
    constructor(config = {}) {
        this.config = config;
    }

    getInitialApprover(request) {
        // Get approval chains configuration for this category
        const approvalChains = this.config.approvalChains || {};

        // Look up the specific chain for this request type
        if (request.approvalType in approvalChains) {
            const typeChains = approvalChains[request.approvalType];

            if (request.category in typeChains) {
                const categoryChain = typeChains[request.category];

                // Find the appropriate level based on amount/other criteria
                if ('thresholds' in categoryChain) {
                    // Sort thresholds by amount (descending) and find the first one that matches
                    const thresholds = [...categoryChain.thresholds].sort((a, b) => b.amount - a.amount);

                    for (const threshold of thresholds) {
                        if (request.amount >= threshold.amount) {
                            // For simplicity, return the first approver in the first matching level
                            if ('approvers' in threshold && threshold.approvers.length > 0) {
                                // In a real system, you'd have logic to determine actual user IDs
                                // For now, returning a placeholder
                                return {
                                    id: `approver-${threshold.level}`,
                                    name: `Approver Level ${threshold.level}`,
                                    email: `approver${threshold.level}@company.com`
                                };
                            }
                        }
                    }
                }
            }
        }

        // Default fallback approver
        return {
            id: 'default-approver',
            name: 'Default Approver',
            email: 'default@approver.com'
        };
    }

    getNextApprover(request, currentApproverIndex) {
        // For this implementation, we'll just return a placeholder
        // In a real system, you'd have more complex logic based on the approval chain configuration
        if (currentApproverIndex + 1 < request.approvalChain.length) {
            return request.approvalChain[currentApproverIndex + 1];
        }

        return null;
    }
}

class AutoApprovalEvaluator {
    constructor(config = {}) {
        this.config = config;
        this.autoApprovalRules = config.autoApprovalRules?.rules || [];
    }

    shouldAutoApprove(request) {
        for (const rule of this.autoApprovalRules) {
            // Check if all conditions are met
            let conditionsMet = true;

            for (const condition of rule.conditions || []) {
                const field = condition.field;
                const operator = condition.operator;
                const value = condition.value;

                // Get the actual value from the request
                const actualValue = request[field];

                if (actualValue === undefined) {
                    conditionsMet = false;
                    break;
                }

                // Evaluate the condition based on the operator
                switch (operator) {
                    case '=':
                        if (actualValue !== value) {
                            conditionsMet = false;
                        }
                        break;
                    case '!=':
                        if (actualValue === value) {
                            conditionsMet = false;
                        }
                        break;
                    case '>':
                        if (actualValue <= value) {
                            conditionsMet = false;
                        }
                        break;
                    case '>=':
                        if (actualValue < value) {
                            conditionsMet = false;
                        }
                        break;
                    case '<':
                        if (actualValue >= value) {
                            conditionsMet = false;
                        }
                        break;
                    case '<=':
                        if (actualValue > value) {
                            conditionsMet = false;
                        }
                        break;
                    case 'in':
                        if (!Array.isArray(value) || !value.includes(actualValue)) {
                            conditionsMet = false;
                        }
                        break;
                    case 'contains':
                        if (typeof actualValue === 'string' && !actualValue.includes(value)) {
                            conditionsMet = false;
                        }
                        break;
                    default:
                        conditionsMet = false;
                        break;
                }

                if (!conditionsMet) {
                    break;
                }
            }

            if (conditionsMet) {
                return [true, rule.reason || 'Auto-approved by rule'];
            }
        }

        return [false, 'Does not meet auto-approval criteria'];
    }
}

class ApprovalNotifier {
    constructor(config = {}) {
        this.config = config;
        this.smtpConfig = config.notifications?.channels?.email || {};
    }

    notifyApprover(request) {
        if (!this.smtpConfig.enabled) {
            return;
        }

        const subject = `Action Required: Approval Request #${request.id}`;

        const htmlBody = `
        <h2>Approval Request #${request.id}</h2>
        <p><strong>Requestor:</strong> ${request.requestorName} (${request.requestorEmail})</p>
        <p><strong>Category:</strong> ${request.category}</p>
        <p><strong>Amount:</strong> ${request.currency} ${request.amount}</p>
        <p><strong>Description:</strong> ${request.description}</p>
        <p><strong>Justification:</strong> ${request.justification}</p>
        <p><strong>Risk Level:</strong> ${request.riskLevel}</p>
        <p><strong>Due Date:</strong> ${new Date(request.dueDate)}</p>
        `;

        this.sendEmail([request.currentApproverEmail], subject, htmlBody);
    }

    notifyRequestor(request, action, comments = "") {
        if (!this.smtpConfig.enabled) {
            return;
        }

        const subject = `Approval Update: Request #${request.id} - ${action.toUpperCase()}`;

        let htmlBody = `
        <h2>Approval Update for Request #${request.id}</h2>
        <p><strong>Action Taken:</strong> ${action.toUpperCase()}</p>
        <p><strong>By:</strong> ${request.currentApproverName}</p>
        <p><strong>Status:</strong> ${request.status}</p>
        `;

        if (comments) {
            htmlBody += `<p><strong>Comments:</strong> ${comments}</p>`;
        }

        this.sendEmail([request.requestorEmail], subject, htmlBody);
    }

    sendEmail(recipients, subject, body) {
        if (!this.smtpConfig.enabled) {
            return;
        }

        // In a real implementation, this would connect to an SMTP server
        console.log(`Email notification would be sent to ${recipients.join(', ')} with subject: ${subject}`);

        // For demonstration purposes, we'll just log the email content
        console.log('Email content:', {
            recipients,
            subject,
            body
        });
    }
}

class ApprovalProcessor extends EventEmitter {
    constructor(configPath = null) {
        super();
        this.config = this.loadConfig(configPath);
        this.store = new ApprovalStore();
        this.chainEvaluator = new ApprovalChainEvaluator(this.config);
        this.autoApprovalEvaluator = new AutoApprovalEvaluator(this.config);
        this.notifier = new ApprovalNotifier(this.config);
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
                retentionDays: 365
            },
            approvalChains: {
                financial: {
                    paymentApprovals: {
                        enabled: true,
                        thresholds: [
                            { amount: 0, level: 1, approvers: [{ role: 'manager' }] },
                            { amount: 5000, level: 2, approvers: [{ role: 'director' }] },
                            { amount: 25000, level: 3, approvers: [{ role: 'vp' }] }
                        ]
                    }
                }
            },
            autoApprovalRules: {
                enabled: true,
                rules: []
            },
            notifications: {
                channels: {
                    email: { enabled: false }
                }
            },
            escalationRules: {
                timeBased: {
                    enabled: true,
                    rules: []
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

    submitRequest(requestData) {
        // Generate request ID
        const requestId = this.generateRequestId(requestData);

        // Determine the initial approver
        const initialApprover = this.chainEvaluator.getInitialApprover(
            new ApprovalRequest({
                id: requestId,
                requestorId: requestData.requestorId || 'unknown',
                requestorName: requestData.requestorName || 'Unknown',
                requestorEmail: requestData.requestorEmail || '',
                approvalType: requestData.approvalType || 'general',
                category: requestData.category || 'general',
                requestDate: Date.now(),
                dueDate: Date.now() + (7 * 24 * 60 * 60 * 1000), // Default: 1 week
                priority: requestData.priority || ApprovalPriority.NORMAL,
                amount: requestData.amount || 0.0,
                currency: requestData.currency || 'USD',
                description: requestData.description || '',
                justification: requestData.justification || '',
                associatedDocuments: requestData.associatedDocuments || [],
                riskLevel: requestData.riskLevel || 'medium',
                currentApproverId: '',
                currentApproverName: '',
                currentApproverEmail: '',
                approvalChain: [],
                currentLevel: 0,
                status: ApprovalStatus.PENDING,
                createdBy: requestData.requestorId || 'unknown'
            })
        );

        if (!initialApprover) {
            throw new Error("Could not determine initial approver for request");
        }

        // Check for auto-approval
        const [autoApprove, reason] = this.autoApprovalEvaluator.shouldAutoApprove(
            new ApprovalRequest({
                id: requestId,
                requestorId: requestData.requestorId || 'unknown',
                requestorName: requestData.requestorName || 'Unknown',
                requestorEmail: requestData.requestorEmail || '',
                approvalType: requestData.approvalType || 'general',
                category: requestData.category || 'general',
                requestDate: Date.now(),
                dueDate: Date.now() + (7 * 24 * 60 * 60 * 1000), // Default: 1 week
                priority: requestData.priority || ApprovalPriority.NORMAL,
                amount: requestData.amount || 0.0,
                currency: requestData.currency || 'USD',
                description: requestData.description || '',
                justification: requestData.justification || '',
                associatedDocuments: requestData.associatedDocuments || [],
                riskLevel: requestData.riskLevel || 'medium',
                currentApproverId: initialApprover.id,
                currentApproverName: initialApprover.name,
                currentApproverEmail: initialApprover.email,
                approvalChain: [], // Will be populated based on config
                currentLevel: 0,
                status: autoApprove ? ApprovalStatus.APPROVED : ApprovalStatus.PENDING,
                createdBy: requestData.requestorId || 'unknown'
            })
        );

        // Create the approval request object
        const request = new ApprovalRequest({
            id: requestId,
            requestorId: requestData.requestorId || 'unknown',
            requestorName: requestData.requestorName || 'Unknown',
            requestorEmail: requestData.requestorEmail || '',
            approvalType: requestData.approvalType || 'general',
            category: requestData.category || 'general',
            requestDate: Date.now(),
            dueDate: requestData.dueDate || (Date.now() + (7 * 24 * 60 * 60 * 1000)), // Default: 1 week
            priority: requestData.priority || ApprovalPriority.NORMAL,
            amount: requestData.amount || 0.0,
            currency: requestData.currency || 'USD',
            description: requestData.description || '',
            justification: requestData.justification || '',
            associatedDocuments: requestData.associatedDocuments || [],
            riskLevel: requestData.riskLevel || 'medium',
            currentApproverId: autoApprove ? requestData.requestorId || 'unknown' : initialApprover.id,
            currentApproverName: autoApprove ? requestData.requestorName || 'Unknown' : initialApprover.name,
            currentApproverEmail: autoApprove ? requestData.requestorEmail || '' : initialApprover.email,
            approvalChain: [], // Will be populated based on the actual approval chain configuration
            currentLevel: 0,
            status: autoApprove ? ApprovalStatus.APPROVED : ApprovalStatus.PENDING,
            createdBy: requestData.requestorId || 'unknown',
            metadata: requestData.metadata || {},
            approvalHistory: []
        });

        // Save the request
        this.store.saveApprovalRequest(request);

        // If not auto-approved, notify the first approver
        if (!autoApprove) {
            this.notifier.notifyApprover(request);
        } else {
            // For auto-approved requests, notify the requestor
            this.notifier.notifyRequestor(request, 'auto-approved', reason);
        }

        console.log(`Submitted approval request ${requestId}. Auto-approved: ${autoApprove}`);

        // Emit event
        this.emit('requestSubmitted', {
            requestId,
            autoApproved: autoApprove,
            reason: autoApprove ? reason : null
        });

        return requestId;
    }

    approveRequest(requestId, approverId, approverName, approverEmail, comments = "") {
        const request = this.store.getApprovalRequest(requestId);
        if (!request) {
            console.log(`Request ${requestId} not found`);
            return false;
        }

        if (request.status !== ApprovalStatus.PENDING) {
            console.log(`Request ${requestId} is not in pending status`);
            return false;
        }

        // Record the approval action
        const action = new ApprovalAction({
            requestId,
            approverId,
            approverName,
            approverEmail,
            action: 'approve',
            timestamp: Date.now(),
            comments
        });
        this.store.saveApprovalAction(action);

        // Check if this was the final approval in the chain
        // For simplicity in this example, we'll assume a single-level approval
        // In a real system, you'd check the approval chain configuration
        const nextApprover = this.chainEvaluator.getNextApprover(request, request.currentLevel);

        if (nextApprover) {
            // Move to next approver in chain
            const updatedRequest = new ApprovalRequest({
                ...request.toJSON(),
                currentApproverId: nextApprover.id,
                currentApproverName: nextApprover.name,
                currentApproverEmail: nextApprover.email,
                currentLevel: request.currentLevel + 1,
                approvalHistory: [...request.approvalHistory, action.toJSON()]
            });

            this.store.saveApprovalRequest(updatedRequest);
            this.notifier.notifyApprover(updatedRequest);

            console.log(`Request ${requestId} approved, forwarded to next approver: ${nextApprover.name}`);

            // Emit event
            this.emit('requestForwarded', {
                requestId,
                nextApprover: nextApprover.name
            });
        } else {
            // Final approval - mark as approved
            const updatedRequest = new ApprovalRequest({
                ...request.toJSON(),
                status: ApprovalStatus.APPROVED,
                approvalHistory: [...request.approvalHistory, action.toJSON()]
            });

            this.store.saveApprovalRequest(updatedRequest);
            this.notifier.notifyRequestor(updatedRequest, 'approved', comments);

            console.log(`Request ${requestId} fully approved`);

            // Emit event
            this.emit('requestApproved', {
                requestId,
                approvedBy: approverName
            });
        }

        return true;
    }

    rejectRequest(requestId, approverId, approverName, approverEmail, comments = "") {
        const request = this.store.getApprovalRequest(requestId);
        if (!request) {
            console.log(`Request ${requestId} not found`);
            return false;
        }

        if (request.status !== ApprovalStatus.PENDING) {
            console.log(`Request ${requestId} is not in pending status`);
            return false;
        }

        // Record the rejection action
        const action = new ApprovalAction({
            requestId,
            approverId,
            approverName,
            approverEmail,
            action: 'reject',
            timestamp: Date.now(),
            comments
        });
        this.store.saveApprovalAction(action);

        // Update the request status to rejected
        const updatedRequest = new ApprovalRequest({
            ...request.toJSON(),
            status: ApprovalStatus.REJECTED,
            approvalHistory: [...request.approvalHistory, action.toJSON()]
        });

        this.store.saveApprovalRequest(updatedRequest);
        this.notifier.notifyRequestor(updatedRequest, 'rejected', comments);

        console.log(`Request ${requestId} rejected by ${approverName}`);

        // Emit event
        this.emit('requestRejected', {
            requestId,
            rejectedBy: approverName,
            comments
        });

        return true;
    }

    cancelRequest(requestId, requestorId, reason = "") {
        const request = this.store.getApprovalRequest(requestId);
        if (!request) {
            console.log(`Request ${requestId} not found`);
            return false;
        }

        if (request.requestorId !== requestorId) {
            console.log(`Unauthorized: Requestor ${requestorId} cannot cancel request ${requestId}`);
            return false;
        }

        if (request.status !== ApprovalStatus.PENDING) {
            console.log(`Request ${requestId} is not in pending status and cannot be cancelled`);
            return false;
        }

        // Update the request status to cancelled
        const updatedRequest = new ApprovalRequest({
            ...request.toJSON(),
            status: ApprovalStatus.CANCELLED,
            cancellationReason: reason
        });

        this.store.saveApprovalRequest(updatedRequest);

        console.log(`Request ${requestId} cancelled by requestor ${requestorId}`);

        // Emit event
        this.emit('requestCancelled', {
            requestId,
            cancelledBy: requestorId,
            reason
        });

        return true;
    }

    generateRequestId(requestData) {
        const content = `${requestData.requestorId || ''}:${requestData.description || ''}:${Date.now()}`;
        return crypto.createHash('sha256').update(content).digest('hex').substring(0, 16);
    }

    async checkForOverdueApprovals() {
        const allRequests = this.store.requests;
        const now = Date.now();

        for (const request of allRequests) {
            if (request.status === ApprovalStatus.PENDING && request.dueDate < now) {
                console.log(`Overdue request detected: ${request.id}`);

                // In a real system, you would implement escalation logic here
                // For now, we'll just update the status to escalated
                const updatedRequest = new ApprovalRequest({
                    ...request,
                    status: ApprovalStatus.ESCALATED
                });

                this.store.saveApprovalRequest(updatedRequest);

                // Emit event
                this.emit('requestEscalated', {
                    requestId: request.id,
                    dueDate: request.dueDate
                });
            }
        }
    }

    async runEscalationCheck() {
        while (this.running) {
            try {
                await this.checkForOverdueApprovals();
            } catch (error) {
                console.error('Error during escalation check:', error.message);
            }

            // Wait for the escalation check interval (1 hour)
            await new Promise(resolve => setTimeout(resolve, 3600000)); // 1 hour
        }
    }

    async runContinuous() {
        if (this.running) {
            throw new Error('Approval processor is already running');
        }

        this.running = true;
        console.log('Starting approval processor...');

        // Start escalation checker in background
        const escalationPromise = this.runEscalationCheck();

        try {
            while (this.running) {
                // Perform any periodic maintenance tasks
                await new Promise(resolve => setTimeout(resolve, 60000)); // Check every minute
            }
        } catch (error) {
            console.error('Error in main loop:', error.message);
        } finally {
            this.running = false;
            // Wait for escalation checker to finish
            try {
                await Promise.race([
                    escalationPromise,
                    new Promise(resolve => setTimeout(resolve, 5000)) // 5 second timeout
                ]);
            } catch (e) {
                console.error('Error stopping escalation checker:', e.message);
            }
        }

        console.log('Approval processor stopped');
        this.emit('stopped');
    }

    async stop() {
        if (!this.running) {
            return;
        }

        this.running = false;

        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }

        console.log('Approval processor stopped');
        this.emit('stopped');
    }

    async getStatus() {
        return {
            running: this.running,
            pendingApprovals: this.store.requests.filter(r => r.status === ApprovalStatus.PENDING).length,
            config: {
                batchSize: this.config.processing.batchSize,
                batchInterval: this.config.processing.batchInterval
            }
        };
    }
}

// If running directly, start the processor
if (require.main === module) {
    const args = process.argv.slice(2);

    // Parse command line arguments
    const configIndex = args.indexOf('--config');
    const configPath = configIndex !== -1 ? args[configIndex + 1] : null;

    const testModeIndex = args.indexOf('--test-mode');
    const testMode = testModeIndex !== -1;

    const processor = new ApprovalProcessor(configPath);

    if (testMode) {
        // Submit a test request
        const testRequest = {
            requestorId: 'user-123',
            requestorName: 'John Doe',
            requestorEmail: 'john.doe@company.com',
            approvalType: 'financial',
            category: 'payment',
            amount: 250.00,
            currency: 'USD',
            description: 'Office supplies purchase',
            justification: 'Quarterly office supplies restocking',
            riskLevel: 'low',
            priority: ApprovalPriority.NORMAL
        };

        const requestId = processor.submitRequest(testRequest);
        console.log(`Test request submitted with ID: ${requestId}`);

        // Simulate approval if not auto-approved
        setTimeout(() => {
            const request = processor.store.getApprovalRequest(requestId);
            if (request && request.status === ApprovalStatus.PENDING) {
                console.log(`Approving test request ${requestId}`);
                processor.approveRequest(
                    requestId,
                    'approver-456',
                    'Jane Smith',
                    'jane.smith@company.com',
                    'Approved based on policy'
                );
            }
        }, 2000); // Wait 2 seconds before simulating approval
    }

    // Handle shutdown gracefully
    const shutdown = async () => {
        console.log('\nReceived interrupt signal, stopping processor...');
        await processor.stop();
        process.exit(0);
    };

    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);

    // Start processor
    processor.runContinuous().catch(err => {
        console.error('Error starting processor:', err);
        process.exit(1);
    });

    // Listen for events
    processor.on('requestSubmitted', (data) => {
        console.log(`Request submitted: ${data.requestId}, Auto-approved: ${data.autoApproved}`);
    });

    processor.on('requestApproved', (data) => {
        console.log(`Request approved: ${data.requestId} by ${data.approvedBy}`);
    });

    processor.on('requestRejected', (data) => {
        console.log(`Request rejected: ${data.requestId} by ${data.rejectedBy}`);
    });

    processor.on('requestCancelled', (data) => {
        console.log(`Request cancelled: ${data.requestId} by ${data.cancelledBy}`);
    });

    processor.on('requestEscalated', (data) => {
        console.log(`Request escalated: ${data.requestId}`);
    });

    processor.on('stopped', () => {
        console.log('Processor stopped successfully');
    });
}

module.exports = {
    ApprovalProcessor,
    ApprovalRequest,
    ApprovalAction,
    ApprovalStatus,
    ApprovalPriority
};