/**
 * WhatsApp Automation Script for WhatsApp Manager Skill
 */

const fs = require('fs');
const path = require('path');
const axios = require('axios');

class WhatsAppAutomation {
    constructor() {
        // Configuration from environment variables
        this.apiToken = process.env.WHATSAPP_API_TOKEN;
        this.phoneNumberId = process.env.WHATSAPP_PHONE_NUMBER_ID;
        this.baseUrl = `https://graph.facebook.com/v17.0/${this.phoneNumberId}`;

        // Setup logging
        this.logFile = path.join('/Logs', `whatsapp_automation_${new Date().toISOString().split('T')[0]}.log`);

        // Escalation keywords
        this.escalationKeywords = [
            'urgent', 'asap', 'immediately', 'emergency', 'problem',
            'issue', 'complaint', 'ceo', 'manager', 'supervisor',
            'legal', 'lawyer', 'attorney', 'contract', 'agreement'
        ];

        // Response templates
        this.responseTemplates = {
            greeting: 'Hello! 👋 Thanks for contacting us. How can I assist you today?',
            gratitude: 'You\'re very welcome! Is there anything else I can help with?',
            inquiry: 'I\'d be happy to help with your inquiry. Could you please provide more details?',
            sales: 'Thanks for your interest in our services! I\'d love to learn more about your needs.',
            appointment: 'I\'d be happy to schedule an appointment for you. Please let me know your preferred date and time.',
            complaint: '⚠️ I apologize for any inconvenience. This has been escalated to our support team.'
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
     * Send a message via WhatsApp Business API
     */
    async sendMessage(recipient, message) {
        try {
            const response = await axios.post(`${this.baseUrl}/messages`, {
                messaging_product: 'whatsapp',
                to: recipient,
                type: 'text',
                text: {
                    body: message
                }
            }, {
                headers: {
                    'Authorization': `Bearer ${this.apiToken}`,
                    'Content-Type': 'application/json'
                }
            });

            this.log('INFO', `Message sent to ${recipient}: ${message.substring(0, 50)}...`);
            return true;
        } catch (error) {
            this.log('ERROR', `Failed to send message to ${recipient}: ${error.message}`);
            return false;
        }
    }

    /**
     * Get messages from WhatsApp API
     */
    async getMessages() {
        try {
            const response = await axios.get(`${this.baseUrl}/messages`, {
                headers: {
                    'Authorization': `Bearer ${this.apiToken}`
                },
                params: {
                    fields: 'messages,contacts',
                    limit: 100
                }
            });

            this.log('INFO', `Retrieved ${response.data.messages?.length || 0} messages`);
            return response.data.messages || [];
        } catch (error) {
            this.log('ERROR', `Failed to retrieve messages: ${error.message}`);
            return [];
        }
    }

    /**
     * Categorize a message based on its content
     */
    categorizeMessage(message) {
        const lowerMsg = message.toLowerCase();

        if (lowerMsg.includes('hello') || lowerMsg.includes('hi') || lowerMsg.includes('hey')) {
            return 'greeting';
        } else if (lowerMsg.includes('thank') || lowerMsg.includes('thanks')) {
            return 'gratitude';
        } else if (lowerMsg.includes('question') || lowerMsg.includes('ask') || lowerMsg.includes('wonder')) {
            return 'inquiry';
        } else if (lowerMsg.includes('order') || lowerMsg.includes('purchase') || lowerMsg.includes('buy')) {
            return 'sales';
        } else if (lowerMsg.includes('meeting') || lowerMsg.includes('appointment') || lowerMsg.includes('schedule')) {
            return 'appointment';
        } else if (lowerMsg.includes('complaint') || lowerMsg.includes('issue') || lowerMsg.includes('problem')) {
            return 'complaint';
        } else {
            return 'general';
        }
    }

    /**
     * Check if a message requires escalation
     */
    needsEscalation(message) {
        const lowerMsg = message.toLowerCase();
        return this.escalationKeywords.some(keyword => lowerMsg.includes(keyword));
    }

    /**
     * Generate an appropriate response based on message content
     */
    generateResponse(message, sender) {
        if (this.needsEscalation(message)) {
            return this.responseTemplates.complaint;
        }

        const category = this.categorizeMessage(message);
        return this.responseTemplates[category] || 'Thanks for your message! We\'ll get back to you soon.';
    }

    /**
     * Process new messages
     */
    async processNewMessages() {
        try {
            const messages = await this.getMessages();

            for (const message of messages) {
                const sender = message.from;
                const messageText = message.text?.body || 'Media message';

                this.log('INFO', `Processing message from ${sender}: ${messageText.substring(0, 50)}...`);

                if (this.needsEscalation(messageText)) {
                    // Create escalation request
                    await this.createEscalationRequest(sender, messageText);

                    // Send acknowledgment
                    await this.sendMessage(sender,
                        "Your message has been received and escalated to our team. Someone will contact you shortly.");
                } else {
                    const response = this.generateResponse(messageText, sender);
                    await this.sendMessage(sender, response);
                }
            }

            this.log('INFO', `Processed ${messages.length} messages`);
        } catch (error) {
            this.log('ERROR', `Error processing new messages: ${error.message}`);
        }
    }

    /**
     * Create an escalation request file
     */
    async createEscalationRequest(sender, message) {
        const timestamp = Math.floor(Date.now() / 1000);
        const escalationFile = path.join('/Pending_Approval', `whatsapp_${timestamp}.md`);

        const content = `# WhatsApp Escalation Request

**Time:** ${new Date().toISOString()}
**Sender:** ${sender}
**Message:** ${message}

**Action Required:** Please review this urgent message and respond.`;

        try {
            fs.writeFileSync(escalationFile, content);
            this.log('INFO', `Escalation request created: ${escalationFile}`);
        } catch (error) {
            this.log('ERROR', `Failed to create escalation request: ${error.message}`);
        }
    }

    /**
     * Send bulk messages to multiple recipients
     */
    async sendBulkMessages(recipients, messageTemplate, variables = {}) {
        const results = {
            successful: 0,
            failed: 0,
            recipients: []
        };

        for (const recipient of recipients) {
            try {
                // Replace variables in template
                let message = messageTemplate;
                Object.keys(variables).forEach(key => {
                    message = message.replace(new RegExp(`{{${key}}}`, 'g'), variables[key]);
                });

                const success = await this.sendMessage(recipient, message);

                if (success) {
                    results.successful++;
                    results.recipients.push({ recipient, status: 'success' });
                } else {
                    results.failed++;
                    results.recipients.push({ recipient, status: 'failed' });
                }

                // Rate limiting - wait between messages
                await new Promise(resolve => setTimeout(resolve, 1000));
            } catch (error) {
                this.log('ERROR', `Error sending message to ${recipient}: ${error.message}`);
                results.failed++;
                results.recipients.push({ recipient, status: 'error', error: error.message });
            }
        }

        return results;
    }

    /**
     * Get WhatsApp usage statistics
     */
    async getStats() {
        try {
            const stats = {
                timestamp: new Date().toISOString(),
                totalMessagesSent: 0,
                totalMessagesReceived: 0,
                successfulDeliveries: 0,
                failedDeliveries: 0
            };

            // Would typically query a database or API for actual stats
            // This is a simplified version
            this.log('INFO', 'Retrieved WhatsApp statistics');
            return stats;
        } catch (error) {
            this.log('ERROR', `Failed to get stats: ${error.message}`);
            return null;
        }
    }
}

module.exports = WhatsAppAutomation;

// Example usage
if (require.main === module) {
    (async () => {
        const wa = new WhatsAppAutomation();

        console.log('WhatsApp Automation initialized');

        // Process new messages
        await wa.processNewMessages();

        // Get stats
        const stats = await wa.getStats();
        console.log('Stats:', stats);
    })();
}