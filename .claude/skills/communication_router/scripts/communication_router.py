#!/usr/bin/env python3
"""
Communication Router

This module provides intelligent routing and management of communication flows for the Personal AI Employee system.
It handles incoming and outgoing messages, routes them to appropriate destinations based on content, context, and rules,
and manages various communication channels including email, SMS, chat, and API endpoints.

Features:
- Multi-channel message routing
- Content analysis and categorization
- Rule-based message processing
- Security scanning and filtering
- Message transformation and formatting
- Delivery status tracking
- Rate limiting and throttling
- Audit logging and compliance
"""

import json
import os
import sqlite3
import logging
import threading
import time
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests
import hashlib
import socket
import ssl


class ChannelType(Enum):
    """Types of communication channels."""
    EMAIL = "email"
    SMS = "sms"
    CHAT = "chat"
    API = "api"
    INTERNAL = "internal"


class MessagePriority(Enum):
    """Priority levels for messages."""
    LOW = 100
    NORMAL = 50
    HIGH = 10
    URGENT = 1


class MessageStatus(Enum):
    """Status of message processing."""
    RECEIVED = "received"
    ROUTED = "routed"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    FILTERED = "filtered"


@dataclass
class MessageInfo:
    """Data class to hold message information."""
    id: str
    source_channel: ChannelType
    destination_channel: ChannelType
    content: str
    message_type: str  # text, image, document, structured_data
    priority: MessagePriority
    routing_rules_applied: List[Dict[str, Any]]
    context: Dict[str, Any]
    metadata: Dict[str, Any]
    status: MessageStatus
    created_at: str
    processed_at: Optional[str] = None
    delivered_at: Optional[str] = None
    error_message: Optional[str] = None
    transformed_content: Optional[str] = None


