#!/usr/bin/env python3
"""
WhatsApp Monitoring Module for WhatsApp Manager Skill
"""

import asyncio
import aiohttp
import json
import os
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
from playwright.async_api import async_playwright
from pathlib import Path

class WhatsAppMonitor:
    def __init__(self):
        """Initialize the WhatsApp Monitor with configuration"""
        self.api_token = os.getenv('WHATSAPP_API_TOKEN')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.base_url = f"https://graph.facebook.com/v17.0/{self.phone_number_id}"

        # Setup logging
        logging.basicConfig(
            filename=f'/Logs/whatsapp_monitor_{datetime.now().strftime("%Y%m%d")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Database for tracking messages
        self.db_path = '/Data/whatsapp_messages.db'
        self._setup_database()

        # Escalation keywords
        self.escalation_keywords = [
            "urgent", "asap", "immediately", "emergency", "problem",
            "issue", "complaint", "ceo", "manager", "supervisor",
            "legal", "lawyer", "attorney", "contract", "agreement"
        ]

    def _setup_database(self):
        """Setup database for tracking WhatsApp messages"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE,
                escalation_needed BOOLEAN DEFAULT FALSE,
                escalation_timestamp DATETIME,
                response_sent BOOLEAN DEFAULT FALSE,
                response_text TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT UNIQUE NOT NULL,
                name TEXT,
                customer_type TEXT DEFAULT 'regular',  -- vip, regular, prospect
                last_contact DATETIME,
                total_messages INTEGER DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()

    async def check_new_messages(self) -> List[Dict]:
        """
        Check for new WhatsApp messages

        Returns:
            List[Dict]: List of new messages
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }

            # Get messages from the last 10 minutes
            since_time = datetime.now() - timedelta(minutes=10)
            params = {
                'fields': 'messages,contacts',
                'since': int(since_time.timestamp())
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url + '/messages', headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        messages = data.get('messages', [])

                        # Process each message
                        for msg in messages:
                            await self._store_message(msg)

                        logging.info(f"Found {len(messages)} new messages")
                        return messages
                    else:
                        logging.error(f"Failed to fetch messages: {response.status}")
                        return []

        except Exception as e:
            logging.error(f"Error checking new messages: {str(e)}")
            return []

    async def _store_message(self, message_data: Dict):
        """Store incoming message in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Extract message details
        sender = message_data.get('from', 'unknown')
        message_text = message_data.get('text', {}).get('body', 'Media message')
        timestamp = datetime.fromisoformat(message_data.get('timestamp'))

        # Check if escalation is needed
        escalation_needed = self._check_escalation_needed(message_text.lower())

        # Insert message
        cursor.execute('''
            INSERT INTO messages (sender, message, timestamp, escalation_needed)
            VALUES (?, ?, ?, ?)
        ''', (sender, message_text, timestamp, escalation_needed))

        # Update contact info
        cursor.execute('''
            INSERT OR REPLACE INTO contacts (phone_number, name, last_contact, total_messages)
            VALUES (?, ?, ?, COALESCE((SELECT total_messages FROM contacts WHERE phone_number = ?), 0) + 1)
        ''', (sender, f"Contact {sender}", timestamp, sender))

        conn.commit()
        conn.close()

    def _check_escalation_needed(self, message: str) -> bool:
        """Check if message needs escalation based on keywords"""
        message_lower = message.lower()
        for keyword in self.escalation_keywords:
            if keyword in message_lower:
                return True
        return False

    async def get_unprocessed_messages(self) -> List[Dict]:
        """Get messages that haven't been processed yet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, sender, message, timestamp, escalation_needed
            FROM messages
            WHERE processed = FALSE
            ORDER BY timestamp ASC
        ''')

        rows = cursor.fetchall()
        messages = []
        for row in rows:
            messages.append({
                'id': row[0],
                'sender': row[1],
                'message': row[2],
                'timestamp': row[3],
                'escalation_needed': row[4]
            })

        conn.close()
        return messages

    def categorize_message(self, message: str) -> str:
        """
        Categorize message based on content

        Args:
            message: The message content

        Returns:
            str: Category of the message
        """
        message_lower = message.lower()

        if any(keyword in message_lower for keyword in ['hello', 'hi', 'hey', 'greetings']):
            return 'greeting'
        elif any(keyword in message_lower for keyword in ['thank', 'thanks', 'appreciate']):
            return 'gratitude'
        elif any(keyword in message_lower for keyword in ['question', 'ask', 'wonder', 'want to know']):
            return 'inquiry'
        elif any(keyword in message_lower for keyword in ['order', 'purchase', 'buy', 'cart']):
            return 'sales_inquiry'
        elif any(keyword in message_lower for keyword in ['meeting', 'appointment', 'schedule']):
            return 'appointment'
        elif any(keyword in message_lower for keyword in ['complaint', 'issue', 'problem', 'bug']):
            return 'complaint'
        else:
            return 'general'

    def generate_response(self, message: str, sender: str) -> str:
        """
        Generate appropriate response based on message content and sender

        Args:
            message: The incoming message
            sender: The sender's phone number

        Returns:
            str: The response message
        """
        category = self.categorize_message(message)
        customer_type = self.get_customer_type(sender)

        if customer_type == 'vip':
            greeting = f"Hello valued customer {sender}! "
        else:
            greeting = f"Hello! Thanks for reaching out ({sender[-4:]}****). "

        if category == 'greeting':
            return greeting + "How can I assist you today? For urgent matters, please let me know."
        elif category == 'gratitude':
            return "You're very welcome! Is there anything else I can help with?"
        elif category == 'inquiry':
            return greeting + "I'd be happy to help with your inquiry. Could you please provide more details about what you need?"
        elif category == 'sales_inquiry':
            return greeting + "Thanks for your interest in our services! I'd love to learn more about your needs. What type of service are you looking for?"
        elif category == 'appointment':
            return greeting + "I'd be happy to schedule an appointment for you. Please let me know your preferred date and time, and what the meeting is about."
        elif category == 'complaint':
            return f"⚠️ {greeting}I apologize for any inconvenience. This has been escalated to our support team and someone will contact you shortly. Reference: {datetime.now().strftime('%Y%m%d-%H%M%S')}"
        else:
            return f"{greeting}I've received your message and will forward it to the appropriate team. Someone will get back to you soon!"

    def get_customer_type(self, phone_number: str) -> str:
        """Get customer type from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT customer_type FROM contacts WHERE phone_number = ?', (phone_number,))
        result = cursor.fetchone()

        conn.close()
        return result[0] if result else 'regular'

    async def send_response(self, recipient: str, message: str) -> bool:
        """
        Send response message via WhatsApp API

        Args:
            recipient: Recipient's phone number
            message: Message content

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }

            payload = {
                'messaging_product': 'whatsapp',
                'to': recipient,
                'type': 'text',
                'text': {
                    'body': message
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(f'{self.base_url}/messages', headers=headers, json=payload) as response:
                    if response.status in [200, 201]:
                        # Update message record with response info
                        await self._mark_as_responded(recipient, message)
                        logging.info(f"Response sent to {recipient}: {message[:50]}...")
                        return True
                    else:
                        logging.error(f"Failed to send response to {recipient}: {response.status}")
                        return False

        except Exception as e:
            logging.error(f"Error sending response to {recipient}: {str(e)}")
            return False

    async def _mark_as_responded(self, recipient: str, response_text: str):
        """Mark the latest message from this recipient as responded"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE messages
            SET processed = TRUE, response_sent = TRUE, response_text = ?
            WHERE sender = ? AND processed = FALSE
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (response_text, recipient))

        conn.commit()
        conn.close()

    async def process_pending_messages(self):
        """Process all unprocessed messages"""
        messages = await self.get_unprocessed_messages()
        logging.info(f"Processing {len(messages)} pending messages")

        for msg in messages:
            if msg['escalation_needed']:
                # Create escalation request in Pending_Approval
                escalation_file = f"/Pending_Approval/whatsapp_{msg['id']}_{int(msg['timestamp'].timestamp())}.md"
                with open(escalation_file, 'w') as f:
                    f.write(f"# WhatsApp Escalation Request\n\n")
                    f.write(f"**Time:** {msg['timestamp']}\n")
                    f.write(f"**Sender:** {msg['sender']}\n")
                    f.write(f"**Message:** {msg['message']}\n\n")
                    f.write(f"**Action Required:** Please review this urgent message and respond.\n")

                logging.info(f"Escalation request created for message {msg['id']}")

                # Send acknowledgment
                await self.send_response(msg['sender'],
                                       "Your message has been received and escalated to our team. Someone will contact you shortly.")
            else:
                response = self.generate_response(msg['message'], msg['sender'])
                success = await self.send_response(msg['sender'], response)

                if success:
                    logging.info(f"Response sent for message {msg['id']}")
                else:
                    logging.error(f"Failed to send response for message {msg['id']}")

    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about WhatsApp usage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total messages received
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = cursor.fetchone()[0]

        # Processed vs unprocessed
        cursor.execute("SELECT COUNT(*) FROM messages WHERE processed = TRUE")
        processed_messages = cursor.fetchone()[0]

        # Escalated messages
        cursor.execute("SELECT COUNT(*) FROM messages WHERE escalation_needed = TRUE")
        escalated_messages = cursor.fetchone()[0]

        conn.close()

        return {
            "total_messages": total_messages,
            "processed_messages": processed_messages,
            "pending_messages": total_messages - processed_messages,
            "escalated_messages": escalated_messages
        }

async def main():
    """Main function for testing WhatsApp monitoring"""
    monitor = WhatsAppMonitor()

    print("WhatsApp Monitor initialized")
    print("Fetching new messages...")

    # Check for new messages
    new_messages = await monitor.check_new_messages()
    print(f"Found {len(new_messages)} new messages")

    # Process pending messages
    await monitor.process_pending_messages()

    # Print statistics
    stats = monitor.get_statistics()
    print(f"\nStatistics:")
    for key, value in stats.items():
        print(f"- {key}: {value}")

if __name__ == "__main__":
    asyncio.run(main())