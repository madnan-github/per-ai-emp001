#!/usr/bin/env python3
"""
Notification Aggregator - Consolidates alerts and notifications from various sources

This script implements a notification aggregator that collects, processes, and
delivers notifications from multiple sources to create a unified, prioritized feed
of alerts for the AI employee to process.
"""

import os
import sys
import json
import yaml
import asyncio
import aiohttp
import aioredis
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import re
import hashlib
import hmac
from collections import defaultdict
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor


class NotificationSeverity(Enum):
    """Notification severity levels"""
    LOW = 4
    MEDIUM = 3
    HIGH = 2
    CRITICAL = 1


class NotificationCategory(Enum):
    """Notification categories"""
    SYSTEM = "system"
    BUSINESS = "business"
    COMMUNICATION = "communication"
    MONITORING = "monitoring"
    SECURITY = "security"


@dataclass
class Notification:
    """Represents a notification with all required fields"""
    id: str
    source: str
    timestamp: float
    category: NotificationCategory
    severity: NotificationSeverity
    title: str
    description: str
    correlation_id: Optional[str] = None
    metadata: Optional[Dict] = None
    acknowledged: bool = False
    delivered: bool = False

    def to_dict(self) -> Dict:
        """Convert notification to dictionary format"""
        result = asdict(self)
        result['category'] = self.category.value
        result['severity'] = self.severity.value
        return result