class MessageRouter:
    """Routes messages based on rules and context."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('MessageRouter')

    def route_message(self, message: MessageInfo) -> MessageInfo:
        """Apply routing rules to determine destination."""
        # Apply routing rules from configuration
        routing_rules = self.config.get('routing_rules', {}).get('rules', [])

        for rule in routing_rules:
            if self._evaluate_rule(rule, message):
                action = rule.get('action', {})

                # Update destination if specified
                if 'route_to' in action:
                    try:
                        message.destination_channel = ChannelType(action['route_to'])
                    except ValueError:
                        self.logger.warning(f"Invalid channel type: {action['route_to']}")

                # Update priority if specified
                if 'priority' in action:
                    try:
                        message.priority = MessagePriority[action['priority'].upper()]
                    except KeyError:
                        self.logger.warning(f"Invalid priority: {action['priority']}")

                # Add rule to applied rules
                message.routing_rules_applied.append(rule)

        # Apply default route if no specific route was determined
        if message.destination_channel == ChannelType.INTERNAL:
            default_route = self.config.get('routing_rules', {}).get('default_route', 'email')
            try:
                message.destination_channel = ChannelType(default_route)
            except ValueError:
                self.logger.warning(f"Invalid default route: {default_route}")

        return message

    def _evaluate_rule(self, rule: Dict[str, Any], message: MessageInfo) -> bool:
        """Evaluate if a rule applies to a message."""
        condition = rule.get('condition', {})

        if condition.get('type') == 'time_range':
            return self._evaluate_time_range(condition, message)
        else:
            return self._evaluate_field_condition(condition, message)

    def _evaluate_time_range(self, condition: Dict[str, Any], message: MessageInfo) -> bool:
        """Evaluate time range condition."""
        from datetime import datetime, time
        import pytz

        tz = pytz.timezone(condition.get('timezone', 'UTC'))
        now = datetime.now(tz).time()

        start_time = datetime.strptime(condition['start_time'], '%H:%M').time()
        end_time = datetime.strptime(condition['end_time'], '%H:%M').time()

        return start_time <= now <= end_time

    def _evaluate_field_condition(self, condition: Dict[str, Any], message: MessageInfo) -> bool:
        """Evaluate field-based condition."""
        field = condition.get('field', '')
        operator = condition.get('operator', '')
        values = condition.get('values', [])

        # Get the field value from message
        field_value = self._get_field_value(field, message)

        if operator == 'contains_any' and isinstance(field_value, str):
            field_lower = field_value.lower()
            for value in values:
                if value.lower() in field_lower:
                    return True
            return False
        elif operator == 'equals' and isinstance(field_value, str):
            return field_value.lower() == values[0].lower()
        elif operator == 'starts_with' and isinstance(field_value, str):
            return field_value.startswith(values[0])
        elif operator == 'ends_with' and isinstance(field_value, str):
            return field_value.endswith(values[0])

        return False

    def _get_field_value(self, field: str, message: MessageInfo) -> str:
        """Get field value from message."""
        if field == 'content':
            return message.content
        elif field == 'source_channel':
            return message.source_channel.value
        elif field == 'priority':
            return message.priority.name.lower()
        else:
            # Try to get from context
            return str(message.context.get(field, ''))


class MessageProcessor:
    """Processes messages for transformation and security."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('MessageProcessor')

    def process_message(self, message: MessageInfo) -> MessageInfo:
        """Process message for transformation and security."""
        try:
            # Apply content filtering
            if not self._apply_content_filters(message):
                message.status = MessageStatus.FILTERED
                message.error_message = "Message filtered by security policies"
                return message

            # Transform content based on destination
            message.transformed_content = self._transform_content(
                message.content,
                message.source_channel,
                message.destination_channel
            )

            # Apply format conversion if configured
            content_processing = self.config.get('content_processing', {})
            if content_processing.get('format_conversion', {}).get('markdown_to_html', False):
                message.transformed_content = self._convert_markdown_to_html(message.transformed_content)

            message.status = MessageStatus.PROCESSING
            message.processed_at = datetime.now().isoformat()

            return message
        except Exception as e:
            message.status = MessageStatus.FAILED
            message.error_message = str(e)
            self.logger.error(f"Error processing message {message.id}: {e}")
            return message

    def _apply_content_filters(self, message: MessageInfo) -> bool:
        """Apply content filters to the message."""
        content_filtering = self.config.get('content_processing', {}).get('content_filtering', {})

        # Profanity filter
        if content_filtering.get('profanity_filter', {}).get('enabled', False):
            replacement = content_filtering['profanity_filter'].get('replacement_text', '[FILTERED]')
            # Simple profanity filter - in a real system, use a proper library
            message.content = re.sub(r'\b(badword1|badword2)\b', replacement, message.content, flags=re.IGNORECASE)

        # Check for security policies
        security_processing = self.config.get('security_processing', {})
        dlp_policies = security_processing.get('data_loss_prevention', {}).get('policies', [])

        for policy in dlp_policies:
            pattern = policy.get('pattern', '')
            if re.search(pattern, message.content):
                action = policy.get('action', 'block_and_alert')
                if action == 'block_and_alert':
                    self.logger.warning(f"DLP policy triggered for message {message.id}: {policy.get('name')}")
                    return False
                elif action == 'encrypt_and_notify':
                    # Mark for encryption but allow through
                    message.context['needs_encryption'] = True

        return True

    def _transform_content(self, content: str, source_channel: ChannelType, destination_channel: ChannelType) -> str:
        """Transform content based on source and destination channels."""
        # Add channel-specific formatting
        if destination_channel == ChannelType.EMAIL:
            # Format for email
            transformed = f"Message from {source_channel.value} channel:\n\n{content}"
        elif destination_channel == ChannelType.SMS:
            # Format for SMS (shorter, simpler)
            transformed = content[:160]  # SMS character limit
        elif destination_channel == ChannelType.CHAT:
            # Format for chat
            transformed = f"*New message from {source_channel.value}:*\n{content}"
        else:
            # Default transformation
            transformed = content

        return transformed

    def _convert_markdown_to_html(self, content: str) -> str:
        """Convert markdown to HTML."""
        # Simple markdown to HTML conversion
        html = content.replace('\n\n', '<br><br>')
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
        html = re.sub(r'# (.*?)\n', r'<h1>\1</h1>', html)
        html = re.sub(r'## (.*?)\n', r'<h2>\1</h2>', html)
        return html


