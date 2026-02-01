/**
 * Social Media Content Formatter for Social Media Poster Skill
 */

const fs = require('fs');
const path = require('path');
const axios = require('axios');

class ContentFormatter {
    constructor() {
        // Platform-specific character limits
        this.characterLimits = {
            twitter: 280,
            facebook: 63206,  // Max for feed posts
            linkedin: 3000,   // Main post content
            instagram: 2200   // Caption limit
        };

        // Setup logging
        this.logFile = path.join('/Logs', `content_formatter_${new Date().toISOString().split('T')[0]}.log`);

        // Hashtag strategies
        this.hashtagStrategies = {
            twitter: { min: 1, max: 2, optimal: 1 },
            facebook: { min: 1, max: 5, optimal: 2 },
            linkedin: { min: 3, max: 5, optimal: 4 },
            instagram: { min: 5, max: 30, optimal: 15 }
        };

        // Emoji recommendations by platform
        this.emojiGuidelines = {
            linkedin: {
                professional: ['📊', '📈', '💡', '🚀', '🤝', '👍', '🎯', '✨'],
                avoid: ['😂', '🤣', '🔥', '💯', '⚡', '💥']
            },
            twitter: {
                balanced: ['📊', '📈', '💡', '🚀', '👍', '👇', '⬆️', '⬇️', '🔥', '💯', '⚡'],
                avoid: []
            },
            facebook: {
                friendly: ['👍', '❤️', '🌟', '🎉', '💡', '📊', '📈', '🚀'],
                avoid: []
            },
            instagram: {
                expressive: ['✨', '🔥', '💡', '🚀', '🌟', '🎉', '💪', '🎯', '👍', '❤️'],
                avoid: []
            }
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
     * Format content for a specific platform
     */
    formatForPlatform(content, platform, options = {}) {
        try {
            this.log('INFO', `Formatting content for ${platform}`);

            let formattedContent = content;

            // Apply platform-specific formatting
            switch (platform.toLowerCase()) {
                case 'twitter':
                    formattedContent = this.formatForTwitter(formattedContent, options);
                    break;
                case 'facebook':
                    formattedContent = this.formatForFacebook(formattedContent, options);
                    break;
                case 'linkedin':
                    formattedContent = this.formatForLinkedIn(formattedContent, options);
                    break;
                case 'instagram':
                    formattedContent = this.formatForInstagram(formattedContent, options);
                    break;
                default:
                    throw new Error(`Unsupported platform: ${platform}`);
            }

            this.log('INFO', `Content formatted successfully for ${platform}`);
            return formattedContent;
        } catch (error) {
            this.log('ERROR', `Error formatting content for ${platform}: ${error.message}`);
            throw error;
        }
    }

    /**
     * Format content specifically for Twitter
     */
    formatForTwitter(content, options = {}) {
        let formatted = content;

        // Apply character limit
        if (formatted.length > this.characterLimits.twitter) {
            formatted = this.truncateContent(formatted, this.characterLimits.twitter - 20); // Leave room for hashtags
        }

        // Apply hashtag strategy
        formatted = this.applyHashtagStrategy(formatted, 'twitter', options.hashtags);

        // Apply emoji strategy if not explicitly disabled
        if (options.useEmojis !== false) {
            formatted = this.applyEmojiStrategy(formatted, 'twitter', options.emphasis);
        }

        // Add link placeholder if needed
        if (options.link) {
            const linkPlaceholder = ` ${options.link}`;
            if (formatted.length + linkPlaceholder.length <= this.characterLimits.twitter) {
                formatted += linkPlaceholder;
            }
        }

        return formatted;
    }

    /**
     * Format content specifically for Facebook
     */
    formatForFacebook(content, options = {}) {
        let formatted = content;

        // Apply character limit if necessary
        if (options.enforceLimit && formatted.length > this.characterLimits.facebook) {
            formatted = this.truncateContent(formatted, this.characterLimits.facebook);
        }

        // Apply hashtag strategy
        formatted = this.applyHashtagStrategy(formatted, 'facebook', options.hashtags);

        // Apply emoji strategy if not explicitly disabled
        if (options.useEmojis !== false) {
            formatted = this.applyEmojiStrategy(formatted, 'facebook', options.emphasis);
        }

        // Format paragraphs for readability
        formatted = this.formatParagraphs(formatted);

        return formatted;
    }

    /**
     * Format content specifically for LinkedIn
     */
    formatForLinkedIn(content, options = {}) {
        let formatted = content;

        // Apply character limit if necessary
        if (options.enforceLimit && formatted.length > this.characterLimits.linkedin) {
            formatted = this.truncateContent(formatted, this.characterLimits.linkedin);
        }

        // Apply hashtag strategy
        formatted = this.applyHashtagStrategy(formatted, 'linkedin', options.hashtags);

        // Apply emoji strategy (professional emojis only)
        if (options.useEmojis !== false) {
            formatted = this.applyEmojiStrategy(formatted, 'linkedin', options.emphasis);
        }

        // Format for professional readability
        formatted = this.formatForProfessionalReading(formatted);

        return formatted;
    }

    /**
     * Format content specifically for Instagram
     */
    formatForInstagram(content, options = {}) {
        let formatted = content;

        // Apply character limit
        if (formatted.length > this.characterLimits.instagram) {
            formatted = this.truncateContent(formatted, this.characterLimits.instagram);
        }

        // Apply hashtag strategy (often more hashtags for Instagram)
        formatted = this.applyHashtagStrategy(formatted, 'instagram', options.hashtags);

        // Apply emoji strategy if not explicitly disabled
        if (options.useEmojis !== false) {
            formatted = this.applyEmojiStrategy(formatted, 'instagram', options.emphasis);
        }

        return formatted;
    }

    /**
     * Truncate content to fit within character limit
     */
    truncateContent(content, maxLength) {
        if (content.length <= maxLength) {
            return content;
        }

        // Try to cut at sentence boundary if possible
        const sentences = content.split(/(?<=[.!?])\s+/);
        let result = '';

        for (const sentence of sentences) {
            if ((result + sentence).length > maxLength - 3) {
                result += '...';
                break;
            }
            if (result) result += ' ';
            result += sentence;
        }

        // If still too long, just truncate
        if (result.length > maxLength) {
            result = result.substring(0, maxLength - 3) + '...';
        }

        return result;
    }

    /**
     * Apply hashtag strategy based on platform
     */
    applyHashtagStrategy(content, platform, hashtags = []) {
        if (!hashtags || hashtags.length === 0) {
            return content;
        }

        const strategy = this.hashtagStrategies[platform];
        if (!strategy) {
            return content;
        }

        // Limit hashtags based on platform strategy
        const maxHashtags = strategy.max;
        let selectedHashtags = hashtags.slice(0, maxHashtags);

        // Add hashtags to content
        const hashtagString = selectedHashtags.map(tag => `#${tag.replace('#', '')}`).join(' ');
        return `${content} ${hashtagString}`.trim();
    }

    /**
     * Apply emoji strategy based on platform
     */
    applyEmojiStrategy(content, platform, emphasis = 'medium') {
        if (!this.emojiGuidelines[platform]) {
            return content;
        }

        const guidelines = this.emojiGuidelines[platform];
        const { professional = [], balanced = [], friendly = [], expressive = [], avoid = [] } = guidelines;

        let emojisToUse = [];
        switch (emphasis) {
            case 'high':
            case 'strong':
                emojisToUse = expressive.length > 0 ? expressive : balanced;
                break;
            case 'low':
            case 'minimal':
                emojisToUse = professional.length > 0 ? professional : [friendly[0], balanced[0]].filter(Boolean);
                break;
            default: // medium
                emojisToUse = balanced.length > 0 ? balanced :
                             professional.length > 0 ? professional :
                             friendly;
        }

        // Add emojis appropriately
        if (emojisToUse.length > 0) {
            // For now, just append a random selection of appropriate emojis
            const numEmojis = emphasis === 'high' ? 3 : emphasis === 'low' ? 1 : 2;
            const selectedEmojis = this.getRandomElements(emojisToUse, numEmojis);
            return `${content} ${selectedEmojis.join(' ')}`;
        }

        return content;
    }

    /**
     * Format content for professional reading (LinkedIn style)
     */
    formatForProfessionalReading(content) {
        // Add structure with bullet points if there are multiple ideas
        const sentences = content.split(/(?<=[.!?])\s+/);

        if (sentences.length >= 3) {
            // Look for key points and structure them
            const formattedSentences = sentences.map((sentence, index) => {
                // Add numbering for LinkedIn-style structure
                if (index === 0) {
                    return `🔹 ${sentence}`;
                } else if (index === sentences.length - 1) {
                    return `✓ ${sentence}`;
                } else {
                    return `• ${sentence}`;
                }
            });

            return formattedSentences.join('\n\n');
        }

        return content;
    }

    /**
     * Format paragraphs for better readability
     */
    formatParagraphs(content) {
        // Split content into paragraphs based on sentence structure
        const paragraphs = content.split(/\n\s*\n/);
        return paragraphs.join('\n\n');
    }

    /**
     * Get random elements from an array
     */
    getRandomElements(array, count) {
        const shuffled = [...array].sort(() => 0.5 - Math.random());
        return shuffled.slice(0, count);
    }

    /**
     * Validate content against platform guidelines
     */
    validateContent(content, platform) {
        const validation = {
            isValid: true,
            errors: [],
            warnings: []
        };

        // Check character limit
        if (content.length > this.characterLimits[platform]) {
            validation.isValid = false;
            validation.errors.push(`Content exceeds ${platform} character limit (${content.length}/${this.characterLimits[platform]})`);
        }

        // Check for prohibited content (basic checks)
        const prohibitedPatterns = [
            /spam|click here|free money/gi,
            /buy now|act now|limited time/gi  // Potentially promotional
        ];

        for (const pattern of prohibitedPatterns) {
            if (pattern.test(content)) {
                validation.warnings.push(`Content may contain promotional language that could affect reach`);
            }
        }

        return validation;
    }

    /**
     * Generate platform-appropriate caption from headline and description
     */
    generateCaption(headline, description, platform, options = {}) {
        let caption = '';

        if (platform === 'twitter') {
            // Twitter: Short, punchy, with key info first
            caption = `${headline} ${description}`.substring(0, this.characterLimits.twitter - 30);
        } else if (platform === 'instagram') {
            // Instagram: Longer description, emojis, hashtags at the end
            caption = `${headline}\n\n${description}`;
        } else if (platform === 'linkedin') {
            // LinkedIn: Professional, structured, value-focused
            caption = `📋 ${headline}\n\n${description}`;
        } else if (platform === 'facebook') {
            // Facebook: Conversational, engaging
            caption = `${headline}\n\n${description}`;
        }

        return this.formatForPlatform(caption, platform, options);
    }

    /**
     * Create carousel post content (for Instagram/Facebook)
     */
    createCarouselContent(slides, platform) {
        if (platform !== 'instagram' && platform !== 'facebook') {
            throw new Error(`${platform} does not support carousel posts`);
        }

        const carouselContent = [];

        slides.forEach((slide, index) => {
            const slideContent = {
                index: index + 1,
                headline: slide.headline || '',
                description: slide.description || '',
                formatted: this.formatForPlatform(
                    `${slide.headline ? slide.headline + ': ' : ''}${slide.description}`,
                    platform,
                    { enforceLimit: true }
                )
            };

            carouselContent.push(slideContent);
        });

        return carouselContent;
    }

    /**
     * Create story content (for Instagram/Facebook)
     */
    createStoryContent(text, platform) {
        if (platform !== 'instagram' && platform !== 'facebook') {
            throw new Error(`${platform} stories not fully supported in formatter`);
        }

        // Story content is typically minimal
        const maxLength = platform === 'instagram' ? 120 : 120; // Approximate for stories
        return this.truncateContent(text, maxLength);
    }
}

module.exports = ContentFormatter;

// Example usage
if (require.main === module) {
    const formatter = new ContentFormatter();

    const sampleContent = "We're excited to announce our new product launch! This innovative solution addresses key challenges in the industry and provides unprecedented value to our customers.";

    console.log("Original content:");
    console.log(sampleContent);
    console.log("\n" + "=".repeat(50) + "\n");

    console.log("Formatted for LinkedIn:");
    console.log(formatter.formatForLinkedIn(sampleContent, { hashtags: ['innovation', 'productLaunch', 'tech'], useEmojis: true }));
    console.log("\n" + "=".repeat(50) + "\n");

    console.log("Formatted for Twitter:");
    console.log(formatter.formatForTwitter(sampleContent, { hashtags: ['news', 'launch'], useEmojis: true, link: 'https://example.com' }));
    console.log("\n" + "=".repeat(50) + "\n");

    console.log("Formatted for Instagram:");
    console.log(formatter.formatForInstagram(sampleContent, { hashtags: ['newproduct', 'launch', 'tech', 'innovation', 'business'], useEmojis: true }));
    console.log("\n" + "=".repeat(50) + "\n");

    console.log("Validation for Twitter:");
    console.log(formatter.validateContent(sampleContent, 'twitter'));
}