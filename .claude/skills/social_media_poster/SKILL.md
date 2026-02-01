# Social Media Poster Skill

## Purpose and Use Cases
The Social Media Poster skill enables the AI employee to schedule and post content to LinkedIn, Twitter, Facebook, and Instagram according to predetermined strategies. This skill automates social media marketing while ensuring brand consistency and compliance with platform policies.

## Input Parameters and Expected Formats
- `platforms`: Array of platforms to post to ('linkedin', 'twitter', 'facebook', 'instagram')
- `content`: Post content (text, image URL, video URL)
- `schedule_time`: ISO 8601 timestamp for scheduled posting
- `hashtags`: Array of hashtags to include
- `target_audience`: Audience segment for personalized content
- `campaign`: Campaign identifier for analytics tracking
- `media_attachments`: Array of local file paths for media

## Processing Logic and Decision Trees
1. **Content Preparation**:
   - Format content according to platform-specific requirements
   - Adjust character limits for each platform
   - Optimize media for platform-specific dimensions

2. **Schedule Operation**:
   - Validate schedule_time is in the future
   - Queue post in scheduler system
   - Create reminder in calendar for review

3. **Posting Operation**:
   - Authenticate with platform APIs
   - Upload media if required
   - Publish post with appropriate metadata

4. **Analytics Tracking**:
   - Monitor post performance metrics
   - Update campaign analytics
   - Flag underperforming content for review

## Output Formats and File Structures
- Creates social media activity logs in /Logs/social_media_[date].log
- Generates approval requests in /Pending_Approval/social_[timestamp].md for sensitive posts
- Updates Dashboard.md with posting metrics and engagement stats
- Maintains campaign performance data in /Data/campaigns/

## Error Handling Procedures
- Retry failed posts with exponential backoff
- Log API rate limit errors to /Logs/api_limits.log
- Queue posts for manual review if automation fails
- Send alert if account authentication fails

## Security Considerations
- Store social media API keys in environment variables
- Implement approval workflow for brand-sensitive content
- Maintain audit trail of all posted content
- Rate limit posting to avoid platform restrictions

## Integration Points with Other System Components
- Triggers communication logger for all social media activities
- Integrates with Approval Processor for sensitive content
- Updates Dashboard Updater with engagement metrics
- Creates action files in /Needs_Action for community management