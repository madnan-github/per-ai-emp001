#!/usr/bin/env python3
"""
Approval Processor - Manages approval workflows for sensitive operations

This script implements an approval processing system that manages approval workflows
for sensitive operations, payments, communications, and other business-critical
actions, ensuring appropriate governance and security controls.
"""

import os
import sys
import json
import yaml
import asyncio
import logging
import sqlite3
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class ApprovalStatus(Enum):
    """Approval request status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


class ApprovalPriority(Enum):
    """Approval request priority"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ApprovalRequest:
    """Represents an approval request with all required fields"""
    id: str
    requestor_id: str
    requestor_name: str
    requestor_email: str
    approval_type: str
    category: str
    request_date: float
    due_date: float
    priority: ApprovalPriority
    amount: float
    currency: str
    description: str
    justification: str
    associated_documents: List[Dict[str, str]]
    risk_level: str
    current_approver_id: str
    current_approver_name: str
    current_approver_email: str
    approval_chain: List[Dict[str, Any]]
    current_level: int
    status: ApprovalStatus
    created_by: str
    metadata: Optional[Dict] = None
    approval_history: Optional[List[Dict]] = None
    cancellation_reason: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert approval request to dictionary format"""
        result = asdict(self)
        result['priority'] = self.priority.value
        result['status'] = self.status.value
        return result


@dataclass
class ApprovalAction:
    """Represents an approval action taken by an approver"""
    request_id: str
    approver_id: str
    approver_name: str
    approver_email: str
    action: str  # 'approve', 'reject', 'request_info', 'escalate'
    timestamp: float
    comments: str
    next_approver_id: Optional[str] = None
    next_approver_name: Optional[str] = None
    next_approver_email: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert approval action to dictionary format"""
        return asdict(self)