class NotificationStore:
    """Manages storage and retrieval of notifications"""

    def __init__(self, db_path: str = "notifications.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                source TEXT,
                timestamp REAL,
                category TEXT,
                severity INTEGER,
                title TEXT,
                description TEXT,
                correlation_id TEXT,
                metadata TEXT,
                acknowledged BOOLEAN DEFAULT FALSE,
                delivered BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON notifications(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_severity ON notifications(severity)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON notifications(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_acknowledged ON notifications(acknowledged)')

        conn.commit()
        conn.close()

    def save_notification(self, notification: Notification):
        """Save a notification to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO notifications
            (id, source, timestamp, category, severity, title, description, correlation_id, metadata, acknowledged, delivered)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            notification.id,
            notification.source,
            notification.timestamp,
            notification.category.value,
            notification.severity.value,
            notification.title,
            notification.description,
            notification.correlation_id,
            json.dumps(notification.metadata or {}),
            notification.acknowledged,
            notification.delivered
        ))

        conn.commit()
        conn.close()

    def get_unprocessed_notifications(self, limit: int = 100) -> List[Notification]:
        """Get unacknowledged and undelivered notifications"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, source, timestamp, category, severity, title, description, correlation_id, metadata
            FROM notifications
            WHERE acknowledged = 0 AND delivered = 0
            ORDER BY severity ASC, timestamp DESC
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        conn.close()

        notifications = []
        for row in rows:
            metadata = json.loads(row[8]) if row[8] else {}
            notification = Notification(
                id=row[0],
                source=row[1],
                timestamp=row[2],
                category=NotificationCategory(row[3]),
                severity=NotificationSeverity(row[4]),
                title=row[5],
                description=row[6],
                correlation_id=row[7],
                metadata=metadata
            )
            notifications.append(notification)

        return notifications

    def acknowledge_notification(self, notification_id: str):
        """Mark a notification as acknowledged"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('UPDATE notifications SET acknowledged = 1 WHERE id = ?', (notification_id,))
        conn.commit()
        conn.close()

    def mark_as_delivered(self, notification_id: str):
        """Mark a notification as delivered"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('UPDATE notifications SET delivered = 1 WHERE id = ?', (notification_id,))
        conn.commit()
        conn.close()


class NotificationClassifier:
    """Classifies and prioritizes notifications based on rules"""

    def __init__(self, config: Dict):
        self.config = config
        self.severity_mapping = config.get('classification', {}).get('severity_mapping', {})

    def classify_notification(self, raw_notification: Dict) -> Notification:
        """Classify a raw notification and return a Notification object"""
        # Extract basic fields
        source = raw_notification.get('source', 'unknown')
        title = raw_notification.get('title', 'Untitled Notification')
        description = raw_notification.get('description', '')
        timestamp = raw_notification.get('timestamp', time.time())

        # Determine category
        category = self._determine_category(raw_notification)

        # Determine severity
        severity = self._determine_severity(raw_notification, source, title, description)

        # Generate unique ID
        notification_id = self._generate_notification_id(source, title, timestamp)

        # Determine correlation ID
        correlation_id = self._determine_correlation_id(raw_notification)

        # Prepare metadata
        metadata = raw_notification.get('metadata', {})
        metadata['original_source'] = source
        metadata['classification_method'] = 'automatic'

        return Notification(
            id=notification_id,
            source=source,
            timestamp=timestamp,
            category=category,
            severity=severity,
            title=title,
            description=description,
            correlation_id=correlation_id,
            metadata=metadata
        )

    def _determine_category(self, notification: Dict) -> NotificationCategory:
        """Determine the category of a notification"""
        # Check explicit category
        if 'category' in notification:
            try:
                return NotificationCategory(notification['category'])
            except ValueError:
                pass

        # Determine category based on source
        source = notification.get('source', '').lower()

        if any(keyword in source for keyword in ['system', 'os', 'hardware', 'network']):
            return NotificationCategory.SYSTEM
        elif any(keyword in source for keyword in ['email', 'slack', 'teams', 'chat']):
            return NotificationCategory.COMMUNICATION
        elif any(keyword in source for keyword in ['monitor', 'alert', 'prometheus', 'datadog']):
            return NotificationCategory.MONITORING
        elif any(keyword in source for keyword in ['security', 'firewall', 'intrusion']):
            return NotificationCategory.SECURITY
        else:
            return NotificationCategory.BUSINESS

    def _determine_severity(self, notification: Dict, source: str, title: str, description: str) -> NotificationSeverity:
        """Determine the severity of a notification"""
        # Check explicit severity
        if 'severity' in notification:
            severity_val = notification['severity']
            if isinstance(severity_val, str):
                severity_map = {'critical': 1, 'high': 2, 'medium': 3, 'low': 4}
                severity_val = severity_map.get(severity_val.lower(), 4)

            if 1 <= severity_val <= 4:
                return NotificationSeverity(severity_val)

        # Apply classification rules
        title_lower = title.lower()
        desc_lower = description.lower()

        # Check for critical keywords
        if any(keyword in title_lower or keyword in desc_lower
               for keyword in ['critical', 'crucial', 'emergency', 'outage', 'breach', 'attack']):
            return NotificationSeverity.CRITICAL

        if any(keyword in title_lower or keyword in desc_lower
               for keyword in ['high', 'urgent', 'important', 'failure', 'error']):
            return NotificationSeverity.HIGH

        if any(keyword in title_lower or keyword in desc_lower
               for keyword in ['medium', 'moderate', 'warning', 'caution']):
            return NotificationSeverity.MEDIUM

        return NotificationSeverity.LOW

    def _generate_notification_id(self, source: str, title: str, timestamp: float) -> str:
        """Generate a unique ID for the notification"""
        content = f"{source}:{title}:{timestamp}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()[:16]

    def _determine_correlation_id(self, notification: Dict) -> Optional[str]:
        """Determine correlation ID for grouping related notifications"""
        correlation_fields = ['correlation_id', 'group_id', 'thread_id']
        for field in correlation_fields:
            if field in notification:
                return str(notification[field])

        # Generate correlation ID based on content similarity
        title = notification.get('title', '')
        source = notification.get('source', '')

        # Group by source and similar title patterns
        if len(title) > 10:  # Only for reasonably long titles
            title_base = re.sub(r'\d+', '#', title.lower())  # Replace numbers with #
            content = f"{source}:{title_base}".encode('utf-8')
            return hashlib.md5(content).hexdigest()[:12]

        return None


class NotificationCorrelator:
    """Groups related notifications together"""

    def __init__(self, config: Dict):
        self.config = config
        self.correlation_rules = config.get('correlation', {}).get('rules', {})
        self.active_groups = {}  # Store ongoing correlation groups

    def correlate_notifications(self, notifications: List[Notification]) -> List[Notification]:
        """Apply correlation rules to group related notifications"""
        # Group notifications by potential correlation factors
        correlation_buckets = defaultdict(list)

        for notification in notifications:
            # Group by correlation ID if exists
            if notification.correlation_id:
                correlation_buckets[notification.correlation_id].append(notification)
            else:
                # Create a correlation key based on source and content similarity
                correlation_key = self._create_correlation_key(notification)
                correlation_buckets[correlation_key].append(notification)

        # Apply correlation rules to each bucket
        correlated_notifications = []
        for bucket_key, bucket_notifications in correlation_buckets.items():
            if len(bucket_notifications) == 1:
                # Single notification, no correlation needed
                correlated_notifications.extend(bucket_notifications)
            else:
                # Apply correlation rules
                correlated_group = self._apply_correlation_rules(bucket_notifications)
                correlated_notifications.extend(correlated_group)

        return correlated_notifications

    def _create_correlation_key(self, notification: Notification) -> str:
        """Create a correlation key for grouping similar notifications"""
        # Use source and first 50 characters of title for grouping
        title_prefix = notification.title[:50].lower().replace(' ', '_')
        return f"{notification.source}:{title_prefix}"

    def _apply_correlation_rules(self, notifications: List[Notification]) -> List[Notification]:
        """Apply configured correlation rules to a group of notifications"""
        if len(notifications) < 2:
            return notifications

        # For now, create a summary notification for groups with more than 2 notifications
        if len(notifications) > 2:
            # Create a summary notification
            summary_title = f"Grouped Alert: {len(notifications)} related notifications"
            summary_desc = f"Multiple notifications from {notifications[0].source}:\n"
            for i, note in enumerate(notifications[:5]):  # Show first 5
                summary_desc += f"- {note.title}\n"
            if len(notifications) > 5:
                summary_desc += f"\nAnd {len(notifications) - 5} more..."

            # Use the highest severity in the group
            max_severity = min(note.severity.value for note in notifications)
            max_severity_enum = NotificationSeverity(max_severity)

            summary_notification = Notification(
                id=f"group_{hashlib.md5(summary_title.encode()).hexdigest()[:8]}",
                source=notifications[0].source,
                timestamp=max(note.timestamp for note in notifications),
                category=notifications[0].category,
                severity=max_severity_enum,
                title=summary_title,
                description=summary_desc,
                correlation_id=notifications[0].correlation_id,
                metadata={
                    'group_size': len(notifications),
                    'individual_ids': [n.id for n in notifications],
                    'original_severities': [n.severity.value for n in notifications]
                }
            )

            return [summary_notification]
        else:
            return notifications


class NotificationSupressor:
    """Suppresses duplicate or redundant notifications"""

    def __init__(self, config: Dict):
        self.config = config
        self.suppression_rules = config.get('suppression', {}).get('rules', {})
        self.recent_notifications = {}  # Cache of recent notifications
        self.suppression_cache = {}  # Cache of suppressed notifications

    def filter_notifications(self, notifications: List[Notification]) -> List[Notification]:
        """Filter out notifications that should be suppressed"""
        filtered_notifications = []

        for notification in notifications:
            if not self._should_suppress(notification):
                filtered_notifications.append(notification)
                # Add to recent notifications cache
                self._add_to_recent_cache(notification)

        return filtered_notifications

    def _should_suppress(self, notification: Notification) -> bool:
        """Determine if a notification should be suppressed"""
        # Check against recent notifications to prevent duplicates
        fingerprint = self._create_fingerprint(notification)

        # Check if this notification is a duplicate within the suppression window
        if fingerprint in self.recent_notifications:
            last_seen = self.recent_notifications[fingerprint]
            suppression_window = self.config.get('suppression_window_minutes', 10) * 60  # Convert to seconds

            if time.time() - last_seen < suppression_window:
                return True

        # Check against configured suppression rules
        for rule_name, rule_config in self.suppression_rules.items():
            if self._matches_suppression_rule(notification, rule_config):
                return True

        return False

    def _create_fingerprint(self, notification: Notification) -> str:
        """Create a fingerprint for duplicate detection"""
        content = f"{notification.source}:{notification.title}:{notification.description[:100]}"
        return hashlib.md5(content.encode()).hexdigest()

    def _matches_suppression_rule(self, notification: Notification, rule_config: Dict) -> bool:
        """Check if a notification matches a suppression rule"""
        # For now, implement basic condition matching
        conditions = rule_config.get('conditions', [])

        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')

            if field == 'category' and operator == '=':
                if notification.category.value != value:
                    return False
            elif field == 'severity' and operator == '>=':
                if notification.severity.value > value:
                    return False

        # If all conditions match, this notification should be suppressed
        return len(conditions) > 0

    def _add_to_recent_cache(self, notification: Notification):
        """Add notification to recent cache for duplicate detection"""
        fingerprint = self._create_fingerprint(notification)
        self.recent_notifications[fingerprint] = time.time()

        # Clean up old entries
        current_time = time.time()
        self.recent_notifications = {
            k: v for k, v in self.recent_notifications.items()
            if current_time - v < 3600  # Keep for 1 hour
        }


class NotificationDeliveryManager:
    """Manages delivery of notifications through various channels"""

    def __init__(self, config: Dict, notification_store: NotificationStore):
        self.config = config
        self.store = notification_store
        self.delivery_channels = {}
        self._setup_delivery_channels()

    def _setup_delivery_channels(self):
        """Setup configured delivery channels"""
        delivery_config = self.config.get('delivery', {}).get('channels', {})

        if delivery_config.get('email', {}).get('enabled', False):
            self.delivery_channels['email'] = self._setup_email_delivery(
                delivery_config['email']
            )

        if delivery_config.get('push', {}).get('firebase', {}).get('enabled', False):
            self.delivery_channels['push'] = self._setup_push_delivery(
                delivery_config['push']['firebase']
            )

        if delivery_config.get('chat', {}).get('slack', {}).get('webhook_urls', {}):
            self.delivery_channels['chat'] = self._setup_chat_delivery(
                delivery_config['chat']['slack']
            )

    def _setup_email_delivery(self, config: Dict) -> Callable:
        """Setup email delivery function"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        smtp_server = config.get('smtp_server')
        smtp_port = config.get('smtp_port', 587)
        username = config.get('username')
        password = os.getenv(config.get('password_env_var', 'SMTP_PASSWORD'))
        from_address = config.get('from_address')

        def send_email(notification: Notification):
            try:
                msg = MIMEMultipart()
                msg['From'] = from_address
                # In a real implementation, we would determine the recipient based on severity/category
                msg['To'] = "admin@company.com"  # Placeholder
                msg['Subject'] = f"[{notification.severity.name}] {notification.title}"

                body = f"""
                Notification Alert
                ==================

                Source: {notification.source}
                Category: {notification.category.value}
                Severity: {notification.severity.name}

                Title: {notification.title}

                Description:
                {notification.description}

                Timestamp: {datetime.fromtimestamp(notification.timestamp)}
                ID: {notification.id}

                This is an automated notification from the AI Employee Notification System.
                """

                msg.attach(MIMEText(body, 'plain'))

                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(username, password)
                    server.send_message(msg)

                print(f"Email sent for notification {notification.id}")
                return True
            except Exception as e:
                print(f"Failed to send email for notification {notification.id}: {e}")
                return False

        return send_email

    def _setup_push_delivery(self, config: Dict) -> Callable:
        """Setup push notification delivery function"""
        async def send_push(notification: Notification):
            try:
                # Placeholder for Firebase push notification
                print(f"Push notification sent for {notification.id}")
                return True
            except Exception as e:
                print(f"Failed to send push for notification {notification.id}: {e}")
                return False

        return send_push

    def _setup_chat_delivery(self, config: Dict) -> Callable:
        """Setup chat delivery function"""
        async def send_chat(notification: Notification):
            try:
                webhook_urls = config.get('webhook_urls', {})

                # Determine appropriate webhook based on severity
                if notification.severity == NotificationSeverity.CRITICAL:
                    webhook_url = webhook_urls.get('critical')
                elif notification.severity.value <= NotificationSeverity.HIGH.value:
                    webhook_url = webhook_urls.get('high')
                else:
                    webhook_url = webhook_urls.get('medium', webhook_urls.get('critical'))

                if webhook_url:
                    payload = {
                        "text": f"*[{notification.severity.name}]* {notification.title}",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*[{notification.severity.name}]* {notification.title}\n{notification.description}"
                                }
                            },
                            {
                                "type": "context",
                                "elements": [
                                    {
                                        "type": "mrkdwn",
                                        "text": f"Source: {notification.source} | Time: {datetime.fromtimestamp(notification.timestamp)}"
                                    }
                                ]
                            }
                        ]
                    }

                    async with aiohttp.ClientSession() as session:
                        async with session.post(webhook_url, json=payload) as response:
                            if response.status == 200:
                                print(f"Chat notification sent for {notification.id}")
                                return True
                            else:
                                print(f"Failed to send chat notification: {response.status}")
                                return False
                else:
                    print("No appropriate webhook URL found for notification severity")
                    return False

            except Exception as e:
                print(f"Failed to send chat notification for {notification.id}: {e}")
                return False

        return send_chat

    async def deliver_notification(self, notification: Notification) -> bool:
        """Deliver a notification through all configured channels"""
        success_count = 0
        total_channels = len(self.delivery_channels)

        for channel_name, delivery_func in self.delivery_channels.items():
            try:
                if asyncio.iscoroutinefunction(delivery_func):
                    result = await delivery_func(notification)
                else:
                    # For sync functions like email, run in thread pool
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, delivery_func, notification)

                if result:
                    success_count += 1
            except Exception as e:
                print(f"Error delivering notification {notification.id} via {channel_name}: {e}")

        # Mark as delivered if at least one channel succeeded
        if success_count > 0:
            self.store.mark_as_delivered(notification.id)
            return True

        return False


class NotificationAggregator:
    """Main notification aggregator class"""

    def __init__(self, config_path: str = None):
        self.config = self.load_config(config_path)
        self.store = NotificationStore()
        self.classifier = NotificationClassifier(self.config)
        self.correlator = NotificationCorrelator(self.config)
        self.suppressor = NotificationSupressor(self.config)
        self.delivery_manager = NotificationDeliveryManager(self.config, self.store)
        self.sources = {}
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=10)

    def load_config(self, config_path: str = None) -> Dict:
        """Load configuration from file"""
        default_config = {
            'processing': {
                'batch_size': 100,
                'batch_interval': 5000,  # milliseconds
                'max_workers': 10
            },
            'storage': {
                'retention_days': 30
            },
            'classification': {
                'severity_mapping': {},
                'category_mapping': {}
            },
            'correlation': {
                'rules': {},
                'window_size': 300  # seconds
            },
            'suppression': {
                'rules': {},
                'window_size': 600  # seconds
            },
            'delivery': {
                'channels': {
                    'email': {'enabled': False},
                    'push': {'enabled': False},
                    'chat': {'enabled': False}
                }
            }
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = yaml.safe_load(f)
                    # Deep merge configs
                    self._deep_merge(default_config, loaded_config)
            except Exception as e:
                print(f"Warning: Could not load config {config_path}: {e}")

        return default_config

    def _deep_merge(self, base: Dict, override: Dict):
        """Deep merge two dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def register_source(self, name: str, source_func: Callable):
        """Register a notification source"""
        self.sources[name] = source_func

    async def ingest_notifications(self):
        """Ingest notifications from all registered sources"""
        all_notifications = []

        for source_name, source_func in self.sources.items():
            try:
                # Call source function (could be sync or async)
                if asyncio.iscoroutinefunction(source_func):
                    source_notifications = await source_func()
                else:
                    source_notifications = await asyncio.get_event_loop().run_in_executor(
                        self.executor, source_func
                    )

                if source_notifications:
                    all_notifications.extend(source_notifications)
                    print(f"Ingested {len(source_notifications)} notifications from {source_name}")
            except Exception as e:
                print(f"Error ingesting notifications from {source_name}: {e}")

        return all_notifications

    def process_notifications(self, raw_notifications: List[Dict]) -> List[Notification]:
        """Process raw notifications through the pipeline"""
        # Classify notifications
        classified_notifications = []
        for raw_note in raw_notifications:
            try:
                classified = self.classifier.classify_notification(raw_note)
                classified_notifications.append(classified)
            except Exception as e:
                print(f"Error classifying notification: {e}")

        # Apply suppression rules
        filtered_notifications = self.suppressor.filter_notifications(classified_notifications)

        # Apply correlation rules
        correlated_notifications = self.correlator.correlate_notifications(filtered_notifications)

        # Save to store
        for notification in correlated_notifications:
            self.store.save_notification(notification)

        return correlated_notifications

    async def deliver_notifications(self, notifications: List[Notification]):
        """Deliver notifications through configured channels"""
        for notification in notifications:
            await self.delivery_manager.deliver_notification(notification)

    async def run_pipeline(self):
        """Run the complete notification processing pipeline"""
        # Ingest notifications from all sources
        raw_notifications = await self.ingest_notifications()

        if raw_notifications:
            # Process through pipeline
            processed_notifications = self.process_notifications(raw_notifications)

            # Deliver notifications
            await self.deliver_notifications(processed_notifications)

            print(f"Processed and delivered {len(processed_notifications)} notifications")
        else:
            print("No new notifications to process")

    async def run_continuous(self):
        """Run the aggregator continuously"""
        self.running = True
        print("Starting notification aggregator...")

        while self.running:
            try:
                await self.run_pipeline()

                # Wait before next iteration
                batch_interval = self.config['processing']['batch_interval'] / 1000.0  # Convert to seconds
                await asyncio.sleep(batch_interval)

            except KeyboardInterrupt:
                print("Received interrupt signal")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying

        print("Notification aggregator stopped")

    def stop(self):
        """Stop the aggregator"""
        self.running = False
        self.executor.shutdown(wait=True)


def main():
    """Main entry point for the notification aggregator"""
    import argparse
    import signal

    parser = argparse.ArgumentParser(description="Notification Aggregator Service")
    parser.add_argument('--config', '-c', help='Path to configuration file')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode with mock data')

    args = parser.parse_args()

    # Initialize aggregator
    aggregator = NotificationAggregator(args.config)

    # Register sample sources for testing
    if args.test_mode:
        async def mock_source():
            import random
            # Generate some mock notifications
            mock_notifications = []
            for i in range(random.randint(0, 5)):  # Random 0-5 notifications
                mock_notifications.append({
                    'source': 'mock_source',
                    'title': f'Mock Alert {i}',
                    'description': f'This is a mock notification #{i}',
                    'timestamp': time.time(),
                    'category': 'system' if random.choice([True, False]) else 'monitoring',
                    'severity': random.choice(['low', 'medium', 'high', 'critical'])
                })
            return mock_notifications

        aggregator.register_source('mock_source', mock_source)

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        aggregator.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the aggregator
    try:
        asyncio.run(aggregator.run_continuous())
    except KeyboardInterrupt:
        print("Shutting down...")


if __name__ == "__main__":
    main()