#!/usr/bin/env python3
"""
GmailWatcher: Monitors Gmail for important/unread messages using the Gmail API.

This module watches a Gmail account for new messages, applies filtering rules
to identify important communications, and triggers appropriate actions based
on predefined criteria.
"""

import os
import pickle
import json
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import base64
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.parser import HeaderParser
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import signal
import sys

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class MessagePriority(Enum):
    """Priority levels for messages."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    TRIVIAL = 1


class MessageCategory(Enum):
    """Categories for classifying messages."""
    URGENT = "urgent"
    MEETING = "meeting"
    FINANCIAL = "financial"
    SECURITY = "security"
    BUSINESS = "business"
    CUSTOMER = "customer"
    PERSONAL = "personal"
    NEWSLETTER = "newsletter"
    SOCIAL = "social"
    NOTIFICATION = "notification"
    SPAM = "spam"


@dataclass
class WatchedMessage:
    """Represents a watched message."""
    id: str
    thread_id: str
    subject: str
    sender: str
    recipient: str
    date: datetime
    snippet: str
    body: str
    labels: List[str]
    attachments: List[Dict[str, Any]]
    priority: MessagePriority
    category: MessageCategory
    processed: bool = False
    action_taken: Optional[str] = None
    created_at: datetime = datetime.now()


class GmailWatcher:
    """
    Gmail watcher that monitors for important messages and applies processing rules.

    Features:
    - OAuth 2.0 authentication with Gmail API
    - Smart filtering for important messages
    - Priority-based processing
    - Action triggering based on content
    - Message categorization
    - Persistent tracking of processed messages
    """

    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
              'https://www.googleapis.com/auth/gmail.modify']

    def __init__(self, credentials_path: str = "credentials.json",
                 token_path: str = "token.pickle",
                 db_path: str = "./gmail_watcher.db"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.db_path = db_path
        self.service = None
        self.running = False

        # Initialize database
        self.setup_database()

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('gmail_watcher.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Define trigger patterns
        self.trigger_keywords = {
            MessageCategory.URGENT: [
                'urgent', 'asap', 'immediately', 'critical', 'emergency',
                'attention required', 'action required', 'high priority'
            ],
            MessageCategory.MEETING: [
                'calendar invitation', 'meeting request', 'schedule',
                'appointment', 'conference', 'call scheduled'
            ],
            MessageCategory.FINANCIAL: [
                'invoice', 'payment', 'billing', 'charge', 'receipt',
                'purchase', 'transaction', 'banking', 'account'
            ],
            MessageCategory.SECURITY: [
                'login', 'security', 'suspicious', 'unauthorized',
                'compromised', 'password', 'authentication'
            ],
            MessageCategory.BUSINESS: [
                'proposal', 'contract', 'agreement', 'partnership',
                'collaboration', 'deal', 'negotiation'
            ],
            MessageCategory.CUSTOMER: [
                'customer', 'client', 'support', 'feedback',
                'complaint', 'review', 'satisfaction'
            ]
        }

        # Define sender patterns
        self.sender_patterns = {
            'vip_contacts': [],  # Will be populated based on user config
            'corporate_domains': ['.com', '.org', '.gov', '.edu'],  # Common corporate domains
            'blacklisted_senders': []  # Will be populated based on user config
        }

    def setup_database(self):
        """Initialize the database schema for message tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watched_messages (
                id TEXT PRIMARY KEY,
                thread_id TEXT,
                subject TEXT,
                sender TEXT,
                recipient TEXT,
                date DATETIME,
                snippet TEXT,
                body TEXT,
                labels_json TEXT,
                attachments_json TEXT,
                priority INTEGER,
                category TEXT,
                processed BOOLEAN DEFAULT FALSE,
                action_taken TEXT,
                created_at DATETIME,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create processing_rules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                condition_json TEXT,
                action_json TEXT,
                priority INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create message_history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT,
                action_taken TEXT,
                result TEXT,
                executed_at DATETIME,
                FOREIGN KEY (message_id) REFERENCES watched_messages (id)
            )
        ''')

        conn.commit()
        conn.close()

    def authenticate(self):
        """Authenticate with Gmail API using OAuth 2.0."""
        creds = None

        # Load existing token
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, request new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    self.logger.error(f"Failed to refresh token: {e}")
                    # Delete the stored token and re-authenticate
                    os.remove(self.token_path)

            if not creds or not creds.valid:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(f"Credentials file not found: {self.credentials_path}")

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('gmail', 'v1', credentials=creds)
        self.logger.info("Successfully authenticated with Gmail API")

    def get_recent_messages(self, max_results: int = 10, days_back: int = 1) -> List[Dict[str, Any]]:
        """Get recent unread messages from Gmail."""
        if not self.service:
            self.authenticate()

        try:
            # Calculate date threshold
            since_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')

            # Query for unread messages
            query = f'is:unread after:{since_date}'
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            detailed_messages = []

            for msg in messages:
                try:
                    # Get full message details
                    full_msg = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()

                    detailed_messages.append(full_msg)
                except HttpError as e:
                    self.logger.error(f"Failed to retrieve message {msg['id']}: {e}")
                    continue

            self.logger.info(f"Retrieved {len(detailed_messages)} recent messages")
            return detailed_messages

        except HttpError as e:
            self.logger.error(f"Gmail API error: {e}")
            return []

    def extract_message_details(self, msg: Dict[str, Any]) -> Optional[WatchedMessage]:
        """Extract relevant details from a Gmail message."""
        try:
            headers = {header['name'].lower(): header['value']
                      for header in msg.get('payload', {}).get('headers', [])}

            # Extract basic information
            msg_id = msg['id']
            thread_id = msg['threadId']
            subject = headers.get('subject', 'No Subject')
            sender = headers.get('from', 'Unknown Sender')
            recipient = headers.get('to', 'Unknown Recipient')
            date_str = headers.get('date', '')

            try:
                # Parse date - Gmail date format: "Mon, 2 Sep 2024 10:30:00 +0000"
                date_obj = datetime.strptime(date_str.split('(')[0].strip(), '%a, %d %b %Y %H:%M:%S %z')
            except ValueError:
                # Fallback if timezone info is missing
                try:
                    date_obj = datetime.strptime(date_str.split('(')[0].strip(), '%a, %d %b %Y %H:%M:%S')
                except ValueError:
                    date_obj = datetime.now()

            snippet = msg.get('snippet', '')

            # Extract body content
            body = self._extract_body_content(msg)

            # Extract labels
            labels = msg.get('labelIds', [])

            # Extract attachments
            attachments = self._extract_attachments(msg)

            # Categorize and prioritize the message
            category = self._categorize_message(subject, body, sender)
            priority = self._determine_priority(category, subject, body, sender)

            return WatchedMessage(
                id=msg_id,
                thread_id=thread_id,
                subject=subject,
                sender=sender,
                recipient=recipient,
                date=date_obj,
                snippet=snippet,
                body=body,
                labels=labels,
                attachments=attachments,
                priority=priority,
                category=category
            )

        except Exception as e:
            self.logger.error(f"Error extracting message details: {e}")
            return None

    def _extract_body_content(self, msg: Dict[str, Any]) -> str:
        """Extract body content from message payload."""
        body = ""

        # Handle different message payload structures
        payload = msg.get('payload', {})

        # If it's a multipart message
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    body_data = part.get('body', {}).get('data', '')
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
                elif part.get('mimeType') == 'text/html':
                    # Fallback to HTML if plain text not available
                    body_data = part.get('body', {}).get('data', '')
                    if body_data:
                        import html
                        html_content = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        body = html.unescape(html_content)
        else:
            # Simple message
            body_data = payload.get('body', {}).get('data', '')
            if body_data:
                body = base64.urlsafe_b64decode(body_data).decode('utf-8')

        return body

    def _extract_attachments(self, msg: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachment information from message."""
        attachments = []

        payload = msg.get('payload', {})

        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('filename'):  # This indicates an attachment
                    attachment = {
                        'filename': part['filename'],
                        'mimeType': part.get('mimeType', 'application/octet-stream'),
                        'size': part.get('body', {}).get('size', 0),
                        'attachmentId': part.get('body', {}).get('attachmentId')
                    }
                    attachments.append(attachment)

        return attachments

    def _categorize_message(self, subject: str, body: str, sender: str) -> MessageCategory:
        """Categorize a message based on its content."""
        content = f"{subject} {body}".lower()

        # Check for each category based on keywords
        for category, keywords in self.trigger_keywords.items():
            for keyword in keywords:
                if keyword.lower() in content:
                    return category

        # Check for VIP senders
        if any(vip in sender.lower() for vip in self.sender_patterns['vip_contacts']):
            return MessageCategory.BUSINESS  # Or another high-priority category

        # Check for corporate domains
        sender_domain = sender.split('@')[-1].lower() if '@' in sender else ''
        if any(domain in sender_domain for domain in self.sender_patterns['corporate_domains']):
            return MessageCategory.BUSINESS

        # Default categories based on common patterns
        if 'newsletter' in content or 'unsubscribe' in content:
            return MessageCategory.NEWSLETTER

        if any(social in content for social in ['facebook', 'twitter', 'linkedin', 'instagram']):
            return MessageCategory.SOCIAL

        if any(notification in content for notification in ['update', 'alert', 'notification']):
            return MessageCategory.NOTIFICATION

        # Default to personal if no other category matches
        return MessageCategory.PERSONAL

    def _determine_priority(self, category: MessageCategory, subject: str, body: str, sender: str) -> MessagePriority:
        """Determine priority level for a message."""
        # Start with category-based priority
        category_priority = {
            MessageCategory.URGENT: MessagePriority.CRITICAL,
            MessageCategory.SECURITY: MessagePriority.HIGH,
            MessageCategory.FINANCIAL: MessagePriority.HIGH,
            MessageCategory.MEETING: MessagePriority.MEDIUM,
            MessageCategory.BUSINESS: MessagePriority.MEDIUM,
            MessageCategory.CUSTOMER: MessagePriority.MEDIUM,
            MessageCategory.PERSONAL: MessagePriority.LOW,
            MessageCategory.NEWSLETTER: MessagePriority.TRIVIAL,
            MessageCategory.SOCIAL: MessagePriority.TRIVIAL,
            MessageCategory.NOTIFICATION: MessagePriority.LOW,
            MessageCategory.SPAM: MessagePriority.TRIVIAL
        }

        priority = category_priority.get(category, MessagePriority.LOW)

        # Boost priority based on specific content
        content = f"{subject} {body}".lower()

        # Critical keywords boost to highest priority
        if any(word in content for word in ['breach', 'security incident', 'compromise', 'attack', 'malware']):
            return MessagePriority.CRITICAL

        if any(word in content for word in ['payment failure', 'account suspended', 'service interruption']):
            priority = max(priority, MessagePriority.HIGH)

        # VIP sender gets priority boost
        if any(vip in sender.lower() for vip in self.sender_patterns['vip_contacts']):
            priority = max(priority, MessagePriority.HIGH)

        return priority

    def process_message(self, message: WatchedMessage) -> str:
        """Process a message according to rules and return action taken."""
        # Check if already processed
        if self.is_message_processed(message.id):
            return "already_processed"

        # Apply processing rules
        action_taken = self.apply_processing_rules(message)

        # Mark as processed
        self.mark_message_processed(message.id, action_taken)

        self.logger.info(f"Processed message '{message.subject}' with action: {action_taken}")
        return action_taken

    def apply_processing_rules(self, message: WatchedMessage) -> str:
        """Apply configured processing rules to a message."""
        # Default actions based on priority and category
        if message.priority == MessagePriority.CRITICAL:
            return self.handle_critical_message(message)
        elif message.category == MessageCategory.SECURITY:
            return self.handle_security_message(message)
        elif message.category == MessageCategory.FINANCIAL:
            return self.handle_financial_message(message)
        elif message.category == MessageCategory.MEETING:
            return self.handle_meeting_message(message)
        else:
            return self.handle_standard_message(message)

    def handle_critical_message(self, message: WatchedMessage) -> str:
        """Handle critical priority messages."""
        # For critical messages, always flag and notify
        self.add_label_to_message(message.id, 'IMPORTANT')
        self.logger.warning(f"Critical message detected: {message.subject}")
        return "flagged_and_notified"

    def handle_security_message(self, message: WatchedMessage) -> str:
        """Handle security-related messages."""
        # Flag for security review
        self.add_label_to_message(message.id, 'IMPORTANT')
        self.logger.warning(f"Security-related message: {message.subject}")
        return "security_review"

    def handle_financial_message(self, message: WatchedMessage) -> str:
        """Handle financial messages."""
        # Flag for financial review
        self.add_label_to_message(message.id, 'FINANCE')
        self.logger.info(f"Financial message: {message.subject}")
        return "finance_review"

    def handle_meeting_message(self, message: WatchedMessage) -> str:
        """Handle meeting invitations."""
        # Add to calendar processing queue
        self.add_label_to_message(message.id, 'MEETING')
        self.logger.info(f"Meeting invitation: {message.subject}")
        return "calendar_invite"

    def handle_standard_message(self, message: WatchedMessage) -> str:
        """Handle standard messages."""
        # Apply standard processing based on category
        if message.category == MessageCategory.NEWSLETTER:
            # Auto-archive newsletters
            self.add_label_to_message(message.id, 'CATEGORY_UPDATES')
            return "archived"
        elif message.category == MessageCategory.SOCIAL:
            # Mark social notifications appropriately
            self.add_label_to_message(message.id, 'CATEGORY_SOCIAL')
            return "labeled_social"
        else:
            # Standard processing - just mark as read
            return "marked_read"

    def add_label_to_message(self, msg_id: str, label_name: str) -> bool:
        """Add a label to a message."""
        if not self.service:
            self.authenticate()

        try:
            # First, get the label ID
            labels_response = self.service.users().labels().list(userId='me').execute()
            labels = labels_response.get('labels', [])

            label_id = None
            for label in labels:
                if label['name'] == label_name:
                    label_id = label['id']
                    break

            # If label doesn't exist, create it
            if not label_id:
                label_body = {
                    'name': label_name,
                    'messageListVisibility': 'show',
                    'labelListVisibility': 'labelShow'
                }
                created_label = self.service.users().labels().create(
                    userId='me', body=label_body).execute()
                label_id = created_label['id']

            # Add the label to the message
            body = {
                'addLabelIds': [label_id]
            }

            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body=body
            ).execute()

            return True

        except HttpError as e:
            self.logger.error(f"Failed to add label to message {msg_id}: {e}")
            return False

    def is_message_processed(self, msg_id: str) -> bool:
        """Check if a message has already been processed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM watched_messages WHERE id = ? AND processed = TRUE', (msg_id,))
        count = cursor.fetchone()[0]

        conn.close()
        return count > 0

    def mark_message_processed(self, msg_id: str, action_taken: str) -> bool:
        """Mark a message as processed in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE watched_messages
            SET processed = TRUE, action_taken = ?, updated_at = ?
            WHERE id = ?
        ''', (action_taken, datetime.now().isoformat(), msg_id))

        # Also log to message history
        cursor.execute('''
            INSERT INTO message_history (message_id, action_taken, result, executed_at)
            VALUES (?, ?, ?, ?)
        ''', (msg_id, action_taken, 'success', datetime.now().isoformat()))

        conn.commit()
        conn.close()

        return True

    def save_watched_message(self, message: WatchedMessage) -> bool:
        """Save a watched message to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO watched_messages
            (id, thread_id, subject, sender, recipient, date, snippet, body,
             labels_json, attachments_json, priority, category, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message.id, message.thread_id, message.subject, message.sender,
            message.recipient, message.date.isoformat(), message.snippet,
            message.body, json.dumps(message.labels), json.dumps(message.attachments),
            message.priority.value, message.category.value,
            message.created_at.isoformat()
        ))

        conn.commit()
        conn.close()

        return True

    def start_monitoring(self, poll_interval: int = 60, max_messages: int = 10):
        """Start monitoring Gmail for new messages."""
        self.running = True

        def signal_handler(sig, frame):
            self.logger.info("Stopping Gmail watcher...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        self.logger.info(f"Starting Gmail monitoring (polling every {poll_interval}s)")

        while self.running:
            try:
                # Get recent messages
                messages = self.get_recent_messages(max_results=max_messages)

                for msg_data in messages:
                    # Extract message details
                    message = self.extract_message_details(msg_data)

                    if message:
                        # Save to database
                        self.save_watched_message(message)

                        # Process the message
                        action = self.process_message(message)

                        self.logger.debug(f"Action taken for '{message.subject}': {action}")

                # Wait before next poll
                time.sleep(poll_interval)

            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                self.logger.error(f"Error during monitoring: {e}")
                time.sleep(poll_interval)  # Wait before retrying

        self.logger.info("Gmail monitoring stopped")

    def get_unprocessed_messages(self) -> List[WatchedMessage]:
        """Get all unprocessed messages from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, thread_id, subject, sender, recipient, date, snippet, body,
                   labels_json, attachments_json, priority, category, processed, action_taken, created_at
            FROM watched_messages
            WHERE processed = FALSE
            ORDER BY date DESC
        ''')

        messages = []
        for row in cursor.fetchall():
            try:
                message = WatchedMessage(
                    id=row[0], thread_id=row[1], subject=row[2], sender=row[3],
                    recipient=row[4], date=datetime.fromisoformat(row[5]),
                    snippet=row[6], body=row[7], labels=json.loads(row[8]),
                    attachments=json.loads(row[9]) if row[8] else [],
                    priority=MessagePriority(row[10]), category=MessageCategory(row[11]),
                    processed=bool(row[12]), action_taken=row[13],
                    created_at=datetime.fromisoformat(row[14]) if row[14] else datetime.now()
                )
                messages.append(message)
            except Exception as e:
                self.logger.error(f"Error parsing message from DB: {e}")
                continue

        conn.close()
        return messages

    def get_message_statistics(self) -> Dict[str, Any]:
        """Get statistics about processed messages."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total messages
        cursor.execute('SELECT COUNT(*) FROM watched_messages')
        total_messages = cursor.fetchone()[0]

        # Processed messages
        cursor.execute('SELECT COUNT(*) FROM watched_messages WHERE processed = TRUE')
        processed_messages = cursor.fetchone()[0]

        # Messages by category
        cursor.execute('''
            SELECT category, COUNT(*)
            FROM watched_messages
            GROUP BY category
        ''')
        category_counts = dict(cursor.fetchall())

        # Messages by priority
        cursor.execute('''
            SELECT priority, COUNT(*)
            FROM watched_messages
            GROUP BY priority
        ''')
        priority_counts = dict(cursor.fetchall())

        conn.close()

        return {
            'total_messages': total_messages,
            'processed_messages': processed_messages,
            'unprocessed_messages': total_messages - processed_messages,
            'category_breakdown': category_counts,
            'priority_breakdown': priority_counts
        }


def main():
    """Main function for running the Gmail watcher."""
    import argparse

    parser = argparse.ArgumentParser(description='Gmail Watcher')
    parser.add_argument('--credentials', default='credentials.json', help='Path to credentials.json file')
    parser.add_argument('--token', default='token.pickle', help='Path to token.pickle file')
    parser.add_argument('--db-path', default='./gmail_watcher.db', help='Path to database file')
    parser.add_argument('--poll-interval', type=int, default=60, help='Polling interval in seconds')
    parser.add_argument('--max-messages', type=int, default=10, help='Max messages to process per poll')
    parser.add_argument('--demo', action='store_true', help='Run in demo mode without actual API calls')

    args = parser.parse_args()

    if args.demo:
        # Demo mode - just show the structure without connecting to Gmail
        print("Gmail Watcher Demo Mode")
        print("=" * 30)
        print(f"Credentials file: {args.credentials}")
        print(f"Token file: {args.token}")
        print(f"Database: {args.db_path}")
        print(f"Poll interval: {args.poll_interval}s")
        print(f"Max messages: {args.max_messages}")
        print("\nThis would monitor your Gmail account for important messages")
        print("and apply processing rules based on content and sender.")

        # Create a sample message for demonstration
        watcher = GmailWatcher(credentials_path=args.credentials,
                             token_path=args.token,
                             db_path=args.db_path)

        print("\nSample message processing:")
        print("- Categorizing messages based on content")
        print("- Applying priority levels (Critical, High, Medium, Low, Trivial)")
        print("- Taking actions based on message category")
        print("- Tracking processed messages in database")

    else:
        # Initialize and start the watcher
        watcher = GmailWatcher(credentials_path=args.credentials,
                             token_path=args.token,
                             db_path=args.db_path)

        try:
            watcher.start_monitoring(
                poll_interval=args.poll_interval,
                max_messages=args.max_messages
            )
        except Exception as e:
            print(f"Error starting Gmail watcher: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()