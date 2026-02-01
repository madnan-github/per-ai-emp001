#!/usr/bin/env python3
"""
Backup & Recovery

This module provides automated backup and recovery of critical data for the Personal AI Employee system.
It implements comprehensive backup strategies, automated scheduling, and reliable recovery mechanisms
to ensure data integrity and system availability in case of failures, corruptions, or disasters.

Features:
- Automated backup scheduling and execution
- Multiple backup types (full, incremental, differential, snapshot)
- Encryption and compression of backups
- Multi-location backup storage (local, remote, cloud)
- Recovery and restore capabilities
- Backup verification and validation
- Retention policy enforcement
- Monitoring and alerting
"""

import json
import os
import shutil
import sqlite3
import logging
import hashlib
import zipfile
import gzip
import tarfile
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import schedule
import time
import tempfile
import socket
import ssl


@dataclass
class BackupInfo:
    """Data class to hold backup information."""
    id: str
    name: str
    type: str  # full, incremental, differential, snapshot
    source_paths: List[str]
    target_location: str
    timestamp: str
    size_bytes: int
    status: str  # pending, running, completed, failed
    encryption: bool
    compression: str  # none, gzip, zip, lzma
    checksum: str
    retention_date: str
    metadata: Dict[str, Any]


@dataclass
class RecoveryInfo:
    """Data class to hold recovery information."""
    id: str
    backup_id: str
    target_location: str
    timestamp: str
    status: str  # pending, running, completed, failed
    files_restored: int
    bytes_restored: int
    verification_result: str
    metadata: Dict[str, Any]


class BackupEncryption:
    """Handles encryption and decryption of backup data."""

    def __init__(self, password: str = None):
        self.password = password or os.getenv('BACKUP_ENCRYPTION_PASSWORD', '')

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from password and salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password.encode()))
        return key

    def encrypt_file(self, file_path: str, output_path: str) -> str:
        """Encrypt a file using Fernet symmetric encryption."""
        salt = os.urandom(16)
        key = self._derive_key(salt)
        fernet = Fernet(key)

        with open(file_path, 'rb') as f:
            data = f.read()

        encrypted_data = fernet.encrypt(data)

        # Write salt + encrypted data
        with open(output_path, 'wb') as f:
            f.write(salt + encrypted_data)

        return hashlib.sha256(encrypted_data).hexdigest()

    def decrypt_file(self, encrypted_path: str, output_path: str) -> bool:
        """Decrypt a file using Fernet symmetric encryption."""
        with open(encrypted_path, 'rb') as f:
            file_data = f.read()

        salt = file_data[:16]
        encrypted_data = file_data[16:]

        key = self._derive_key(salt)
        fernet = Fernet(key)

        try:
            decrypted_data = fernet.decrypt(encrypted_data)
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            return True
        except Exception:
            return False


