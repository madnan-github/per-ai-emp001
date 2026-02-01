#!/usr/bin/env python3
"""
Credential Manager

This module provides secure credential storage, retrieval, and management
for the Personal AI Employee system. It implements secure credential
storage, rotation, and access controls to ensure safe access to sensitive
authentication information needed by various skills.

Features:
- Secure credential encryption and storage
- Role-based access controls
- Credential rotation and lifecycle management
- Audit logging for compliance
- API key management
- Integration with external vaults
"""

import json
import os
import sqlite3
import hashlib
import secrets
import base64
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from contextlib import contextmanager
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import time


@dataclass
class Credential:
    """Data class to represent a credential."""
    id: str
    type: str
    service_name: str
    value: str
    permissions: List[str]
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None
    rotation_policy: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CredentialEncryption:
    """Handles encryption and decryption of credentials."""

    def __init__(self, master_key: bytes):
        self.master_key = master_key
        self.cipher_suite = Fernet(base64.urlsafe_b64encode(master_key))

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string."""
        return self.cipher_suite.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a ciphertext string."""
        return self.cipher_suite.decrypt(ciphertext.encode()).decode()


class CredentialStore:
    """Manages storage and retrieval of credentials in a secure database."""

    def __init__(self, db_path: str = ":memory:", encryption: CredentialEncryption = None):
        self.db_path = db_path
        self.encryption = encryption
        self.lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """Initialize the database with required tables."""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS credentials (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    value TEXT NOT NULL,
                    permissions TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    rotation_policy TEXT,
                    description TEXT,
                    metadata TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')

            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_service_name ON credentials(service_name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_type ON credentials(type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_expires_at ON credentials(expires_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_is_active ON credentials(is_active)')

    @contextmanager
    def _get_connection(self):
        """Get a thread-safe database connection."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_credential(self, credential: Credential) -> bool:
        """Create a new credential in the store."""
        with self.lock:
            try:
                encrypted_value = self.encryption.encrypt(credential.value) if self.encryption else credential.value

                with self._get_connection() as conn:
                    conn.execute('''
                        INSERT INTO credentials
                        (id, type, service_name, value, permissions, created_at, updated_at,
                         expires_at, rotation_policy, description, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        credential.id, credential.type, credential.service_name,
                        encrypted_value, json.dumps(credential.permissions),
                        credential.created_at, credential.updated_at,
                        credential.expires_at, credential.rotation_policy,
                        credential.description, json.dumps(credential.metadata or {})
                    ))
                return True
            except sqlite3.IntegrityError:
                return False

    def get_credential(self, credential_id: str) -> Optional[Credential]:
        """Retrieve a credential by ID."""
        with self.lock:
            with self._get_connection() as conn:
                row = conn.execute(
                    'SELECT * FROM credentials WHERE id = ? AND is_active = 1',
                    (credential_id,)
                ).fetchone()

                if row:
                    decrypted_value = self.encryption.decrypt(row['value']) if self.encryption else row['value']

                    return Credential(
                        id=row['id'],
                        type=row['type'],
                        service_name=row['service_name'],
                        value=decrypted_value,
                        permissions=json.loads(row['permissions']),
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        expires_at=row['expires_at'],
                        rotation_policy=row['rotation_policy'],
                        description=row['description'],
                        metadata=json.loads(row['metadata']) if row['metadata'] else None
                    )
                return None

    def get_credentials_by_service(self, service_name: str) -> List[Credential]:
        """Retrieve all credentials for a specific service."""
        with self.lock:
            with self._get_connection() as conn:
                rows = conn.execute(
                    'SELECT * FROM credentials WHERE service_name = ? AND is_active = 1',
                    (service_name,)
                ).fetchall()

                credentials = []
                for row in rows:
                    decrypted_value = self.encryption.decrypt(row['value']) if self.encryption else row['value']

                    credentials.append(Credential(
                        id=row['id'],
                        type=row['type'],
                        service_name=row['service_name'],
                        value=decrypted_value,
                        permissions=json.loads(row['permissions']),
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        expires_at=row['expires_at'],
                        rotation_policy=row['rotation_policy'],
                        description=row['description'],
                        metadata=json.loads(row['metadata']) if row['metadata'] else None
                    ))
                return credentials

    def update_credential(self, credential: Credential) -> bool:
        """Update an existing credential."""
        with self.lock:
            try:
                encrypted_value = self.encryption.encrypt(credential.value) if self.encryption else credential.value

                with self._get_connection() as conn:
                    conn.execute('''
                        UPDATE credentials SET
                            type = ?, service_name = ?, value = ?, permissions = ?,
                            updated_at = ?, expires_at = ?, rotation_policy = ?,
                            description = ?, metadata = ?
                        WHERE id = ?
                    ''', (
                        credential.type, credential.service_name, encrypted_value,
                        json.dumps(credential.permissions), credential.updated_at,
                        credential.expires_at, credential.rotation_policy,
                        credential.description, json.dumps(credential.metadata or {}),
                        credential.id
                    ))
                return True
            except Exception:
                return False

    def delete_credential(self, credential_id: str) -> bool:
        """Mark a credential as inactive (soft delete)."""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.execute('UPDATE credentials SET is_active = 0 WHERE id = ?', (credential_id,))
                return cursor.rowcount > 0

    def get_all_credentials(self) -> List[Credential]:
        """Retrieve all active credentials."""
        with self.lock:
            with self._get_connection() as conn:
                rows = conn.execute('SELECT * FROM credentials WHERE is_active = 1').fetchall()

                credentials = []
                for row in rows:
                    decrypted_value = self.encryption.decrypt(row['value']) if self.encryption else row['value']

                    credentials.append(Credential(
                        id=row['id'],
                        type=row['type'],
                        service_name=row['service_name'],
                        value=decrypted_value,
                        permissions=json.loads(row['permissions']),
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        expires_at=row['expires_at'],
                        rotation_policy=row['rotation_policy'],
                        description=row['description'],
                        metadata=json.loads(row['metadata']) if row['metadata'] else None
                    ))
                return credentials


class AccessControl:
    """Manages access control for credential access."""

    def __init__(self, roles: Dict[str, List[str]] = None):
        self.roles = roles or {
            'admin': [
                'create_credential', 'read_credential', 'update_credential',
                'delete_credential', 'rotate_credential', 'manage_access'
            ],
            'service': ['read_credential', 'rotate_own_credential'],
            'auditor': ['read_audit_logs', 'generate_reports']
        }

    def check_permission(self, user_roles: List[str], required_permission: str) -> bool:
        """Check if a user has the required permission."""
        for role in user_roles:
            if role in self.roles and required_permission in self.roles[role]:
                return True
        return False

    def authenticate_service(self, service_name: str, service_token: str) -> bool:
        """Authenticate a service requesting credentials."""
        # In a real implementation, this would verify the service token
        # For now, we'll implement a basic check
        return service_token and len(service_token) >= 10  # Basic validation


class CredentialAuditLogger:
    """Handles logging of credential access for compliance and security."""

    def __init__(self, log_path: str = "/tmp/credential_audit.log"):
        self.log_path = log_path
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for audit trail."""
        logger = logging.getLogger('CredentialAudit')
        logger.setLevel(logging.INFO)

        # Create file handler
        handler = logging.FileHandler(self.log_path)
        formatter = logging.Formatter('%(asctime)s - AUDIT - %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    def log_access(self, user: str, credential_id: str, action: str, success: bool, details: str = ""):
        """Log credential access event."""
        status = "SUCCESS" if success else "FAILURE"
        self.logger.info(f"USER={user} CREDENTIAL={credential_id} ACTION={action} STATUS={status} DETAILS={details}")

    def log_creation(self, user: str, credential_id: str, service: str):
        """Log credential creation event."""
        self.logger.info(f"USER={user} ACTION=CREATE_CREDENTIAL CREDENTIAL={credential_id} SERVICE={service}")

    def log_rotation(self, user: str, credential_id: str, old_credential_hash: str, new_credential_hash: str):
        """Log credential rotation event."""
        self.logger.info(f"USER={user} ACTION=ROTATE_CREDENTIAL CREDENTIAL={credential_id} OLD_HASH={old_credential_hash} NEW_HASH={new_credential_hash}")


class CredentialRotationManager:
    """Manages automatic credential rotation based on policies."""

    def __init__(self, credential_store: CredentialStore, audit_logger: CredentialAuditLogger):
        self.credential_store = credential_store
        self.audit_logger = audit_logger
        self.default_rotation_interval = timedelta(days=90)

    def check_and_rotate_expired_credentials(self) -> List[str]:
        """Check for expired credentials and rotate them."""
        credentials = self.credential_store.get_all_credentials()
        rotated_credentials = []

        for cred in credentials:
            if cred.expires_at:
                expiry_date = datetime.fromisoformat(cred.expires_at)
                if datetime.now() >= expiry_date:
                    try:
                        # Generate new credential
                        new_value = self.generate_secure_credential_value(cred.type)

                        # Update the credential
                        updated_cred = Credential(
                            id=cred.id,
                            type=cred.type,
                            service_name=cred.service_name,
                            value=new_value,
                            permissions=cred.permissions,
                            created_at=cred.created_at,
                            updated_at=datetime.now().isoformat(),
                            expires_at=(datetime.now() + self.default_rotation_interval).isoformat(),
                            rotation_policy=cred.rotation_policy,
                            description=cred.description,
                            metadata=cred.metadata
                        )

                        if self.credential_store.update_credential(updated_cred):
                            rotated_credentials.append(cred.id)
                            self.audit_logger.log_rotation(
                                user="system",
                                credential_id=cred.id,
                                old_credential_hash=hashlib.sha256(cred.value.encode()).hexdigest(),
                                new_credential_hash=hashlib.sha256(new_value.encode()).hexdigest()
                            )

                    except Exception as e:
                        print(f"Failed to rotate credential {cred.id}: {e}")

        return rotated_credentials

    def generate_secure_credential_value(self, credential_type: str) -> str:
        """Generate a secure credential value based on type."""
        if credential_type == 'api_key':
            # Generate a random API key
            return f"sk-{secrets.token_urlsafe(32)}"
        elif credential_type == 'password':
            # Generate a secure password
            alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
            return ''.join(secrets.choice(alphabet) for _ in range(20))
        elif credential_type == 'token':
            # Generate an OAuth-like token
            return secrets.token_urlsafe(32)
        else:
            # Default to a generic secure token
            return secrets.token_urlsafe(32)


class CredentialManager:
    """
    Main credential manager class that orchestrates credential storage,
    access control, and lifecycle management.
    """

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.logger = self._setup_logger()

        # Initialize components
        self.encryption = self._setup_encryption()
        self.credential_store = CredentialStore(
            db_path=os.getenv('CREDENTIAL_MANAGER_DATABASE_PATH', ':memory:'),
            encryption=self.encryption
        )
        self.access_control = AccessControl()
        self.audit_logger = CredentialAuditLogger(
            log_path=os.getenv('CREDENTIAL_MANAGER_AUDIT_LOG_PATH', '/tmp/credential_audit.log')
        )
        self.rotation_manager = CredentialRotationManager(self.credential_store, self.audit_logger)

        # Load configuration
        self.config = self._load_config()

    def _setup_logger(self) -> logging.Logger:
        """Setup main logger for the credential manager."""
        logger = logging.getLogger('CredentialManager')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    def _setup_encryption(self) -> Optional[CredentialEncryption]:
        """Setup encryption using master key."""
        try:
            # Try to get master key from file
            master_key_path = os.getenv('CREDENTIAL_MANAGER_MASTER_KEY_PATH')
            if master_key_path and os.path.exists(master_key_path):
                with open(master_key_path, 'rb') as f:
                    master_key = f.read()
                return CredentialEncryption(master_key)

            # Fallback to environment variable (less secure)
            master_key_b64 = os.getenv('CREDENTIAL_MANAGER_MASTER_KEY_B64')
            if master_key_b64:
                master_key = base64.urlsafe_b64decode(master_key_b64)
                return CredentialEncryption(master_key)

            # If no key provided, warn but continue without encryption
            self.logger.warning("No encryption key provided, credentials will be stored in plain text")
            return None
        except Exception as e:
            self.logger.error(f"Failed to setup encryption: {e}")
            return None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment."""
        config = {
            'rotation_interval_days': int(os.getenv('CREDENTIAL_MANAGER_ROTATION_INTERVAL_DAYS', '30')),
            'default_permissions': ['read_credential']
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

    def create_credential(self, credential_type: str, service_name: str, credential_value: str,
                         permissions: List[str] = None, expiration_date: str = None,
                         rotation_policy: str = None, description: str = None,
                         requesting_user: str = "system", context: Dict[str, Any] = None) -> str:
        """
        Create a new credential with the specified parameters.

        Returns:
            Credential ID if successful, None if failed
        """
        # Generate a unique ID for the credential
        credential_id = f"cred_{secrets.token_urlsafe(8)}"

        # Set default permissions if not provided
        if permissions is None:
            permissions = self.config.get('default_permissions', ['read_credential'])

        # Set default expiration if not provided
        if expiration_date is None:
            rotation_interval = self.config.get('rotation_interval_days', 30)
            exp_date = datetime.now() + timedelta(days=rotation_interval)
            expiration_date = exp_date.isoformat()

        # Create the credential object
        credential = Credential(
            id=credential_id,
            type=credential_type,
            service_name=service_name,
            value=credential_value,
            permissions=permissions,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            expires_at=expiration_date,
            rotation_policy=rotation_policy,
            description=description,
            metadata=context
        )

        # Store the credential
        success = self.credential_store.create_credential(credential)

        if success:
            self.audit_logger.log_creation(requesting_user, credential_id, service_name)
            self.logger.info(f"Credential created: {credential_id} for {service_name}")
            return credential_id
        else:
            self.logger.error(f"Failed to create credential for {service_name}")
            return None

    def get_credential(self, credential_id: str, requesting_user: str, user_roles: List[str]) -> Optional[Credential]:
        """
        Retrieve a credential by ID with proper authentication and authorization.
        """
        # Check if user has read permission
        if not self.access_control.check_permission(user_roles, 'read_credential'):
            self.audit_logger.log_access(requesting_user, credential_id, 'read', False, 'insufficient_permissions')
            self.logger.warning(f"Access denied for {requesting_user} to credential {credential_id}")
            return None

        # Get the credential from store
        credential = self.credential_store.get_credential(credential_id)

        if credential:
            self.audit_logger.log_access(requesting_user, credential_id, 'read', True)
            self.logger.info(f"Credential accessed: {credential_id} by {requesting_user}")
            return credential
        else:
            self.audit_logger.log_access(requesting_user, credential_id, 'read', False, 'not_found')
            self.logger.warning(f"Credential not found: {credential_id}")
            return None

    def authenticate_service_and_get_credential(self, service_name: str, service_token: str, credential_id: str) -> Optional[Credential]:
        """
        Authenticate a service and return the requested credential if authorized.
        """
        # Authenticate the service
        if not self.access_control.authenticate_service(service_name, service_token):
            self.audit_logger.log_access(service_name, credential_id, 'read', False, 'authentication_failed')
            self.logger.warning(f"Service authentication failed for {service_name}")
            return None

        # Get the credential by ID
        credential = self.credential_store.get_credential(credential_id)

        if credential and credential.service_name == service_name:
            self.audit_logger.log_access(service_name, credential_id, 'read', True)
            self.logger.info(f"Service {service_name} accessed credential {credential_id}")
            return credential
        else:
            self.audit_logger.log_access(service_name, credential_id, 'read', False, 'not_found_or_not_owned')
            self.logger.warning(f"Service {service_name} tried to access unauthorized credential {credential_id}")
            return None

    def rotate_credential(self, credential_id: str, new_value: str = None, requesting_user: str = "system") -> bool:
        """
        Rotate a credential with a new value.
        """
        # Get the current credential
        current_credential = self.credential_store.get_credential(credential_id)

        if not current_credential:
            self.logger.error(f"Cannot rotate non-existent credential: {credential_id}")
            return False

        # Generate new value if not provided
        if new_value is None:
            new_value = self.rotation_manager.generate_secure_credential_value(current_credential.type)

        # Update the credential with new value
        updated_credential = Credential(
            id=current_credential.id,
            type=current_credential.type,
            service_name=current_credential.service_name,
            value=new_value,
            permissions=current_credential.permissions,
            created_at=current_credential.created_at,
            updated_at=datetime.now().isoformat(),
            expires_at=current_credential.expires_at,
            rotation_policy=current_credential.rotation_policy,
            description=current_credential.description,
            metadata=current_credential.metadata
        )

        success = self.credential_store.update_credential(updated_credential)

        if success:
            self.audit_logger.log_rotation(
                user=requesting_user,
                credential_id=credential_id,
                old_credential_hash=hashlib.sha256(current_credential.value.encode()).hexdigest(),
                new_credential_hash=hashlib.sha256(new_value.encode()).hexdigest()
            )
            self.logger.info(f"Credential rotated: {credential_id}")
            return True
        else:
            self.logger.error(f"Failed to rotate credential: {credential_id}")
            return False

    def list_credentials_for_service(self, service_name: str) -> List[Credential]:
        """List all credentials for a specific service."""
        credentials = self.credential_store.get_credentials_by_service(service_name)
        self.logger.info(f"Retrieved {len(credentials)} credentials for service {service_name}")
        return credentials

    def delete_credential(self, credential_id: str, requesting_user: str) -> bool:
        """Mark a credential as inactive."""
        success = self.credential_store.delete_credential(credential_id)
        if success:
            self.audit_logger.log_access(requesting_user, credential_id, 'delete', True)
            self.logger.info(f"Credential deleted: {credential_id}")
        else:
            self.logger.error(f"Failed to delete credential: {credential_id}")
        return success

    def run_periodic_tasks(self):
        """Run periodic tasks like credential rotation."""
        rotated_credentials = self.rotation_manager.check_and_rotate_expired_credentials()
        if rotated_credentials:
            self.logger.info(f"Rotated {len(rotated_credentials)} credentials: {rotated_credentials}")
        else:
            self.logger.debug("No credentials needed rotation")


def main():
    """Main function for testing the Credential Manager."""
    print("Credential Manager Skill")
    print("========================")

    # Initialize the credential manager
    config_path = os.getenv('CREDENTIAL_MANAGER_CONFIG_PATH', './credential_config.json')
    manager = CredentialManager(config_path)

    print(f"Credential Manager initialized with config: {config_path}")

    # Test credential creation
    print("\nTesting credential creation...")
    cred_id = manager.create_credential(
        credential_type="api_key",
        service_name="gmail_api",
        credential_value="sk-1234567890abcdef",
        permissions=["read_credential"],
        description="Gmail API key for email handling skill",
        requesting_user="admin"
    )

    if cred_id:
        print(f"Created credential: {cred_id}")

        # Test credential retrieval
        print("\nTesting credential retrieval...")
        retrieved_cred = manager.get_credential(cred_id, "admin", ["admin"])
        if retrieved_cred:
            print(f"Retrieved credential: {retrieved_cred.service_name} - {retrieved_cred.type}")

        # Test service authentication
        print("\nTesting service authentication...")
        service_cred = manager.authenticate_service_and_get_credential("gmail_api", "valid_token_1234567890", cred_id)
        if service_cred:
            print(f"Service authenticated and retrieved: {service_cred.service_name}")

        # Test credential listing
        print("\nTesting credential listing...")
        service_creds = manager.list_credentials_for_service("gmail_api")
        print(f"Found {len(service_creds)} credentials for gmail_api service")

    # Run periodic tasks to check for rotations
    print("\nRunning periodic tasks...")
    manager.run_periodic_tasks()

    print("\nCredential Manager is ready to securely manage credentials for all skills!")


if __name__ == "__main__":
    main()