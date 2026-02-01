#!/usr/bin/env python3
"""
Communication Logger Module for Communication Logger Skill
"""

import sqlite3
import json
import os
import logging
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from cryptography.fernet import Fernet
from pathlib import Path
import asyncio
import aiofiles

class CommunicationLogger:
    def __init__(self):
        """Initialize the Communication Logger with configuration"""
        self.encryption_key = os.getenv('COMM_LOG_ENCRYPTION_KEY', Fernet.generate_key())
        self.cipher_suite = Fernet(self.encryption_key)

        # Setup logging
        logging.basicConfig(
            filename=f'/Logs/communication_logger_{datetime.now().strftime("%Y%m%d")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Database for storing logs
        self.db_path = '/Data/communications.db'
        self._setup_database()

        # Sensitivity classifications
        self.sensitivity_levels = {
            'public': 1,
            'internal': 2,
            'confidential': 3,
            'restricted': 4
        }

        # Retention policies
        self.retention_days = {
            'business': 2555,  # 7 years for business communications
            'marketing': 1095, # 3 years for marketing
            'support': 1825,   # 5 years for support
            'personal': 730    # 2 years for personal
        }

    def _setup_database(self):
        """Setup database for storing communication logs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main communications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS communications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_id TEXT UNIQUE NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                channel TEXT NOT NULL,
                direction TEXT NOT NULL,
                participants TEXT NOT NULL,
                content_hash TEXT,
                content_encrypted BLOB,
                category TEXT,
                sensitivity_level TEXT DEFAULT 'internal',
                retention_category TEXT DEFAULT 'business',
                retention_expiry DATETIME,
                created_by TEXT,
                approved_by TEXT,
                status TEXT DEFAULT 'logged',
                metadata TEXT  -- JSON metadata
            )
        ''')

        # Indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON communications(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_channel ON communications(channel)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensitivity ON communications(sensitivity_level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_retention_expiry ON communications(retention_expiry)')

        # Access log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                access_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                access_type TEXT NOT NULL,  -- read, export, delete
                purpose TEXT,
                ip_address TEXT,
                user_agent TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def log_communication(self,
                         channel: str,
                         direction: str,
                         participants: List[str],
                         content: str,
                         category: str = 'business',
                         sensitivity_level: str = 'internal',
                         created_by: str = 'system',
                         metadata: Dict[str, Any] = None) -> str:
        """
        Log a communication with appropriate security measures

        Args:
            channel: Communication channel ('email', 'whatsapp', 'social_media', etc.)
            direction: Direction of communication ('incoming', 'outgoing')
            participants: List of participant identifiers
            content: Communication content
            category: Category of communication ('business', 'personal', etc.)
            sensitivity_level: Sensitivity classification
            created_by: Entity that created the log
            metadata: Additional metadata about the communication

        Returns:
            str: Unique log ID
        """
        try:
            # Validate inputs
            if sensitivity_level not in self.sensitivity_levels:
                raise ValueError(f"Invalid sensitivity level: {sensitivity_level}")

            if category not in self.retention_days:
                # Default to business if invalid category
                category = 'business'

            # Generate unique log ID
            log_id = self._generate_log_id(channel, participants, content)

            # Calculate retention expiry
            retention_days = self.retention_days[category]
            retention_expiry = datetime.now() + timedelta(days=retention_days)

            # Encrypt sensitive content
            encrypted_content = self.cipher_suite.encrypt(content.encode('utf-8'))
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

            # Convert participants to JSON
            participants_json = json.dumps(participants)

            # Convert metadata to JSON
            metadata_json = json.dumps(metadata) if metadata else '{}'

            # Insert into database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO communications (
                    log_id, channel, direction, participants,
                    content_hash, content_encrypted, category,
                    sensitivity_level, retention_category, retention_expiry,
                    created_by, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                log_id, channel, direction, participants_json,
                content_hash, encrypted_content, category,
                sensitivity_level, category, retention_expiry,
                created_by, metadata_json
            ))

            conn.commit()
            conn.close()

            logging.info(f"Logged communication: {log_id} ({channel}, {direction})")
            return log_id

        except Exception as e:
            logging.error(f"Failed to log communication: {str(e)}")
            raise

    def retrieve_communication(self, log_id: str, user_id: str, purpose: str = None) -> Dict[str, Any]:
        """
        Retrieve a communication with access logging

        Args:
            log_id: Unique log ID
            user_id: User requesting access
            purpose: Purpose for accessing the communication

        Returns:
            Dict containing communication details
        """
        try:
            # Log the access
            self._log_access(log_id, user_id, 'read', purpose)

            # Retrieve from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT log_id, timestamp, channel, direction, participants,
                       content_encrypted, category, sensitivity_level,
                       retention_category, created_by, metadata, status
                FROM communications
                WHERE log_id = ?
            ''', (log_id,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                raise ValueError(f"Communication with ID {log_id} not found")

            # Decrypt content
            encrypted_content = row[5]
            decrypted_content = self.cipher_suite.decrypt(encrypted_content).decode('utf-8')

            # Parse participants and metadata
            participants = json.loads(row[4])
            metadata = json.loads(row[10])

            communication = {
                'log_id': row[0],
                'timestamp': row[1],
                'channel': row[2],
                'direction': row[3],
                'participants': participants,
                'content': decrypted_content,
                'category': row[6],
                'sensitivity_level': row[7],
                'retention_category': row[8],
                'created_by': row[9],
                'metadata': metadata,
                'status': row[11]
            }

            return communication

        except Exception as e:
            logging.error(f"Failed to retrieve communication {log_id}: {str(e)}")
            raise

    def _log_access(self, log_id: str, user_id: str, access_type: str, purpose: str = None, ip_address: str = None, user_agent: str = None):
        """Log access to a communication"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO access_log (log_id, user_id, access_type, purpose, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (log_id, user_id, access_type, purpose, ip_address, user_agent))

        conn.commit()
        conn.close()

    def _generate_log_id(self, channel: str, participants: List[str], content: str) -> str:
        """Generate a unique log ID based on communication details"""
        timestamp = datetime.now().isoformat()
        participants_str = ','.join(sorted(participants))
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

        # Combine elements to create unique ID
        combined = f"{channel}:{participants_str}:{timestamp}:{content_hash}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:32]

    def search_communications(self,
                            channel: str = None,
                            direction: str = None,
                            participants: List[str] = None,
                            date_from: datetime = None,
                            date_to: datetime = None,
                            category: str = None,
                            sensitivity_level: str = None) -> List[Dict[str, Any]]:
        """
        Search communications with various filters

        Args:
            channel: Filter by channel
            direction: Filter by direction
            participants: Filter by participants (any participant)
            date_from: Filter by date range start
            date_to: Filter by date range end
            category: Filter by category
            sensitivity_level: Filter by sensitivity level

        Returns:
            List of communication summaries (without content)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build query dynamically
            query_parts = ["SELECT log_id, timestamp, channel, direction, participants, category, sensitivity_level FROM communications WHERE 1=1"]
            params = []

            if channel:
                query_parts.append("AND channel = ?")
                params.append(channel)

            if direction:
                query_parts.append("AND direction = ?")
                params.append(direction)

            if participants:
                # Search for any of the specified participants
                participant_conditions = " OR ".join(["json_extract(participants, '$[' || ? || ']') = ?" for p in participants])
                query_parts.append(f"AND ({participant_conditions})")
                for p in participants:
                    params.extend([p, p])

            if date_from:
                query_parts.append("AND timestamp >= ?")
                params.append(date_from.isoformat())

            if date_to:
                query_parts.append("AND timestamp <= ?")
                params.append(date_to.isoformat())

            if category:
                query_parts.append("AND category = ?")
                params.append(category)

            if sensitivity_level:
                query_parts.append("AND sensitivity_level = ?")
                params.append(sensitivity_level)

            query = " ".join(query_parts)
            cursor.execute(query, params)

            rows = cursor.fetchall()
            conn.close()

            communications = []
            for row in rows:
                participants = json.loads(row[4])
                comm = {
                    'log_id': row[0],
                    'timestamp': row[1],
                    'channel': row[2],
                    'direction': row[3],
                    'participants': participants,
                    'category': row[5],
                    'sensitivity_level': row[6]
                }
                communications.append(comm)

            return communications

        except Exception as e:
            logging.error(f"Failed to search communications: {str(e)}")
            raise

    def update_retention_expiry(self, log_id: str, new_expiry: datetime) -> bool:
        """Update the retention expiry for a communication"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE communications
                SET retention_expiry = ?, updated_by = ?
                WHERE log_id = ?
            ''', (new_expiry, 'system', log_id))

            success = cursor.rowcount > 0
            conn.commit()
            conn.close()

            if success:
                logging.info(f"Updated retention expiry for {log_id} to {new_expiry}")
            else:
                logging.warning(f"Communication {log_id} not found for retention update")

            return success

        except Exception as e:
            logging.error(f"Failed to update retention expiry for {log_id}: {str(e)}")
            return False

    def get_expired_communications(self) -> List[str]:
        """Get list of communications that have exceeded their retention period"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT log_id FROM communications
                WHERE retention_expiry < ? AND status = 'logged'
            ''', (datetime.now(),))

            rows = cursor.fetchall()
            conn.close()

            return [row[0] for row in rows]

        except Exception as e:
            logging.error(f"Failed to get expired communications: {str(e)}")
            return []

    def delete_communication(self, log_id: str, reason: str = 'retention_exceeded') -> bool:
        """Delete a communication permanently"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Update status instead of hard delete for audit trail
            cursor.execute('''
                UPDATE communications
                SET status = 'deleted', metadata = json_insert(metadata, '$.deletion_reason', ?)
                WHERE log_id = ?
            ''', (reason, log_id))

            success = cursor.rowcount > 0
            conn.commit()
            conn.close()

            if success:
                logging.info(f"Marked communication {log_id} as deleted ({reason})")
            else:
                logging.warning(f"Communication {log_id} not found for deletion")

            return success

        except Exception as e:
            logging.error(f"Failed to delete communication {log_id}: {str(e)}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about logged communications"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Total communications
            cursor.execute("SELECT COUNT(*) FROM communications")
            total = cursor.fetchone()[0]

            # Communications by channel
            cursor.execute("SELECT channel, COUNT(*) FROM communications GROUP BY channel")
            by_channel = dict(cursor.fetchall())

            # Communications by category
            cursor.execute("SELECT category, COUNT(*) FROM communications GROUP BY category")
            by_category = dict(cursor.fetchall())

            # Communications by sensitivity
            cursor.execute("SELECT sensitivity_level, COUNT(*) FROM communications GROUP BY sensitivity_level")
            by_sensitivity = dict(cursor.fetchall())

            # Expired communications
            cursor.execute("SELECT COUNT(*) FROM communications WHERE retention_expiry < ?", (datetime.now(),))
            expired = cursor.fetchone()[0]

            conn.close()

            return {
                'total_communications': total,
                'by_channel': by_channel,
                'by_category': by_category,
                'by_sensitivity': by_sensitivity,
                'expired_count': expired
            }

        except Exception as e:
            logging.error(f"Failed to get statistics: {str(e)}")
            return {}

    async def export_communications(self, log_ids: List[str], export_format: str = 'json') -> str:
        """
        Export communications in specified format

        Args:
            log_ids: List of communication IDs to export
            export_format: Format for export ('json', 'csv', 'xml')

        Returns:
            Path to exported file
        """
        try:
            # Retrieve communications
            communications = []
            for log_id in log_ids:
                try:
                    comm = self.retrieve_communication(log_id, 'export_process', 'data_export')
                    communications.append(comm)
                except Exception as e:
                    logging.error(f"Failed to retrieve communication {log_id} for export: {str(e)}")

            # Create export directory if it doesn't exist
            export_dir = Path('/Exports/communications')
            export_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"communications_export_{timestamp}.{export_format}"
            filepath = export_dir / filename

            # Export based on format
            if export_format == 'json':
                async with aiofiles.open(filepath, 'w') as f:
                    await f.write(json.dumps(communications, indent=2))
            elif export_format == 'csv':
                import csv
                fieldnames = ['log_id', 'timestamp', 'channel', 'direction', 'participants', 'category', 'sensitivity_level', 'content']
                async with aiofiles.open(filepath, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for comm in communications:
                        # For CSV, we'll simplify participants to a string
                        comm_copy = comm.copy()
                        comm_copy['participants'] = ', '.join(comm['participants'])
                        writer.writerow(comm_copy)
            else:
                raise ValueError(f"Unsupported export format: {export_format}")

            logging.info(f"Exported {len(communications)} communications to {filepath}")
            return str(filepath)

        except Exception as e:
            logging.error(f"Failed to export communications: {str(e)}")
            raise

async def main():
    """Main function for testing the Communication Logger"""
    logger = CommunicationLogger()

    # Example: Log a communication
    log_id = logger.log_communication(
        channel='email',
        direction='outgoing',
        participants=['user@example.com', 'admin@company.com'],
        content='This is a test email communication for logging purposes.',
        category='business',
        sensitivity_level='internal',
        created_by='test_user',
        metadata={'thread_id': 'thread_123', 'priority': 'normal'}
    )

    print(f"Logged communication with ID: {log_id}")

    # Example: Retrieve the communication
    retrieved = logger.retrieve_communication(log_id, 'test_user', 'testing')
    print(f"Retrieved communication: {retrieved['content']}")

    # Example: Search for communications
    results = logger.search_communications(channel='email', direction='outgoing')
    print(f"Found {len(results)} email communications")

    # Example: Get statistics
    stats = logger.get_statistics()
    print(f"Statistics: {stats}")

if __name__ == "__main__":
    asyncio.run(main())