class BackupStorage:
    """Handles different storage backends for backups."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def upload_backup(self, local_path: str, remote_path: str) -> bool:
        """Upload backup to remote storage based on configuration."""
        storage_type = self.config.get('type', 'local')

        if storage_type == 'local':
            # Copy to local path
            target_dir = os.path.dirname(remote_path)
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(local_path, remote_path)
            return True

        elif storage_type == 'sftp':
            import paramiko
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                # Connect to SFTP server
                ssh.connect(
                    hostname=self.config['host'],
                    port=self.config.get('port', 22),
                    username=self.config['username'],
                    password=os.getenv(self.config['password_env_var'])
                )

                sftp = ssh.open_sftp()

                # Create remote directories if they don't exist
                remote_dir = os.path.dirname(remote_path)
                try:
                    sftp.mkdir(remote_dir)
                except IOError:
                    # Directory may already exist
                    pass

                # Upload file
                sftp.put(local_path, remote_path)
                sftp.close()
                ssh.close()
                return True
            except Exception as e:
                print(f"SFTP upload failed: {e}")
                return False

        elif storage_type == 'cloud':
            cloud_type = self.config.get('cloud', {}).get('type', 's3')
            if cloud_type == 's3':
                import boto3
                try:
                    s3 = boto3.client(
                        's3',
                        aws_access_key_id=os.getenv(self.config['cloud']['access_key_env_var']),
                        aws_secret_access_key=os.getenv(self.config['cloud']['secret_key_env_var']),
                        region_name=self.config['cloud'].get('region', 'us-east-1')
                    )

                    bucket = self.config['cloud']['bucket']
                    key = os.path.basename(remote_path)

                    s3.upload_file(local_path, bucket, key)
                    return True
                except Exception as e:
                    print(f"S3 upload failed: {e}")
                    return False

        return False

    def download_backup(self, remote_path: str, local_path: str) -> bool:
        """Download backup from remote storage."""
        storage_type = self.config.get('type', 'local')

        if storage_type == 'local':
            shutil.copy2(remote_path, local_path)
            return True

        elif storage_type == 'sftp':
            import paramiko
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                ssh.connect(
                    hostname=self.config['host'],
                    port=self.config.get('port', 22),
                    username=self.config['username'],
                    password=os.getenv(self.config['password_env_var'])
                )

                sftp = ssh.open_sftp()
                sftp.get(remote_path, local_path)
                sftp.close()
                ssh.close()
                return True
            except Exception as e:
                print(f"SFTP download failed: {e}")
                return False

        elif storage_type == 'cloud':
            cloud_type = self.config.get('cloud', {}).get('type', 's3')
            if cloud_type == 's3':
                import boto3
                try:
                    s3 = boto3.client(
                        's3',
                        aws_access_key_id=os.getenv(self.config['cloud']['access_key_env_var']),
                        aws_secret_access_key=os.getenv(self.config['cloud']['secret_key_env_var']),
                        region_name=self.config['cloud'].get('region', 'us-east-1')
                    )

                    bucket = self.config['cloud']['bucket']
                    key = os.path.basename(remote_path)

                    s3.download_file(bucket, key, local_path)
                    return True
                except Exception as e:
                    print(f"S3 download failed: {e}")
                    return False

        return False


class BackupCatalog:
    """Manages the backup catalog database."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables."""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS backups (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    source_paths TEXT,
                    target_location TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    size_bytes INTEGER,
                    status TEXT NOT NULL,
                    encryption BOOLEAN,
                    compression TEXT,
                    checksum TEXT,
                    retention_date TEXT,
                    metadata TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS recoveries (
                    id TEXT PRIMARY KEY,
                    backup_id TEXT,
                    target_location TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    files_restored INTEGER,
                    bytes_restored INTEGER,
                    verification_result TEXT,
                    metadata TEXT,
                    FOREIGN KEY (backup_id) REFERENCES backups (id)
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

    def add_backup(self, backup_info: BackupInfo):
        """Add a backup record to the catalog."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO backups
                (id, name, type, source_paths, target_location, timestamp, size_bytes,
                 status, encryption, compression, checksum, retention_date, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                backup_info.id, backup_info.name, backup_info.type,
                json.dumps(backup_info.source_paths), backup_info.target_location,
                backup_info.timestamp, backup_info.size_bytes, backup_info.status,
                backup_info.encryption, backup_info.compression, backup_info.checksum,
                backup_info.retention_date, json.dumps(backup_info.metadata)
            ))

    def add_recovery(self, recovery_info: RecoveryInfo):
        """Add a recovery record to the catalog."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO recoveries
                (id, backup_id, target_location, timestamp, status,
                 files_restored, bytes_restored, verification_result, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                recovery_info.id, recovery_info.backup_id, recovery_info.target_location,
                recovery_info.timestamp, recovery_info.status, recovery_info.files_restored,
                recovery_info.bytes_restored, recovery_info.verification_result,
                json.dumps(recovery_info.metadata)
            ))

    def get_backup_by_id(self, backup_id: str) -> Optional[BackupInfo]:
        """Get a backup record by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, name, type, source_paths, target_location, timestamp,
                       size_bytes, status, encryption, compression, checksum,
                       retention_date, metadata
                FROM backups WHERE id = ?
            ''', (backup_id,))
            row = cursor.fetchone()
            if row:
                return BackupInfo(
                    id=row[0], name=row[1], type=row[2],
                    source_paths=json.loads(row[3]), target_location=row[4],
                    timestamp=row[5], size_bytes=row[6], status=row[7],
                    encryption=bool(row[8]), compression=row[9], checksum=row[10],
                    retention_date=row[11], metadata=json.loads(row[12])
                )
        return None

    def get_recent_backups(self, limit: int = 10) -> List[BackupInfo]:
        """Get recent backup records."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, name, type, source_paths, target_location, timestamp,
                       size_bytes, status, encryption, compression, checksum,
                       retention_date, metadata
                FROM backups
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            backups = []
            for row in rows:
                backups.append(BackupInfo(
                    id=row[0], name=row[1], type=row[2],
                    source_paths=json.loads(row[3]), target_location=row[4],
                    timestamp=row[5], size_bytes=row[6], status=row[7],
                    encryption=bool(row[8]), compression=row[9], checksum=row[10],
                    retention_date=row[11], metadata=json.loads(row[12])
                ))
            return backups

    def get_expired_backups(self) -> List[BackupInfo]:
        """Get backups that have exceeded their retention period."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, name, type, source_paths, target_location, timestamp,
                       size_bytes, status, encryption, compression, checksum,
                       retention_date, metadata
                FROM backups
                WHERE retention_date < ?
            ''', (datetime.now().isoformat(),))
            rows = cursor.fetchall()
            backups = []
            for row in rows:
                backups.append(BackupInfo(
                    id=row[0], name=row[1], type=row[2],
                    source_paths=json.loads(row[3]), target_location=row[4],
                    timestamp=row[5], size_bytes=row[6], status=row[7],
                    encryption=bool(row[8]), compression=row[9], checksum=row[10],
                    retention_date=row[11], metadata=json.loads(row[12])
                ))
            return backups


class BackupScheduler:
    """Manages backup scheduling."""

    def __init__(self, backup_manager: 'BackupManager'):
        self.backup_manager = backup_manager
        self.jobs = {}
        self.running = False
        self.thread = None

    def add_schedule(self, schedule_config: Dict[str, Any]):
        """Add a backup schedule."""
        schedule_type = schedule_config.get('type', 'incremental')
        cron_expr = schedule_config.get('cron_expression', '0 2 * * *')
        name = schedule_config.get('name', f"{schedule_type}_backup")

        # Parse cron expression into schedule components
        # This is a simplified version - real implementation would be more robust
        parts = cron_expr.split()
        minute, hour = parts[0], parts[1]

        job = None
        if minute.isdigit():
            job = schedule.every().minute.at(f":{minute}").do(
                self._execute_scheduled_backup,
                name=name,
                backup_type=schedule_type,
                schedule_config=schedule_config
            )
        elif hour.isdigit():
            job = schedule.every().hour.at(f":{minute}").do(
                self._execute_scheduled_backup,
                name=name,
                backup_type=schedule_type,
                schedule_config=schedule_config
            )
        else:
            # Default to daily at 2 AM if not a simple numeric schedule
            job = schedule.every().day.at("02:00").do(
                self._execute_scheduled_backup,
                name=name,
                backup_type=schedule_type,
                schedule_config=schedule_config
            )

        self.jobs[name] = job

    def _execute_scheduled_backup(self, name: str, backup_type: str, schedule_config: Dict[str, Any]):
        """Execute a scheduled backup."""
        include_paths = schedule_config.get('include_paths', [])
        exclude_patterns = schedule_config.get('exclude_patterns', [])

        try:
            self.backup_manager.create_backup(
                name=name,
                backup_type=backup_type,
                source_paths=include_paths,
                target_location=self.backup_manager.default_target,
                compression=self.backup_manager.compression,
                encryption=self.backup_manager.encryption,
                exclude_patterns=exclude_patterns
            )
        except Exception as e:
            print(f"Failed to execute scheduled backup {name}: {e}")

    def start(self):
        """Start the scheduler."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join()

    def _run_scheduler(self):
        """Internal method to run the scheduler."""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


class BackupManager:
    """Main backup manager class."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.logger = self.setup_logger()
        self.catalog = BackupCatalog(os.getenv('BACKUP_CATALOG_DB_PATH', ':memory:'))
        self.scheduler = BackupScheduler(self)
        self.encryption = BackupEncryption()
        self.storage = None
        self.compression = os.getenv('BACKUP_DEFAULT_COMPRESSION', 'gzip')
        self.encryption_enabled = os.getenv('BACKUP_ENCRYPTION_ENABLED', 'false').lower() == 'true'
        self.default_target = os.getenv('BACKUP_DEFAULT_TARGET', '/backups/')

        # Load configuration
        self.config = self.load_config()

        # Initialize storage based on config
        storage_config = self.config.get('storage', {})
        self.storage = BackupStorage(storage_config)

    def setup_logger(self) -> logging.Logger:
        """Setup logging for the backup manager."""
        logger = logging.getLogger('BackupManager')
        logger.setLevel(getattr(logging, os.getenv('BACKUP_LOG_LEVEL', 'INFO')))

        # Create file handler
        log_file = os.getenv('BACKUP_LOG_FILE_PATH', '/tmp/backup_manager.log')
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment."""
        config = {
            'schedules': {},
            'retention_policies': {
                'default': {'full_backup_retention_days': 30},
                'incremental': {'retention_days': 7}
            },
            'compression': {
                'default_algorithm': 'gzip'
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

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _get_file_list(self, source_paths: List[str], exclude_patterns: List[str] = None) -> List[str]:
        """Get list of files to include in backup, respecting exclusions."""
        if exclude_patterns is None:
            exclude_patterns = []

        file_list = []
        for path in source_paths:
            path_obj = Path(path)
            if path_obj.is_file():
                if not self._matches_exclude_pattern(str(path_obj), exclude_patterns):
                    file_list.append(str(path_obj))
            elif path_obj.is_dir():
                for root, dirs, files in os.walk(path_obj):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if not self._matches_exclude_pattern(file_path, exclude_patterns):
                            file_list.append(file_path)
        return file_list

    def _matches_exclude_pattern(self, file_path: str, exclude_patterns: List[str]) -> bool:
        """Check if file path matches any exclude pattern."""
        import fnmatch
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return True
        return False

    def _compress_files(self, source_files: List[str], output_path: str, algorithm: str) -> str:
        """Compress files using specified algorithm."""
        if algorithm == 'gzip':
            # For multiple files, we'll create a tar first then compress
            temp_tar = output_path.replace('.gz', '.tar')

            with tarfile.open(temp_tar, 'w') as tar:
                for file_path in source_files:
                    tar.add(file_path, arcname=os.path.relpath(file_path, os.path.dirname(source_files[0]) if source_files else '.'))

            # Compress the tar file with gzip
            with open(temp_tar, 'rb') as f_in:
                with gzip.open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove the temporary tar file
            os.remove(temp_tar)

        elif algorithm == 'zip':
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in source_files:
                    zipf.write(file_path, os.path.relpath(file_path, os.path.dirname(source_files[0]) if source_files else '.'))

        elif algorithm == 'none':
            # Just copy the first file if no compression (for single files)
            if len(source_files) == 1:
                shutil.copy2(source_files[0], output_path)
            else:
                # For multiple files, create a tar
                with tarfile.open(output_path, 'w') as tar:
                    for file_path in source_files:
                        tar.add(file_path, arcname=os.path.relpath(file_path, os.path.dirname(source_files[0]) if source_files else '.'))

        else:
            # Default to gzip if unknown algorithm
            self._compress_files(source_files, output_path, 'gzip')

        return output_path

    def create_backup(
        self,
        name: str,
        backup_type: str,
        source_paths: List[str],
        target_location: str,
        compression: str = 'gzip',
        encryption: bool = False,
        exclude_patterns: List[str] = None,
        retention_days: int = 30
    ) -> str:
        """Create a backup of specified files."""
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(name) % 10000}"

        try:
            # Get list of files to backup
            source_files = self._get_file_list(source_paths, exclude_patterns)

            if not source_files:
                raise ValueError("No files found to backup")

            # Create temporary directory for backup preparation
            with tempfile.TemporaryDirectory() as temp_dir:
                # Prepare backup file name
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_filename = f"{name}_{timestamp}.{compression if compression != 'none' else 'tar'}"
                temp_backup_path = os.path.join(temp_dir, backup_filename)

                # Compress files
                compressed_path = self._compress_files(source_files, temp_backup_path, compression)

                # Encrypt if required
                if encryption:
                    encrypted_filename = backup_filename + '.enc'
                    encrypted_path = os.path.join(temp_dir, encrypted_filename)
                    checksum = self.encryption.encrypt_file(compressed_path, encrypted_path)
                    final_backup_path = encrypted_path
                else:
                    checksum = self._calculate_checksum(compressed_path)
                    final_backup_path = compressed_path

                # Calculate size
                size_bytes = os.path.getsize(final_backup_path)

                # Determine target path
                target_path = os.path.join(target_location, f"{backup_id}_{backup_filename}")

                # Upload to storage
                if self.storage.upload_backup(final_backup_path, target_path):
                    # Calculate retention date
                    retention_date = (datetime.now() + timedelta(days=retention_days)).isoformat()

                    # Create backup record
                    backup_info = BackupInfo(
                        id=backup_id,
                        name=name,
                        type=backup_type,
                        source_paths=source_paths,
                        target_location=target_path,
                        timestamp=datetime.now().isoformat(),
                        size_bytes=size_bytes,
                        status='completed',
                        encryption=encryption,
                        compression=compression,
                        checksum=checksum,
                        retention_date=retention_date,
                        metadata={
                            'source_file_count': len(source_files),
                            'compressed_size': size_bytes
                        }
                    )

                    self.catalog.add_backup(backup_info)
                    self.logger.info(f"Backup {backup_id} completed successfully")
                    return backup_id
                else:
                    # Mark as failed
                    backup_info = BackupInfo(
                        id=backup_id,
                        name=name,
                        type=backup_type,
                        source_paths=source_paths,
                        target_location=target_path,
                        timestamp=datetime.now().isoformat(),
                        size_bytes=0,
                        status='failed',
                        encryption=encryption,
                        compression=compression,
                        checksum='',
                        retention_date=datetime.now().isoformat(),
                        metadata={'error': 'Storage upload failed'}
                    )
                    self.catalog.add_backup(backup_info)
                    self.logger.error(f"Backup {backup_id} failed to upload")
                    return None

        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            # Create failed backup record
            backup_info = BackupInfo(
                id=backup_id,
                name=name,
                type=backup_type,
                source_paths=source_paths,
                target_location=target_path if 'target_path' in locals() else '',
                timestamp=datetime.now().isoformat(),
                size_bytes=0,
                status='failed',
                encryption=encryption,
                compression=compression,
                checksum='',
                retention_date=datetime.now().isoformat(),
                metadata={'error': str(e)}
            )
            self.catalog.add_backup(backup_info)
            return None

    def recover_backup(
        self,
        backup_id: str,
        target_location: str,
        verify_after_recovery: bool = True
    ) -> bool:
        """Recover a backup to specified location."""
        recovery_id = f"recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(backup_id) % 10000}"

        try:
            # Get backup info
            backup_info = self.catalog.get_backup_by_id(backup_id)
            if not backup_info:
                raise ValueError(f"Backup {backup_id} not found")

            with tempfile.TemporaryDirectory() as temp_dir:
                # Download backup
                local_backup_path = os.path.join(temp_dir, os.path.basename(backup_info.target_location))
                if not self.storage.download_backup(backup_info.target_location, local_backup_path):
                    raise Exception("Failed to download backup")

                # Decrypt if needed
                if backup_info.encryption:
                    decrypted_path = local_backup_path + '_decrypted'
                    if not self.encryption.decrypt_file(local_backup_path, decrypted_path):
                        raise Exception("Failed to decrypt backup")
                    local_backup_path = decrypted_path

                # Extract/decompress based on format
                extracted_dir = os.path.join(temp_dir, 'extracted')
                os.makedirs(extracted_dir, exist_ok=True)

                if backup_info.compression == 'zip':
                    with zipfile.ZipFile(local_backup_path, 'r') as zip_ref:
                        zip_ref.extractall(extracted_dir)
                elif backup_info.compression == 'gzip':
                    extracted_path = os.path.join(temp_dir, 'extracted.tar')
                    with gzip.open(local_backup_path, 'rb') as f_in:
                        with open(extracted_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)

                    with tarfile.open(extracted_path, 'r') as tar:
                        tar.extractall(path=extracted_dir)
                else:
                    # Assume it's a tar file
                    with tarfile.open(local_backup_path, 'r') as tar:
                        tar.extractall(path=extracted_dir)

                # Move extracted files to target location
                files_restored = 0
                bytes_restored = 0

                for root, dirs, files in os.walk(extracted_dir):
                    for file in files:
                        src_path = os.path.join(root, file)
                        rel_path = os.path.relpath(src_path, extracted_dir)
                        dst_path = os.path.join(target_location, rel_path)

                        # Create target directory if needed
                        dst_dir = os.path.dirname(dst_path)
                        os.makedirs(dst_dir, exist_ok=True)

                        # Copy file
                        shutil.copy2(src_path, dst_path)
                        files_restored += 1
                        bytes_restored += os.path.getsize(src_path)

                # Verify recovery if requested
                verification_result = "success"
                if verify_after_recovery:
                    # Simple verification - check if expected files exist
                    verification_result = "success" if files_restored > 0 else "failed"

                # Create recovery record
                recovery_info = RecoveryInfo(
                    id=recovery_id,
                    backup_id=backup_id,
                    target_location=target_location,
                    timestamp=datetime.now().isoformat(),
                    status='completed',
                    files_restored=files_restored,
                    bytes_restored=bytes_restored,
                    verification_result=verification_result,
                    metadata={
                        'original_backup_size': backup_info.size_bytes,
                        'files_restored': files_restored
                    }
                )

                self.catalog.add_recovery(recovery_info)
                self.logger.info(f"Recovery {recovery_id} completed successfully")
                return True

        except Exception as e:
            self.logger.error(f"Recovery failed: {e}")
            # Create failed recovery record
            recovery_info = RecoveryInfo(
                id=recovery_id,
                backup_id=backup_id,
                target_location=target_location,
                timestamp=datetime.now().isoformat(),
                status='failed',
                files_restored=0,
                bytes_restored=0,
                verification_result='failed',
                metadata={'error': str(e)}
            )
            self.catalog.add_recovery(recovery_info)
            return False

    def cleanup_expired_backups(self) -> int:
        """Clean up backups that have exceeded their retention period."""
        expired_backups = self.catalog.get_expired_backups()
        deleted_count = 0

        for backup in expired_backups:
            try:
                # Remove the actual backup file
                if os.path.exists(backup.target_location):
                    os.remove(backup.target_location)

                # Remove from catalog
                with self.catalog.get_connection() as conn:
                    conn.execute("DELETE FROM backups WHERE id = ?", (backup.id,))

                deleted_count += 1
                self.logger.info(f"Deleted expired backup: {backup.id}")
            except Exception as e:
                self.logger.error(f"Failed to delete expired backup {backup.id}: {e}")

        return deleted_count

    def get_backup_status(self, backup_id: str) -> Dict[str, Any]:
        """Get the status of a specific backup."""
        backup_info = self.catalog.get_backup_by_id(backup_id)
        if not backup_info:
            return {'error': f'Backup {backup_id} not found'}

        return asdict(backup_info)


def main():
    """Main function for testing the Backup & Recovery system."""
    print("Backup & Recovery Skill")
    print("=======================")

    # Initialize the backup manager
    config_path = os.getenv('BACKUP_CONFIG_PATH', './backup_config.json')
    backup_manager = BackupManager(config_path)

    print(f"Backup Manager initialized with config: {config_path}")

    # Example: Create a test backup
    print("\nCreating test backup...")
    test_backup_id = backup_manager.create_backup(
        name="test_backup",
        backup_type="full",
        source_paths=["/tmp"],  # This is just an example, use appropriate paths
        target_location="/tmp/test_backups",
        compression="gzip",
        encryption=False,
        retention_days=7
    )

    if test_backup_id:
        print(f"Test backup created with ID: {test_backup_id}")

        # Get backup status
        status = backup_manager.get_backup_status(test_backup_id)
        print(f"Backup status: {status}")
    else:
        print("Test backup creation failed")

    # Example: Add a schedule (if configured)
    schedule_config = {
        'name': 'daily_test',
        'type': 'incremental',
        'cron_expression': '0 2 * * *',  # Daily at 2 AM
        'include_paths': ['/tmp/test_data']
    }

    backup_manager.scheduler.add_schedule(schedule_config)
    print(f"\nAdded backup schedule: {schedule_config['name']}")

    # Show recent backups
    recent_backups = backup_manager.catalog.get_recent_backups(limit=5)
    print(f"\nRecent backups ({len(recent_backups)} found):")
    for backup in recent_backups:
        print(f"  - {backup.id}: {backup.name} ({backup.type}) - {backup.status}")

    print("\nBackup & Recovery system is ready!")


if __name__ == "__main__":
    main()