class ApprovalStore:
    """Manages storage and retrieval of approval requests and actions"""

    def __init__(self, db_path: str = "approvals.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create approval_requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS approval_requests (
                id TEXT PRIMARY KEY,
                requestor_id TEXT,
                requestor_name TEXT,
                requestor_email TEXT,
                approval_type TEXT,
                category TEXT,
                request_date REAL,
                due_date REAL,
                priority INTEGER,
                amount REAL,
                currency TEXT,
                description TEXT,
                justification TEXT,
                associated_documents TEXT,
                risk_level TEXT,
                current_approver_id TEXT,
                current_approver_name TEXT,
                current_approver_email TEXT,
                approval_chain TEXT,
                current_level INTEGER,
                status TEXT,
                created_by TEXT,
                metadata TEXT,
                approval_history TEXT,
                cancellation_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create approval_actions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS approval_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT,
                approver_id TEXT,
                approver_name TEXT,
                approver_email TEXT,
                action TEXT,
                timestamp REAL,
                comments TEXT,
                next_approver_id TEXT,
                next_approver_name TEXT,
                next_approver_email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON approval_requests(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_current_approver ON approval_requests(current_approver_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_requestor ON approval_requests(requestor_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_due_date ON approval_requests(due_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_request_id ON approval_actions(request_id)')

        conn.commit()
        conn.close()

    def save_approval_request(self, request: ApprovalRequest):
        """Save an approval request to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO approval_requests
            (id, requestor_id, requestor_name, requestor_email, approval_type, category, request_date, due_date,
             priority, amount, currency, description, justification, associated_documents, risk_level,
             current_approver_id, current_approver_name, current_approver_email, approval_chain, current_level,
             status, created_by, metadata, approval_history, cancellation_reason, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            request.id,
            request.requestor_id,
            request.requestor_name,
            request.requestor_email,
            request.approval_type,
            request.category,
            request.request_date,
            request.due_date,
            request.priority.value,
            request.amount,
            request.currency,
            request.description,
            request.justification,
            json.dumps(request.associated_documents),
            request.risk_level,
            request.current_approver_id,
            request.current_approver_name,
            request.current_approver_email,
            json.dumps(request.approval_chain),
            request.current_level,
            request.status.value,
            request.created_by,
            json.dumps(request.metadata or {}),
            json.dumps(request.approval_history or []),
            request.cancellation_reason
        ))

        conn.commit()
        conn.close()

    def save_approval_action(self, action: ApprovalAction):
        """Save an approval action to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO approval_actions
            (request_id, approver_id, approver_name, approver_email, action, timestamp, comments,
             next_approver_id, next_approver_name, next_approver_email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            action.request_id,
            action.approver_id,
            action.approver_name,
            action.approver_email,
            action.action,
            action.timestamp,
            action.comments,
            action.next_approver_id,
            action.next_approver_name,
            action.next_approver_email
        ))

        conn.commit()
        conn.close()

    def get_pending_approvals(self, approver_id: str) -> List[ApprovalRequest]:
        """Get pending approval requests for a specific approver"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM approval_requests
            WHERE current_approver_id = ? AND status = ?
            ORDER BY priority DESC, request_date ASC
        ''', (approver_id, ApprovalStatus.PENDING.value))

        rows = cursor.fetchall()
        conn.close()

        requests = []
        for row in rows:
            request = self._row_to_approval_request(row)
            requests.append(request)

        return requests

    def get_approval_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get a specific approval request by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM approval_requests WHERE id = ?', (request_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_approval_request(row)
        return None

    def get_approval_history(self, request_id: str) -> List[ApprovalAction]:
        """Get approval history for a specific request"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM approval_actions
            WHERE request_id = ?
            ORDER BY timestamp ASC
        ''', (request_id,))

        rows = cursor.fetchall()
        conn.close()

        actions = []
        for row in rows:
            action = ApprovalAction(
                request_id=row[1],
                approver_id=row[2],
                approver_name=row[3],
                approver_email=row[4],
                action=row[5],
                timestamp=row[6],
                comments=row[7],
                next_approver_id=row[8],
                next_approver_name=row[9],
                next_approver_email=row[10]
            )
            actions.append(action)

        return actions

    def _row_to_approval_request(self, row) -> ApprovalRequest:
        """Convert database row to ApprovalRequest object"""
        return ApprovalRequest(
            id=row[0],
            requestor_id=row[1],
            requestor_name=row[2],
            requestor_email=row[3],
            approval_type=row[4],
            category=row[5],
            request_date=row[6],
            due_date=row[7],
            priority=ApprovalPriority(row[8]),
            amount=row[9],
            currency=row[10],
            description=row[11],
            justification=row[12],
            associated_documents=json.loads(row[13]) if row[13] else [],
            risk_level=row[14],
            current_approver_id=row[15],
            current_approver_name=row[16],
            current_approver_email=row[17],
            approval_chain=json.loads(row[18]) if row[18] else [],
            current_level=row[19],
            status=ApprovalStatus(row[20]),
            created_by=row[21],
            metadata=json.loads(row[22]) if row[22] else {},
            approval_history=json.loads(row[23]) if row[23] else [],
            cancellation_reason=row[24]
        )


class ApprovalChainEvaluator:
    """Evaluates approval chains and determines approvers"""

    def __init__(self, config: Dict):
        self.config = config

    def get_initial_approver(self, request: ApprovalRequest) -> Optional[Dict[str, str]]:
        """Determine the initial approver for a request based on thresholds"""
        # Get approval chains configuration for this category
        approval_chains = self.config.get('approval_chains', {})

        # Look up the specific chain for this request type
        if request.approval_type in approval_chains:
            type_chains = approval_chains[request.approval_type]

            if request.category in type_chains:
                category_chain = type_chains[request.category]

                # Find the appropriate level based on amount/other criteria
                if 'thresholds' in category_chain:
                    # Sort thresholds by amount (descending) and find the first one that matches
                    thresholds = sorted(category_chain['thresholds'], key=lambda x: x['amount'], reverse=True)

                    for threshold in thresholds:
                        if request.amount >= threshold['amount']:
                            # For simplicity, return the first approver in the first matching level
                            if 'approvers' in threshold and len(threshold['approvers']) > 0:
                                # In a real system, you'd have logic to determine actual user IDs
                                # For now, returning a placeholder
                                return {
                                    'id': f"approver-{threshold['level']}",
                                    'name': f"Approver Level {threshold['level']}",
                                    'email': f"approver{threshold['level']}@company.com"
                                }

        # Default fallback approver
        return {
            'id': 'default-approver',
            'name': 'Default Approver',
            'email': 'default@approver.com'
        }

    def get_next_approver(self, request: ApprovalRequest, current_approver_index: int) -> Optional[Dict[str, str]]:
        """Get the next approver in the chain"""
        # For this implementation, we'll just return a placeholder
        # In a real system, you'd have more complex logic based on the approval chain configuration
        if current_approver_index + 1 < len(request.approval_chain):
            next_approver = request.approval_chain[current_approver_index + 1]
            return next_approver

        return None


class AutoApprovalEvaluator:
    """Evaluates auto-approval rules"""

    def __init__(self, config: Dict):
        self.config = config
        self.auto_approval_rules = config.get('auto_approval_rules', {}).get('rules', [])

    def should_auto_approve(self, request: ApprovalRequest) -> tuple[bool, str]:
        """Check if a request should be auto-approved"""
        for rule in self.auto_approval_rules:
            # Check if all conditions are met
            conditions_met = True

            for condition in rule.get('conditions', []):
                field = condition.get('field')
                operator = condition.get('operator')
                value = condition.get('value')

                # Get the actual value from the request
                actual_value = getattr(request, field, None)

                if actual_value is None:
                    conditions_met = False
                    break

                # Evaluate the condition based on the operator
                if operator == '=':
                    if actual_value != value:
                        conditions_met = False
                        break
                elif operator == '!=':
                    if actual_value == value:
                        conditions_met = False
                        break
                elif operator == '>':
                    if actual_value <= value:
                        conditions_met = False
                        break
                elif operator == '>=':
                    if actual_value < value:
                        conditions_met = False
                        break
                elif operator == '<':
                    if actual_value >= value:
                        conditions_met = False
                        break
                elif operator == '<=':
                    if actual_value > value:
                        conditions_met = False
                        break
                elif operator == 'in':
                    if actual_value not in value:
                        conditions_met = False
                        break
                elif operator == 'contains':
                    if isinstance(actual_value, str) and value not in actual_value:
                        conditions_met = False
                        break

            if conditions_met:
                return True, rule.get('reason', 'Auto-approved by rule')

        return False, 'Does not meet auto-approval criteria'


class ApprovalNotifier:
    """Handles notification of approvers and requestors"""

    def __init__(self, config: Dict):
        self.config = config
        self.smtp_config = config.get('notifications', {}).get('channels', {}).get('email', {})

    def notify_approver(self, request: ApprovalRequest):
        """Send notification to the current approver"""
        if not self.smtp_config.get('enabled', False):
            return

        subject = f"Action Required: Approval Request #{request.id}"

        html_body = f"""
        <h2>Approval Request #{request.id}</h2>
        <p><strong>Requestor:</strong> {request.requestor_name} ({request.requestor_email})</p>
        <p><strong>Category:</strong> {request.category}</p>
        <p><strong>Amount:</strong> {request.currency} {request.amount}</p>
        <p><strong>Description:</strong> {request.description}</p>
        <p><strong>Justification:</strong> {request.justification}</p>
        <p><strong>Risk Level:</strong> {request.risk_level}</p>
        <p><strong>Due Date:</strong> {datetime.fromtimestamp(request.due_date)}</p>
        """

        self._send_email([request.current_approver_email], subject, html_body)

    def notify_requestor(self, request: ApprovalRequest, action: str, comments: str = ""):
        """Notify the requestor about the action taken"""
        if not self.smtp_config.get('enabled', False):
            return

        subject = f"Approval Update: Request #{request.id} - {action.upper()}"

        html_body = f"""
        <h2>Approval Update for Request #{request.id}</h2>
        <p><strong>Action Taken:</strong> {action.upper()}</p>
        <p><strong>By:</strong> {request.current_approver_name}</p>
        <p><strong>Status:</strong> {request.status.value}</p>
        """

        if comments:
            html_body += f"<p><strong>Comments:</strong> {comments}</p>"

        self._send_email([request.requestor_email], subject, html_body)

    def _send_email(self, recipients: List[str], subject: str, body: str):
        """Send an email using SMTP"""
        if not self.smtp_config.get('enabled', False):
            return

        try:
            smtp_server = self.smtp_config.get('smtp_server')
            smtp_port = self.smtp_config.get('smtp_port', 587)
            username = self.smtp_config.get('username')
            password = os.getenv(self.smtp_config.get('password_env_var', 'SMTP_PASSWORD'))
            from_address = self.smtp_config.get('from_address', 'approvals@company.com')

            msg = MIMEMultipart()
            msg['From'] = from_address
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'html'))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)

            print(f"Email notification sent to {recipients}")
        except Exception as e:
            print(f"Failed to send email notification: {e}")


class ApprovalProcessor:
    """Main approval processor class"""

    def __init__(self, config_path: str = None):
        self.config = self.load_config(config_path)
        self.store = ApprovalStore()
        self.chain_evaluator = ApprovalChainEvaluator(self.config)
        self.auto_approval_evaluator = AutoApprovalEvaluator(self.config)
        self.notifier = ApprovalNotifier(self.config)
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
                'retention_days': 365
            },
            'approval_chains': {
                'financial': {
                    'payment_approvals': {
                        'enabled': True,
                        'thresholds': [
                            {'amount': 0, 'level': 1, 'approvers': [{'role': 'manager'}]},
                            {'amount': 5000, 'level': 2, 'approvers': [{'role': 'director'}]},
                            {'amount': 25000, 'level': 3, 'approvers': [{'role': 'vp'}]}
                        ]
                    }
                }
            },
            'auto_approval_rules': {
                'enabled': True,
                'rules': []
            },
            'notifications': {
                'channels': {
                    'email': {'enabled': False}
                }
            },
            'escalation_rules': {
                'time_based': {
                    'enabled': True,
                    'rules': []
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

    def submit_request(self, request_data: Dict) -> str:
        """Submit a new approval request"""
        # Generate request ID
        request_id = self._generate_request_id(request_data)

        # Determine the initial approver
        initial_approver = self.chain_evaluator.get_initial_approver(
            ApprovalRequest(
                id=request_id,
                requestor_id=request_data.get('requestor_id', 'unknown'),
                requestor_name=request_data.get('requestor_name', 'Unknown'),
                requestor_email=request_data.get('requestor_email', ''),
                approval_type=request_data.get('approval_type', 'general'),
                category=request_data.get('category', 'general'),
                request_date=time.time(),
                due_date=time.time() + (7 * 24 * 60 * 60),  # Default: 1 week
                priority=ApprovalPriority(request_data.get('priority', ApprovalPriority.NORMAL.value)),
                amount=request_data.get('amount', 0.0),
                currency=request_data.get('currency', 'USD'),
                description=request_data.get('description', ''),
                justification=request_data.get('justification', ''),
                associated_documents=request_data.get('associated_documents', []),
                risk_level=request_data.get('risk_level', 'medium'),
                current_approver_id='',
                current_approver_name='',
                current_approver_email='',
                approval_chain=[],
                current_level=0,
                status=ApprovalStatus.PENDING,
                created_by=request_data.get('requestor_id', 'unknown')
            )
        )

        if not initial_approver:
            raise ValueError("Could not determine initial approver for request")

        # Check for auto-approval
        auto_approve, reason = self.auto_approval_evaluator.should_auto_approve(
            ApprovalRequest(
                id=request_id,
                requestor_id=request_data.get('requestor_id', 'unknown'),
                requestor_name=request_data.get('requestor_name', 'Unknown'),
                requestor_email=request_data.get('requestor_email', ''),
                approval_type=request_data.get('approval_type', 'general'),
                category=request_data.get('category', 'general'),
                request_date=time.time(),
                due_date=time.time() + (7 * 24 * 60 * 60),  # Default: 1 week
                priority=ApprovalPriority(request_data.get('priority', ApprovalPriority.NORMAL.value)),
                amount=request_data.get('amount', 0.0),
                currency=request_data.get('currency', 'USD'),
                description=request_data.get('description', ''),
                justification=request_data.get('justification', ''),
                associated_documents=request_data.get('associated_documents', []),
                risk_level=request_data.get('risk_level', 'medium'),
                current_approver_id=initial_approver['id'],
                current_approver_name=initial_approver['name'],
                current_approver_email=initial_approver['email'],
                approval_chain=[],  # Will be populated based on config
                current_level=0,
                status=ApprovalStatus.APPROVED if auto_approve else ApprovalStatus.PENDING,
                created_by=request_data.get('requestor_id', 'unknown')
            )
        )

        # Create the approval request object
        request = ApprovalRequest(
            id=request_id,
            requestor_id=request_data.get('requestor_id', 'unknown'),
            requestor_name=request_data.get('requestor_name', 'Unknown'),
            requestor_email=request_data.get('requestor_email', ''),
            approval_type=request_data.get('approval_type', 'general'),
            category=request_data.get('category', 'general'),
            request_date=time.time(),
            due_date=request_data.get('due_date', time.time() + (7 * 24 * 60 * 60)),  # Default: 1 week
            priority=ApprovalPriority(request_data.get('priority', ApprovalPriority.NORMAL.value)),
            amount=request_data.get('amount', 0.0),
            currency=request_data.get('currency', 'USD'),
            description=request_data.get('description', ''),
            justification=request_data.get('justification', ''),
            associated_documents=request_data.get('associated_documents', []),
            risk_level=request_data.get('risk_level', 'medium'),
            current_approver_id=initial_approver['id'] if not auto_approve else request_data.get('requestor_id', 'unknown'),
            current_approver_name=initial_approver['name'] if not auto_approve else request_data.get('requestor_name', 'Unknown'),
            current_approver_email=initial_approver['email'] if not auto_approve else request_data.get('requestor_email', ''),
            approval_chain=[],  # Will be populated based on the actual approval chain configuration
            current_level=0,
            status=ApprovalStatus.APPROVED if auto_approve else ApprovalStatus.PENDING,
            created_by=request_data.get('requestor_id', 'unknown'),
            metadata=request_data.get('metadata', {}),
            approval_history=[]
        )

        # Save the request
        self.store.save_approval_request(request)

        # If not auto-approved, notify the first approver
        if not auto_approve:
            self.notifier.notify_approver(request)
        else:
            # For auto-approved requests, notify the requestor
            self.notifier.notify_requestor(request, 'auto-approved', reason)

        print(f"Submitted approval request {request_id}. Auto-approved: {auto_approve}")
        return request_id

    def approve_request(self, request_id: str, approver_id: str, approver_name: str, approver_email: str, comments: str = "") -> bool:
        """Approve an approval request"""
        request = self.store.get_approval_request(request_id)
        if not request:
            print(f"Request {request_id} not found")
            return False

        if request.status != ApprovalStatus.PENDING:
            print(f"Request {request_id} is not in pending status")
            return False

        # Record the approval action
        action = ApprovalAction(
            request_id=request_id,
            approver_id=approver_id,
            approver_name=approver_name,
            approver_email=approver_email,
            action='approve',
            timestamp=time.time(),
            comments=comments
        )
        self.store.save_approval_action(action)

        # Check if this was the final approval in the chain
        # For simplicity in this example, we'll assume a single-level approval
        # In a real system, you'd check the approval chain configuration
        next_approver = self.chain_evaluator.get_next_approver(request, request.current_level)

        if next_approver:
            # Move to next approver in chain
            updated_request = ApprovalRequest(**request.to_dict())
            updated_request.current_approver_id = next_approver['id']
            updated_request.current_approver_name = next_approver['name']
            updated_request.current_approver_email = next_approver['email']
            updated_request.current_level += 1
            updated_request.approval_history.append(action.to_dict())

            self.store.save_approval_request(updated_request)
            self.notifier.notify_approver(updated_request)

            print(f"Request {request_id} approved, forwarded to next approver: {next_approver['name']}")
        else:
            # Final approval - mark as approved
            updated_request = ApprovalRequest(**request.to_dict())
            updated_request.status = ApprovalStatus.APPROVED
            updated_request.approval_history.append(action.to_dict())

            self.store.save_approval_request(updated_request)
            self.notifier.notify_requestor(updated_request, 'approved', comments)

            print(f"Request {request_id} fully approved")

        return True

    def reject_request(self, request_id: str, approver_id: str, approver_name: str, approver_email: str, comments: str = "") -> bool:
        """Reject an approval request"""
        request = self.store.get_approval_request(request_id)
        if not request:
            print(f"Request {request_id} not found")
            return False

        if request.status != ApprovalStatus.PENDING:
            print(f"Request {request_id} is not in pending status")
            return False

        # Record the rejection action
        action = ApprovalAction(
            request_id=request_id,
            approver_id=approver_id,
            approver_name=approver_name,
            approver_email=approver_email,
            action='reject',
            timestamp=time.time(),
            comments=comments
        )
        self.store.save_approval_action(action)

        # Update the request status to rejected
        updated_request = ApprovalRequest(**request.to_dict())
        updated_request.status = ApprovalStatus.REJECTED
        updated_request.approval_history.append(action.to_dict())

        self.store.save_approval_request(updated_request)
        self.notifier.notify_requestor(updated_request, 'rejected', comments)

        print(f"Request {request_id} rejected by {approver_name}")
        return True

    def cancel_request(self, request_id: str, requestor_id: str, reason: str = "") -> bool:
        """Cancel an approval request"""
        request = self.store.get_approval_request(request_id)
        if not request:
            print(f"Request {request_id} not found")
            return False

        if request.requestor_id != requestor_id:
            print(f"Unauthorized: Requestor {requestor_id} cannot cancel request {request_id}")
            return False

        if request.status != ApprovalStatus.PENDING:
            print(f"Request {request_id} is not in pending status and cannot be cancelled")
            return False

        # Update the request status to cancelled
        updated_request = ApprovalRequest(**request.to_dict())
        updated_request.status = ApprovalStatus.CANCELLED
        updated_request.cancellation_reason = reason

        self.store.save_approval_request(updated_request)

        print(f"Request {request_id} cancelled by requestor {requestor_id}")
        return True

    def _generate_request_id(self, request_data: Dict) -> str:
        """Generate a unique request ID"""
        content = f"{request_data.get('requestor_id', '')}:{request_data.get('description', '')}:{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def check_for_overdue_approvals(self):
        """Check for overdue approval requests and handle escalations"""
        conn = sqlite3.connect(self.store.db_path)
        cursor = conn.cursor()

        # Find pending requests that are overdue
        cursor.execute('''
            SELECT * FROM approval_requests
            WHERE status = ? AND due_date < ?
        ''', (ApprovalStatus.PENDING.value, time.time()))

        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            request = self.store._row_to_approval_request(row)
            print(f"Overdue request detected: {request.id}")

            # In a real system, you would implement escalation logic here
            # For now, we'll just update the status to escalated
            updated_request = ApprovalRequest(**request.to_dict())
            updated_request.status = ApprovalStatus.ESCALATED

            self.store.save_approval_request(updated_request)

    async def run_escalation_check(self):
        """Run periodic checks for escalation conditions"""
        while self.running:
            try:
                await self.check_for_overdue_approvals()
            except Exception as e:
                print(f"Error during escalation check: {e}")

            # Wait for the escalation check interval (1 hour)
            await asyncio.sleep(3600)

    async def run_continuous(self):
        """Run the approval processor continuously"""
        self.running = True
        print("Starting approval processor...")

        # Start escalation checker in background
        escalation_task = asyncio.create_task(self.run_escalation_check())

        try:
            while self.running:
                # Perform any periodic maintenance tasks
                await asyncio.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("Received interrupt signal")
        finally:
            self.running = False
            escalation_task.cancel()

        print("Approval processor stopped")

    def stop(self):
        """Stop the approval processor"""
        self.running = False
        self.executor.shutdown(wait=True)


def main():
    """Main entry point for the approval processor"""
    import argparse
    import signal

    parser = argparse.ArgumentParser(description="Approval Processing Service")
    parser.add_argument('--config', '-c', help='Path to configuration file')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode with sample data')

    args = parser.parse_args()

    # Initialize approval processor
    processor = ApprovalProcessor(args.config)

    if args.test_mode:
        # Submit a test request
        test_request = {
            'requestor_id': 'user-123',
            'requestor_name': 'John Doe',
            'requestor_email': 'john.doe@company.com',
            'approval_type': 'financial',
            'category': 'payment',
            'amount': 250.00,
            'currency': 'USD',
            'description': 'Office supplies purchase',
            'justification': 'Quarterly office supplies restocking',
            'risk_level': 'low',
            'priority': ApprovalPriority.NORMAL.value
        }

        request_id = processor.submit_request(test_request)
        print(f"Test request submitted with ID: {request_id}")

        # Simulate approval if not auto-approved
        request = processor.store.get_approval_request(request_id)
        if request and request.status == ApprovalStatus.PENDING:
            print(f"Approving test request {request_id}")
            processor.approve_request(
                request_id,
                'approver-456',
                'Jane Smith',
                'jane.smith@company.com',
                'Approved based on policy'
            )

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        processor.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the processor
    try:
        asyncio.run(processor.run_continuous())
    except KeyboardInterrupt:
        print("Shutting down...")


if __name__ == "__main__":
    main()