class ChannelManager:
    """Manages different communication channels."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('ChannelManager')

    def send_message(self, message: MessageInfo) -> bool:
        """Send message through the appropriate channel."""
        try:
            if message.destination_channel == ChannelType.EMAIL:
                return self._send_email(message)
            elif message.destination_channel == ChannelType.SMS:
                return self._send_sms(message)
            elif message.destination_channel == ChannelType.CHAT:
                return self._send_chat(message)
            elif message.destination_channel == ChannelType.API:
                return self._send_api(message)
            else:
                self.logger.error(f"Unsupported destination channel: {message.destination_channel}")
                return False
        except Exception as e:
            self.logger.error(f"Error sending message {message.id} via {message.destination_channel}: {e}")
            return False

    def _send_email(self, message: MessageInfo) -> bool:
        """Send email message."""
        try:
            channel_config = self.config.get('channels', {}).get('email', {})

            if not channel_config.get('enabled', False):
                self.logger.warning("Email channel is disabled")
                return False

            smtp_config = channel_config.get('smtp', {})
            server = smtplib.SMTP(smtp_config.get('server', 'localhost'), smtp_config.get('port', 587))

            if smtp_config.get('use_tls', False):
                server.starttls()

            server.login(
                os.getenv(smtp_config.get('username_env_var', ''), ''),
                os.getenv(smtp_config.get('password_env_var', ''), '')
            )

            # Create message
            msg = MIMEMultipart()
            msg['From'] = smtp_config.get('sender_email', 'noreply@example.com')
            msg['To'] = message.context.get('recipient_email', '')
            msg['Subject'] = message.context.get('subject', 'Automated Message')

            # Add body
            body = message.transformed_content or message.content
            msg.attach(MIMEText(body, 'html' if '<' in body else 'plain'))

            # Send email
            server.send_message(msg)
            server.quit()

            self.logger.info(f"Email sent successfully to {msg['To']}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False

    def _send_sms(self, message: MessageInfo) -> bool:
        """Send SMS message."""
        try:
            channel_config = self.config.get('channels', {}).get('sms', {})

            if not channel_config.get('enabled', False):
                self.logger.warning("SMS channel is disabled")
                return False

            provider = channel_config.get('provider', 'twilio')

            if provider == 'twilio':
                return self._send_twilio_sms(message)
            else:
                self.logger.error(f"Unsupported SMS provider: {provider}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to send SMS: {e}")
            return False

    def _send_twilio_sms(self, message: MessageInfo) -> bool:
        """Send SMS via Twilio."""
        try:
            import requests

            account_sid = os.getenv(self.config.get('channels', {}).get('sms', {}).get('twilio', {}).get('account_sid_env_var', ''))
            auth_token = os.getenv(self.config.get('channels', {}).get('sms', {}).get('twilio', {}).get('auth_token_env_var', ''))
            from_number = self.config.get('channels', {}).get('sms', {}).get('twilio', {}).get('from_phone_number', '')

            if not account_sid or not auth_token:
                self.logger.error("Twilio credentials not configured")
                return False

            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

            data = {
                'From': from_number,
                'To': message.context.get('recipient_phone', ''),
                'Body': message.transformed_content or message.content
            }

            response = requests.post(url, data=data, auth=(account_sid, auth_token))

            if response.status_code == 201:
                self.logger.info(f"SMS sent successfully to {message.context.get('recipient_phone', '')}")
                return True
            else:
                self.logger.error(f"Failed to send SMS: {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to send Twilio SMS: {e}")
            return False

    def _send_chat(self, message: MessageInfo) -> bool:
        """Send chat message."""
        try:
            channel_config = self.config.get('channels', {}).get('chat', {})

            if not channel_config.get('enabled', False):
                self.logger.warning("Chat channel is disabled")
                return False

            platform = message.context.get('chat_platform', 'slack')

            if platform == 'slack':
                return self._send_slack_message(message)
            else:
                self.logger.error(f"Unsupported chat platform: {platform}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to send chat message: {e}")
            return False

    def _send_slack_message(self, message: MessageInfo) -> bool:
        """Send message to Slack."""
        try:
            webhook_url = os.getenv(self.config.get('channels', {}).get('chat', {}).get('platforms', {}).get('slack', {}).get('webhook_url_env_var', ''))

            if not webhook_url:
                self.logger.error("Slack webhook URL not configured")
                return False

            payload = {
                'text': message.transformed_content or message.content,
                'channel': message.context.get('chat_channel', '#general'),
                'username': message.context.get('sender_name', 'AI Assistant'),
                'icon_emoji': ':robot_face:'
            }

            response = requests.post(webhook_url, json=payload)

            if response.status_code == 200:
                self.logger.info(f"Slack message sent successfully to {payload['channel']}")
                return True
            else:
                self.logger.error(f"Failed to send Slack message: {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to send Slack message: {e}")
            return False

    def _send_api(self, message: MessageInfo) -> bool:
        """Send message via API."""
        try:
            # Extract API endpoint and method from context
            api_endpoint = message.context.get('api_endpoint', '')
            api_method = message.context.get('api_method', 'POST').upper()
            api_headers = message.context.get('api_headers', {})

            if not api_endpoint:
                self.logger.error("API endpoint not specified in context")
                return False

            # Prepare request data
            data = {
                'message_id': message.id,
                'content': message.transformed_content or message.content,
                'source_channel': message.source_channel.value,
                'timestamp': message.created_at,
                'metadata': message.metadata
            }

            # Make API request
            if api_method == 'GET':
                response = requests.get(api_endpoint, params=data, headers=api_headers)
            elif api_method == 'POST':
                response = requests.post(api_endpoint, json=data, headers=api_headers)
            elif api_method == 'PUT':
                response = requests.put(api_endpoint, json=data, headers=api_headers)
            elif api_method == 'DELETE':
                response = requests.delete(api_endpoint, json=data, headers=api_headers)
            else:
                self.logger.error(f"Unsupported API method: {api_method}")
                return False

            if response.status_code in [200, 201, 202]:
                self.logger.info(f"API message sent successfully to {api_endpoint}")
                return True
            else:
                self.logger.error(f"Failed to send API message: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to send API message: {e}")
            return False


class MessageRegistry:
    """Manages the message registry database."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables."""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    source_channel TEXT NOT NULL,
                    destination_channel TEXT NOT NULL,
                    content TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    routing_rules_applied TEXT,
                    context TEXT,
                    metadata TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    processed_at TEXT,
                    delivered_at TEXT,
                    error_message TEXT,
                    transformed_content TEXT
                )
            ''')

    @contextmanager
    def get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def add_message(self, message_info: MessageInfo):
        """Add a message to the registry."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO messages
                (id, source_channel, destination_channel, content, message_type,
                 priority, routing_rules_applied, context, metadata, status,
                 created_at, processed_at, delivered_at, error_message, transformed_content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message_info.id, message_info.source_channel.value,
                message_info.destination_channel.value, message_info.content,
                message_info.message_type, message_info.priority.name,
                json.dumps(message_info.routing_rules_applied),
                json.dumps(message_info.context), json.dumps(message_info.metadata),
                message_info.status.name, message_info.created_at,
                message_info.processed_at, message_info.delivered_at,
                message_info.error_message, message_info.transformed_content
            ))

    def update_message_status(self, message_id: str, status: MessageStatus, delivered_at: str = None, error_message: str = None):
        """Update message status in the registry."""
        with self.get_connection() as conn:
            update_fields = []
            params = []

            update_fields.append("status = ?")
            params.append(status.name)

            if delivered_at:
                update_fields.append("delivered_at = ?")
                params.append(delivered_at)

            if error_message:
                update_fields.append("error_message = ?")
                params.append(error_message)

            params.append(message_id)

            query = f"UPDATE messages SET {', '.join(update_fields)} WHERE id = ?"
            conn.execute(query, params)

    def get_message_by_id(self, message_id: str) -> Optional[MessageInfo]:
        """Get a message by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, source_channel, destination_channel, content, message_type,
                       priority, routing_rules_applied, context, metadata, status,
                       created_at, processed_at, delivered_at, error_message, transformed_content
                FROM messages WHERE id = ?
            ''', (message_id,))
            row = cursor.fetchone()
            if row:
                return MessageInfo(
                    id=row[0], source_channel=ChannelType(row[1]), destination_channel=ChannelType(row[2]),
                    content=row[3], message_type=row[4], priority=MessagePriority[row[5]],
                    routing_rules_applied=json.loads(row[6]) if row[6] else [],
                    context=json.loads(row[7]) if row[7] else {},
                    metadata=json.loads(row[8]) if row[8] else {},
                    status=MessageStatus[row[9]], created_at=row[10],
                    processed_at=row[11], delivered_at=row[12],
                    error_message=row[13], transformed_content=row[14]
                )
        return None

    def get_messages_by_status(self, status: MessageStatus) -> List[MessageInfo]:
        """Get messages by status."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, source_channel, destination_channel, content, message_type,
                       priority, routing_rules_applied, context, metadata, status,
                       created_at, processed_at, delivered_at, error_message, transformed_content
                FROM messages WHERE status = ?
            ''', (status.name,))
            rows = cursor.fetchall()
            messages = []
            for row in rows:
                messages.append(MessageInfo(
                    id=row[0], source_channel=ChannelType(row[1]), destination_channel=ChannelType(row[2]),
                    content=row[3], message_type=row[4], priority=MessagePriority[row[5]],
                    routing_rules_applied=json.loads(row[6]) if row[6] else [],
                    context=json.loads(row[7]) if row[7] else {},
                    metadata=json.loads(row[8]) if row[8] else {},
                    status=MessageStatus[row[9]], created_at=row[10],
                    processed_at=row[11], delivered_at=row[12],
                    error_message=row[13], transformed_content=row[14]
                ))
            return messages


class CommunicationRouter:
    """Main communication router class."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.logger = self.setup_logger()
        self.message_registry = MessageRegistry(os.getenv('COMMUNICATION_ROUTER_DATABASE_PATH', ':memory:'))
        self.router = MessageRouter({})
        self.processor = MessageProcessor({})
        self.channel_manager = ChannelManager({})

        # Load configuration
        self.config = self.load_config()

        # Reinitialize components with loaded config
        self.router = MessageRouter(self.config)
        self.processor = MessageProcessor(self.config)
        self.channel_manager = ChannelManager(self.config)

    def setup_logger(self) -> logging.Logger:
        """Setup logging for the communication router."""
        logger = logging.getLogger('CommunicationRouter')
        logger.setLevel(getattr(logging, os.getenv('COMMUNICATION_ROUTER_LOG_LEVEL', 'INFO')))

        # Create file handler
        log_file = os.getenv('COMMUNICATION_ROUTER_LOG_FILE_PATH', '/tmp/communication_router.log')
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment."""
        config = {
            'routing_rules': {
                'default_route': 'email',
                'rules': []
            },
            'channels': {
                'email': {'enabled': True},
                'sms': {'enabled': False},
                'chat': {'enabled': False}
            },
            'content_processing': {
                'format_conversion': {
                    'markdown_to_html': True
                }
            }
        }

        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    # Merge file config with defaults
                    for key, value in file_config.items():
                        if isinstance(value, dict) and key in config:
                            config[key].update(value)
                        else:
                            config[key] = value
            except Exception as e:
                self.logger.warning(f"Failed to load config from {self.config_path}: {e}")

        return config

    def route_and_send_message(
        self,
        content: str,
        source_channel: str,
        destination_channel: str = None,
        message_type: str = 'text',
        priority: str = 'normal',
        context: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Route and send a message through appropriate channels."""
        if context is None:
            context = {}
        if metadata is None:
            metadata = {}

        # Generate message ID
        message_id = f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(content) % 10000}"

        # Create message info
        message_info = MessageInfo(
            id=message_id,
            source_channel=ChannelType(source_channel.lower()),
            destination_channel=ChannelType(destination_channel.lower()) if destination_channel else ChannelType.INTERNAL,
            content=content,
            message_type=message_type,
            priority=MessagePriority[priority.upper()],
            routing_rules_applied=[],
            context=context,
            metadata=metadata,
            status=MessageStatus.RECEIVED,
            created_at=datetime.now().isoformat()
        )

        try:
            # Add to registry
            self.message_registry.add_message(message_info)

            # Route the message
            routed_message = self.router.route_message(message_info)
            self.logger.info(f"Message {message_id} routed to {routed_message.destination_channel.value}")

            # Process the message
            processed_message = self.processor.process_message(routed_message)

            # Update registry with processed message
            self.message_registry.add_message(processed_message)

            if processed_message.status == MessageStatus.FILTERED:
                self.logger.info(f"Message {message_id} was filtered by security policies")
                return message_id

            # Send the message through appropriate channel
            success = self.channel_manager.send_message(processed_message)

            if success:
                delivered_at = datetime.now().isoformat()
                self.message_registry.update_message_status(
                    message_id, MessageStatus.DELIVERED, delivered_at=delivered_at
                )
                self.logger.info(f"Message {message_id} delivered successfully")
            else:
                self.message_registry.update_message_status(
                    message_id, MessageStatus.FAILED, error_message="Delivery failed"
                )
                self.logger.error(f"Message {message_id} delivery failed")

        except Exception as e:
            self.logger.error(f"Error routing and sending message {message_id}: {e}")
            self.message_registry.update_message_status(
                message_id, MessageStatus.FAILED, error_message=str(e)
            )

        return message_id

    def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """Get the status of a specific message."""
        message_info = self.message_registry.get_message_by_id(message_id)
        if not message_info:
            return {'error': f'Message {message_id} not found'}

        result = asdict(message_info)
        result['source_channel'] = message_info.source_channel.name
        result['destination_channel'] = message_info.destination_channel.name
        result['priority'] = message_info.priority.name
        result['status'] = message_info.status.name
        return result

    def get_messages_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get messages by status."""
        try:
            status_enum = MessageStatus[status.upper()]
            messages = self.message_registry.get_messages_by_status(status_enum)
            result = []
            for msg in messages:
                msg_dict = asdict(msg)
                msg_dict['source_channel'] = msg.source_channel.name
                msg_dict['destination_channel'] = msg.destination_channel.name
                msg_dict['priority'] = msg.priority.name
                msg_dict['status'] = msg.status.name
                result.append(msg_dict)
            return result
        except KeyError:
            return []


def main():
    """Main function for testing the Communication Router."""
    print("Communication Router Skill")
    print("=========================")

    # Initialize the communication router
    config_path = os.getenv('ROUTER_CONFIG_PATH', './router_config.json')
    router = CommunicationRouter(config_path)

    print(f"Communication Router initialized with config: {config_path}")

    # Example: Send a test message
    print("\nSending test message...")
    test_message_id = router.route_and_send_message(
        content="This is a test message from the Communication Router.",
        source_channel="internal",
        message_type="text",
        priority="normal",
        context={
            "recipient_email": "test@example.com",
            "subject": "Test Message"
        }
    )

    print(f"Test message sent with ID: {test_message_id}")

    # Check message status
    status = router.get_message_status(test_message_id)
    print(f"Message status: {status['status']}")

    # Example: Send an urgent message
    print("\nSending urgent message...")
    urgent_message_id = router.route_and_send_message(
        content="URGENT: This requires immediate attention!",
        source_channel="internal",
        message_type="text",
        priority="urgent",
        context={
            "recipient_phone": "+1234567890",
            "chat_channel": "#urgent-notifications"
        }
    )

    print(f"Urgent message sent with ID: {urgent_message_id}")

    # Get all received messages
    received_messages = router.get_messages_by_status('received')
    print(f"\nReceived messages: {len(received_messages)}")

    # Get all delivered messages
    delivered_messages = router.get_messages_by_status('delivered')
    print(f"Delivered messages: {len(delivered_messages)}")

    print("\nCommunication Router is ready to route messages!")


if __name__ == "__main__":
    main()