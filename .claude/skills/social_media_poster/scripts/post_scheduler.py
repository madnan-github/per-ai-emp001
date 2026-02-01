#!/usr/bin/env python3
"""
Social Media Post Scheduler for Social Media Poster Skill
"""

import asyncio
import aiohttp
import json
import os
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import hashlib
from pathlib import Path
import schedule
import time

class SocialMediaScheduler:
    def __init__(self):
        """Initialize the Social Media Scheduler with configuration"""
        # API tokens from environment variables
        self.linkedin_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
        self.twitter_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.facebook_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
        self.instagram_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')

        # Setup logging
        logging.basicConfig(
            filename=f'/Logs/social_media_scheduler_{datetime.now().strftime("%Y%m%d")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Database for tracking posts
        self.db_path = '/Data/social_media_posts.db'
        self._setup_database()

        # Platform configurations
        self.platform_configs = {
            'linkedin': {
                'api_url': 'https://api.linkedin.com/v2/ugcPosts',
                'headers': {'Authorization': f'Bearer {self.linkedin_token}'}
            },
            'twitter': {
                'api_url': 'https://api.twitter.com/2/tweets',
                'headers': {'Authorization': f'Bearer {self.twitter_token}'}
            },
            'facebook': {
                'api_url': f'https://graph.facebook.com/me/feed',
                'headers': {'Authorization': f'Bearer {self.facebook_token}'}
            },
            'instagram': {
                'api_url': f'https://graph.facebook.com/v17.0/me/accounts',
                'headers': {'Authorization': f'Bearer {self.instagram_token}'}
            }
        }

    def _setup_database(self):
        """Setup database for tracking scheduled posts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                content TEXT NOT NULL,
                scheduled_time DATETIME NOT NULL,
                status TEXT DEFAULT 'scheduled',  -- scheduled, posted, failed, cancelled
                post_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS post_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER,
                platform TEXT,
                metric_name TEXT,
                metric_value REAL,
                recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def schedule_post(self,
                     platform: str,
                     content: str,
                     scheduled_time: datetime,
                     media_attachments: List[str] = None) -> bool:
        """
        Schedule a post for a specific platform and time

        Args:
            platform: Social media platform ('linkedin', 'twitter', 'facebook', 'instagram')
            content: Post content
            scheduled_time: When to post
            media_attachments: List of media file paths

        Returns:
            bool: True if scheduled successfully, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO scheduled_posts (platform, content, scheduled_time)
                VALUES (?, ?, ?)
            ''', (platform, content, scheduled_time))

            conn.commit()
            post_id = cursor.lastrowid
            conn.close()

            logging.info(f"Post scheduled for {platform} at {scheduled_time}: {content[:50]}...")

            # If scheduled time is in the past, post immediately
            if scheduled_time <= datetime.now():
                asyncio.run(self._post_immediately(platform, content, media_attachments))

            return True

        except Exception as e:
            logging.error(f"Failed to schedule post: {str(e)}")
            return False

    async def _post_immediately(self, platform: str, content: str, media_attachments: List[str] = None):
        """Post immediately to the specified platform"""
        success = await self.post_to_platform(platform, content, media_attachments)
        if success:
            logging.info(f"Immediate post successful to {platform}")
        else:
            logging.error(f"Immediate post failed to {platform}")

    async def post_to_platform(self, platform: str, content: str, media_attachments: List[str] = None) -> bool:
        """
        Post content to a specific platform

        Args:
            platform: Social media platform
            content: Content to post
            media_attachments: List of media files to attach

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if platform not in self.platform_configs:
                logging.error(f"Unsupported platform: {platform}")
                return False

            config = self.platform_configs[platform]

            if platform == 'linkedin':
                return await self._post_linkedin(content, media_attachments)
            elif platform == 'twitter':
                return await self._post_twitter(content, media_attachments)
            elif platform == 'facebook':
                return await self._post_facebook(content, media_attachments)
            elif platform == 'instagram':
                return await self._post_instagram(content, media_attachments)
            else:
                logging.error(f"Platform {platform} not implemented")
                return False

        except Exception as e:
            logging.error(f"Error posting to {platform}: {str(e)}")
            return False

    async def _post_linkedin(self, content: str, media_attachments: List[str]) -> bool:
        """Post to LinkedIn"""
        headers = {
            'Authorization': f'Bearer {self.linkedin_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }

        # Prepare the post data
        post_data = {
            "author": f"urn:li:person:{os.getenv('LINKEDIN_PERSON_URN')}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        if media_attachments:
            # Handle media upload for LinkedIn
            media_values = []
            for media_path in media_attachments:
                if os.path.exists(media_path):
                    # In a real implementation, we would upload media first
                    # This is a simplified version
                    media_values.append({
                        "status": "READY",
                        "media": f"urn:li:image:{hashlib.md5(media_path.encode()).hexdigest()}"
                    })

            post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
            post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = media_values

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.linkedin.com/v2/ugcPosts',
                    headers=headers,
                    json=post_data
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        logging.info(f"LinkedIn post successful: {result.get('id', 'unknown')}")
                        return True
                    else:
                        logging.error(f"LinkedIn post failed: {response.status}, {await response.text()}")
                        return False
        except Exception as e:
            logging.error(f"Error posting to LinkedIn: {str(e)}")
            return False

    async def _post_twitter(self, content: str, media_attachments: List[str]) -> bool:
        """Post to Twitter"""
        headers = {
            'Authorization': f'Bearer {self.twitter_token}',
            'Content-Type': 'application/json'
        }

        post_data = {
            "text": content
        }

        # Handle media attachments
        if media_attachments:
            # In a real implementation, we would upload media first
            # This is a simplified version
            pass

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.twitter.com/2/tweets',
                    headers=headers,
                    json=post_data
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        logging.info(f"Twitter post successful: {result.get('data', {}).get('id', 'unknown')}")
                        return True
                    else:
                        logging.error(f"Twitter post failed: {response.status}, {await response.text()}")
                        return False
        except Exception as e:
            logging.error(f"Error posting to Twitter: {str(e)}")
            return False

    async def _post_facebook(self, content: str, media_attachments: List[str]) -> bool:
        """Post to Facebook"""
        headers = {
            'Authorization': f'Bearer {self.facebook_token}'
        }

        post_data = {
            'message': content
        }

        # Handle media attachments
        if media_attachments:
            # In a real implementation, we would handle media differently
            # This is a simplified version
            pass

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'https://graph.facebook.com/me/feed',
                    headers=headers,
                    data=post_data
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        logging.info(f"Facebook post successful: {result.get('id', 'unknown')}")
                        return True
                    else:
                        logging.error(f"Facebook post failed: {response.status}, {await response.text()}")
                        return False
        except Exception as e:
            logging.error(f"Error posting to Facebook: {str(e)}")
            return False

    async def _post_instagram(self, content: str, media_attachments: List[str]) -> bool:
        """Post to Instagram"""
        headers = {
            'Authorization': f'Bearer {self.instagram_token}'
        }

        # Get Instagram account ID first
        try:
            async with aiohttp.ClientSession() as session:
                # Get user's Instagram account
                async with session.get(
                    f'https://graph.facebook.com/v17.0/me/accounts',
                    headers={'Authorization': f'Bearer {self.instagram_token}'}
                ) as response:
                    if response.status != 200:
                        logging.error(f"Could not get Instagram account: {await response.text()}")
                        return False

                    accounts = await response.json()
                    instagram_account_id = None

                    for account in accounts.get('data', []):
                        if 'instagram' in account.get('name', '').lower():
                            instagram_account_id = account['id']
                            break

                    if not instagram_account_id:
                        logging.error("No Instagram account found linked to Facebook")
                        return False

                # Create media container
                media_data = {
                    'caption': content,
                    'access_token': self.instagram_token
                }

                async with session.post(
                    f'https://graph.facebook.com/v17.0/{instagram_account_id}/media',
                    headers=headers,
                    data=media_data
                ) as create_response:
                    if create_response.status != 200:
                        logging.error(f"Failed to create Instagram media container: {await create_response.text()}")
                        return False

                    container_result = await create_response.json()
                    container_id = container_result.get('id')

                    # Publish the media
                    publish_data = {
                        'creation_id': container_id,
                        'access_token': self.instagram_token
                    }

                    async with session.post(
                        f'https://graph.facebook.com/v17.0/{instagram_account_id}/media_publish',
                        headers=headers,
                        data=publish_data
                    ) as publish_response:
                        if publish_response.status in [200, 201]:
                            result = await publish_response.json()
                            logging.info(f"Instagram post successful: {result.get('id', 'unknown')}")
                            return True
                        else:
                            logging.error(f"Instagram publish failed: {publish_response.status}, {await publish_response.text()}")
                            return False
        except Exception as e:
            logging.error(f"Error posting to Instagram: {str(e)}")
            return False

    async def check_and_post_scheduled(self):
        """Check for scheduled posts that are ready to be posted"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get posts that are scheduled and ready to be posted
        now = datetime.now()
        cursor.execute('''
            SELECT id, platform, content, scheduled_time
            FROM scheduled_posts
            WHERE status = 'scheduled' AND scheduled_time <= ?
            ORDER BY scheduled_time ASC
        ''', (now,))

        ready_posts = cursor.fetchall()
        conn.close()

        logging.info(f"Found {len(ready_posts)} posts ready for publishing")

        for post_row in ready_posts:
            post_id, platform, content, scheduled_time = post_row

            # Update status to 'posting' to prevent duplicate processing
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE scheduled_posts SET status = ? WHERE id = ?', ('posting', post_id))
            conn.commit()
            conn.close()

            # Post to the platform
            success = await self.post_to_platform(platform, content)

            # Update status based on result
            final_status = 'posted' if success else 'failed'
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE scheduled_posts SET status = ?, updated_at = ? WHERE id = ?',
                          (final_status, datetime.now(), post_id))
            conn.commit()
            conn.close()

            if success:
                logging.info(f"Successfully posted scheduled post {post_id} to {platform}")
            else:
                logging.error(f"Failed to post scheduled post {post_id} to {platform}")

    def cancel_scheduled_post(self, post_id: int) -> bool:
        """Cancel a scheduled post"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE scheduled_posts
                SET status = 'cancelled', updated_at = ?
                WHERE id = ? AND status = 'scheduled'
            ''', (datetime.now(), post_id))

            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                logging.info(f"Cancelled scheduled post {post_id}")
                return True
            else:
                conn.close()
                logging.warning(f"No scheduled post found with ID {post_id}")
                return False

        except Exception as e:
            logging.error(f"Error cancelling post {post_id}: {str(e)}")
            return False

    def get_post_stats(self, platform: str = None) -> Dict[str, int]:
        """Get statistics about posts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if platform:
            cursor.execute('SELECT status, COUNT(*) FROM scheduled_posts WHERE platform = ? GROUP BY status', (platform,))
        else:
            cursor.execute('SELECT status, COUNT(*) FROM scheduled_posts GROUP BY status')

        stats = {}
        for row in cursor.fetchall():
            stats[row[0]] = row[1]

        conn.close()

        # Ensure all statuses are represented
        for status in ['scheduled', 'posted', 'failed', 'cancelled']:
            if status not in stats:
                stats[status] = 0

        return stats

    async def run_scheduler_loop(self):
        """Run the scheduler loop continuously"""
        logging.info("Social Media Scheduler started")

        while True:
            try:
                await self.check_and_post_scheduled()
                await asyncio.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logging.info("Social Media Scheduler stopped")
                break
            except Exception as e:
                logging.error(f"Error in scheduler loop: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying

def main():
    """Main function for testing the scheduler"""
    scheduler = SocialMediaScheduler()

    # Example: Schedule a post
    future_time = datetime.now() + timedelta(minutes=5)
    scheduler.schedule_post(
        platform='twitter',
        content='Testing the social media scheduler! 🚀',
        scheduled_time=future_time
    )

    # Print stats
    stats = scheduler.get_post_stats()
    print("Post Statistics:", stats)

    # Run the scheduler
    # asyncio.run(scheduler.run_scheduler_loop())

if __name__ == "__main__":
    main()