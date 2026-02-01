#!/usr/bin/env python3
"""
Policy Enforcer Skill

This module implements a comprehensive policy enforcement system for the Personal AI Employee.
It validates actions against predefined organizational policies, governance requirements,
and compliance standards before allowing execution. The system provides real-time policy
checking, violation detection, and compliance reporting capabilities.

Features:
- Pre-action validation against policy rules
- Real-time monitoring of ongoing activities
- Post-action verification for compliance
- Exception handling and override mechanisms
- Audit logging for all policy evaluations
- Integration with external systems for policy data
"""

import json
import sqlite3
import logging
import os
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
import hashlib
import threading
from contextlib import contextmanager


class PolicyCategory(Enum):
    """Categories of policies for classification and organization."""
    GOVERNANCE = "governance"
    FINANCIAL = "financial"
    SECURITY = "security"
    COMPLIANCE = "compliance"


class PolicyPriority(Enum):
    """Priority levels for policy enforcement."""
    CRITICAL = "critical"  # P0: Mandatory policies that block all non-compliant actions
    HIGH = "high"         # P1: Important policies requiring approval before proceeding
    MEDIUM = "medium"     # P2: Standard policies with notification requirements
    LOW = "low"          # P3: Advisory policies with optional compliance tracking
    INFORMATIONAL = "informational"  # Reference policies for awareness only


class PolicyAction(Enum):
    """Possible actions when a policy is evaluated."""
    ALLOW = "allow"      # Action complies with all applicable policies
    BLOCK = "block"      # Action violates critical policies and cannot proceed
    REVIEW = "review"    # Action requires human review before proceeding
    ALERT = "alert"      # Action is compliant but requires notification
    CONDITIONAL = "conditional"  # Action allowed with specific conditions applied


@dataclass
class PolicyCondition:
    """Represents a condition that must be met for a policy to apply."""
    attribute: str
    operator: str  # equals, contains, greater_than, less_than, matches_regex
    value: Union[str, int, float, bool]
    comparator: str = "AND"  # AND or OR when multiple conditions exist


@dataclass
class PolicyActionRule:
    """Defines what action to take when a policy condition is met."""
    type: PolicyAction
    parameters: Dict[str, Any]


@dataclass
class PolicyException:
    """Defines exceptions to policies for specific roles or contexts."""
    role: str
    scope: str  # global, department, project
    duration: str  # time period (e.g., "24_hours", "7_days")


@dataclass
class Policy:
    """Represents a single policy rule."""
    id: str
    name: str
    category: PolicyCategory
    priority: PolicyPriority
    description: str
    conditions: List[PolicyCondition]
    actions: List[PolicyActionRule]
    exceptions: List[PolicyException]
    enabled: bool = True
    created_date: str = ""
    last_updated: str = ""
    version: str = "1.0"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PolicyEvaluation:
    """Represents the result of a policy evaluation."""
    policy_id: str
    policy_name: str
    action_taken: PolicyAction
    matched: bool
    reason: str
    timestamp: str
    execution_time_ms: float
    context: Dict[str, Any]


class PolicyStore:
    """
    Manages storage and retrieval of policies in a SQLite database.
    Provides thread-safe operations for policy management.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database with required tables."""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS policies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    description TEXT,
                    conditions TEXT,
                    actions TEXT,
                    exceptions TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    created_date TEXT,
                    last_updated TEXT,
                    version TEXT,
                    metadata TEXT
                )
            ''')

            # Create indexes for faster queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_category ON policies(category)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_priority ON policies(priority)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_enabled ON policies(enabled)')

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

    def add_policy(self, policy: Policy) -> bool:
        """Add a new policy to the store."""
        with self.lock:
            try:
                with self._get_connection() as conn:
                    conn.execute('''
                        INSERT INTO policies
                        (id, name, category, priority, description, conditions, actions,
                         exceptions, enabled, created_date, last_updated, version, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        policy.id, policy.name, policy.category.value, policy.priority.value,
                        policy.description,
                        json.dumps([asdict(cond) for cond in policy.conditions]),
                        json.dumps([asdict(act) for act in policy.actions]),
                        json.dumps([asdict(exc) for exc in policy.exceptions]),
                        policy.enabled, policy.created_date, policy.last_updated,
                        policy.version, json.dumps(policy.metadata) if policy.metadata else None
                    ))
                return True
            except sqlite3.IntegrityError:
                return False

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Retrieve a policy by ID."""
        with self.lock:
            with self._get_connection() as conn:
                row = conn.execute(
                    'SELECT * FROM policies WHERE id = ?', (policy_id,)
                ).fetchone()

                if row:
                    return Policy(
                        id=row['id'],
                        name=row['name'],
                        category=PolicyCategory(row['category']),
                        priority=PolicyPriority(row['priority']),
                        description=row['description'],
                        conditions=[PolicyCondition(**cond) for cond in json.loads(row['conditions'])],
                        actions=[PolicyActionRule(PolicyAction(act['type']), act['parameters']) for act in json.loads(row['actions'])],
                        exceptions=[PolicyException(**exc) for exc in json.loads(row['exceptions'])],
                        enabled=bool(row['enabled']),
                        created_date=row['created_date'],
                        last_updated=row['last_updated'],
                        version=row['version'],
                        metadata=json.loads(row['metadata']) if row['metadata'] else None
                    )
                return None

    def get_policies_by_category(self, category: PolicyCategory) -> List[Policy]:
        """Retrieve all policies in a specific category."""
        with self.lock:
            with self._get_connection() as conn:
                rows = conn.execute(
                    'SELECT * FROM policies WHERE category = ? AND enabled = 1',
                    (category.value,)
                ).fetchall()

                policies = []
                for row in rows:
                    policies.append(Policy(
                        id=row['id'],
                        name=row['name'],
                        category=PolicyCategory(row['category']),
                        priority=PolicyPriority(row['priority']),
                        description=row['description'],
                        conditions=[PolicyCondition(**cond) for cond in json.loads(row['conditions'])],
                        actions=[PolicyActionRule(PolicyAction(act['type']), act['parameters']) for act in json.loads(row['actions'])],
                        exceptions=[PolicyException(**exc) for exc in json.loads(row['exceptions'])],
                        enabled=bool(row['enabled']),
                        created_date=row['created_date'],
                        last_updated=row['last_updated'],
                        version=row['version'],
                        metadata=json.loads(row['metadata']) if row['metadata'] else None
                    ))
                return policies

    def get_policies_by_priority(self, priority: PolicyPriority) -> List[Policy]:
        """Retrieve all policies with a specific priority."""
        with self.lock:
            with self._get_connection() as conn:
                rows = conn.execute(
                    'SELECT * FROM policies WHERE priority = ? AND enabled = 1 ORDER BY category',
                    (priority.value,)
                ).fetchall()

                policies = []
                for row in rows:
                    policies.append(Policy(
                        id=row['id'],
                        name=row['name'],
                        category=PolicyCategory(row['category']),
                        priority=PolicyPriority(row['priority']),
                        description=row['description'],
                        conditions=[PolicyCondition(**cond) for cond in json.loads(row['conditions'])],
                        actions=[PolicyActionRule(PolicyAction(act['type']), act['parameters']) for act in json.loads(row['actions'])],
                        exceptions=[PolicyException(**exc) for exc in json.loads(row['exceptions'])],
                        enabled=bool(row['enabled']),
                        created_date=row['created_date'],
                        last_updated=row['last_updated'],
                        version=row['version'],
                        metadata=json.loads(row['metadata']) if row['metadata'] else None
                    ))
                return policies

    def update_policy(self, policy: Policy) -> bool:
        """Update an existing policy."""
        with self.lock:
            try:
                with self._get_connection() as conn:
                    conn.execute('''
                        UPDATE policies SET
                            name = ?, category = ?, priority = ?, description = ?,
                            conditions = ?, actions = ?, exceptions = ?, enabled = ?,
                            last_updated = ?, version = ?, metadata = ?
                        WHERE id = ?
                    ''', (
                        policy.name, policy.category.value, policy.priority.value,
                        policy.description,
                        json.dumps([asdict(cond) for cond in policy.conditions]),
                        json.dumps([asdict(act) for act in policy.actions]),
                        json.dumps([asdict(exc) for exc in policy.exceptions]),
                        policy.enabled, datetime.now().isoformat(),
                        policy.version, json.dumps(policy.metadata) if policy.metadata else None,
                        policy.id
                    ))
                return True
            except Exception:
                return False

    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy from the store."""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.execute('DELETE FROM policies WHERE id = ?', (policy_id,))
                return cursor.rowcount > 0

    def get_all_policies(self) -> List[Policy]:
        """Retrieve all policies."""
        with self.lock:
            with self._get_connection() as conn:
                rows = conn.execute('SELECT * FROM policies WHERE enabled = 1').fetchall()

                policies = []
                for row in rows:
                    policies.append(Policy(
                        id=row['id'],
                        name=row['name'],
                        category=PolicyCategory(row['category']),
                        priority=PolicyPriority(row['priority']),
                        description=row['description'],
                        conditions=[PolicyCondition(**cond) for cond in json.loads(row['conditions'])],
                        actions=[PolicyActionRule(PolicyAction(act['type']), act['parameters']) for act in json.loads(row['actions'])],
                        exceptions=[PolicyException(**exc) for exc in json.loads(row['exceptions'])],
                        enabled=bool(row['enabled']),
                        created_date=row['created_date'],
                        last_updated=row['last_updated'],
                        version=row['version'],
                        metadata=json.loads(row['metadata']) if row['metadata'] else None
                    ))
                return policies


class ConditionEvaluator:
    """
    Evaluates policy conditions against action contexts.
    Supports various operators for flexible policy matching.
    """

    def evaluate_condition(self, condition: PolicyCondition, context: Dict[str, Any]) -> bool:
        """Evaluate a single condition against the provided context."""
        # Navigate the context using dot notation (e.g., "user.department")
        value_parts = condition.attribute.split('.')
        context_value = context

        for part in value_parts:
            if isinstance(context_value, dict) and part in context_value:
                context_value = context_value[part]
            elif isinstance(context_value, list) and part.isdigit():
                index = int(part)
                if 0 <= index < len(context_value):
                    context_value = context_value[index]
                else:
                    return False  # Path doesn't exist
            else:
                return False  # Path doesn't exist

        # Apply the operator
        if condition.operator == "equals":
            return str(context_value).lower() == str(condition.value).lower()
        elif condition.operator == "contains":
            return str(condition.value).lower() in str(context_value).lower()
        elif condition.operator == "greater_than":
            try:
                return float(context_value) > float(condition.value)
            except (ValueError, TypeError):
                return False
        elif condition.operator == "less_than":
            try:
                return float(context_value) < float(condition.value)
            except (ValueError, TypeError):
                return False
        elif condition.operator == "matches_regex":
            try:
                return bool(re.search(str(condition.value), str(context_value)))
            except re.error:
                return False
        else:
            # Unsupported operator
            return False

    def evaluate_conditions(self, conditions: List[PolicyCondition], context: Dict[str, Any]) -> bool:
        """Evaluate multiple conditions against the provided context."""
        if not conditions:
            return True  # No conditions means always match

        # Start with the result of the first condition
        result = self.evaluate_condition(conditions[0], context)

        # Apply subsequent conditions with their comparators
        for i in range(1, len(conditions)):
            condition_result = self.evaluate_condition(conditions[i], context)
            if conditions[i-1].comparator.upper() == "OR":
                result = result or condition_result
            else:  # Default to AND
                result = result and condition_result

        return result


class PolicyEnforcer:
    """
    Main policy enforcement class that validates actions against policies.
    Implements pre-action validation, real-time monitoring, and post-action verification.
    """

    def __init__(self, config_path: str = None, db_path: str = ":memory:"):
        self.config_path = config_path
        self.policy_store = PolicyStore(db_path)
        self.condition_evaluator = ConditionEvaluator()
        self.logger = self._setup_logger()

        # Load configuration if provided
        self.config = self._load_config()

        # Cache for performance
        self.policy_cache = {}
        self.cache_last_update = datetime.now()

        # Initialize with default policies if none exist
        self._initialize_default_policies()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the policy enforcer."""
        logger = logging.getLogger('PolicyEnforcer')
        logger.setLevel(logging.INFO)

        # Create handler that writes to file
        log_path = os.getenv('POLICY_ENFORCER_AUDIT_LOG_PATH', '/tmp/policy_audit.log')
        handler = logging.FileHandler(log_path)
        handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        # Add handler to logger
        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment."""
        config = {
            'pre_action_validation': {
                'policy_lookup_timeout_seconds': 30,
                'fail_open_behavior': False,
                'cache_policy_results': True,
                'cache_duration_minutes': 5,
                'parallel_validation_enabled': True
            },
            'real_time_monitoring': {
                'monitoring_interval_seconds': 10,
                'violation_alert_recipients': ['admin@example.com'],
                'violation_severity_thresholds': {
                    'critical': ['block_immediately'],
                    'high': ['alert_immediately', 'review_within_1_hour'],
                    'medium': ['log_violation', 'review_daily'],
                    'low': ['log_violation', 'review_weekly']
                }
            },
            'post_action_verification': {
                'verification_delay_minutes': 5,
                'verification_retries': 3,
                'non_compliance_notification_recipients': ['admin@example.com'],
                'automatic_correction_enabled': False
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

    def _initialize_default_policies(self):
        """Initialize default policies if none exist."""
        if not self.policy_store.get_all_policies():
            # Add some basic default policies
            self._add_default_financial_policies()
            self._add_default_security_policies()
            self._add_default_governance_policies()

    def _add_default_financial_policies(self):
        """Add default financial policies."""
        # Individual daily spending limit
        spending_policy = Policy(
            id="default-spending-limit-001",
            name="Default Individual Daily Spending Limit",
            category=PolicyCategory.FINANCIAL,
            priority=PolicyPriority.HIGH,
            description="Default limit on individual daily spending",
            conditions=[
                PolicyCondition("action.type", "equals", "expense_submission"),
                PolicyCondition("action.amount", "greater_than", 500)
            ],
            actions=[
                PolicyActionRule(PolicyAction.REVIEW, {"reason": "Amount exceeds daily limit"})
            ],
            exceptions=[],
            enabled=True,
            created_date=datetime.now().isoformat()
        )
        self.policy_store.add_policy(spending_policy)

        # Payment authorization requirement
        payment_policy = Policy(
            id="default-payment-auth-001",
            name="Default Payment Authorization Requirement",
            category=PolicyCategory.FINANCIAL,
            priority=PolicyPriority.CRITICAL,
            description="Require approval for payments above threshold",
            conditions=[
                PolicyCondition("action.type", "equals", "payment_initiation"),
                PolicyCondition("action.amount", "greater_than", 1000)
            ],
            actions=[
                PolicyActionRule(PolicyAction.BLOCK, {"reason": "Payment requires approval"})
            ],
            exceptions=[],
            enabled=True,
            created_date=datetime.now().isoformat()
        )
        self.policy_store.add_policy(payment_policy)

    def _add_default_security_policies(self):
        """Add default security policies."""
        # Sensitive data sharing restriction
        data_policy = Policy(
            id="default-data-protection-001",
            name="Default Sensitive Data Sharing Restriction",
            category=PolicyCategory.SECURITY,
            priority=PolicyPriority.CRITICAL,
            description="Restrict sharing of sensitive data externally",
            conditions=[
                PolicyCondition("action.type", "equals", "file_share"),
                PolicyCondition("action.destination", "equals", "external"),
                PolicyCondition("action.file.contains_sensitive_data", "equals", "true")
            ],
            actions=[
                PolicyActionRule(PolicyAction.BLOCK, {"reason": "Contains sensitive data"})
            ],
            exceptions=[],
            enabled=True,
            created_date=datetime.now().isoformat()
        )
        self.policy_store.add_policy(data_policy)

    def _add_default_governance_policies(self):
        """Add default governance policies."""
        # Authorization requirement
        auth_policy = Policy(
            id="default-authorization-001",
            name="Default Authorization Requirement",
            category=PolicyCategory.GOVERNANCE,
            priority=PolicyPriority.HIGH,
            description="Require proper authorization for sensitive actions",
            conditions=[
                PolicyCondition("action.type", "equals", "sensitive_operation"),
                PolicyCondition("user.permissions", "contains", "admin")
            ],
            actions=[
                PolicyActionRule(PolicyAction.ALLOW, {}),
                PolicyActionRule(PolicyAction.ALERT, {"message": "Sensitive operation performed"})
            ],
            exceptions=[],
            enabled=True,
            created_date=datetime.now().isoformat()
        )
        self.policy_store.add_policy(auth_policy)

    def evaluate_action(self, action_context: Dict[str, Any], category_filter: str = "all") -> List[PolicyEvaluation]:
        """
        Evaluate an action against all applicable policies.

        Args:
            action_context: Dictionary containing details about the action to evaluate
            category_filter: Category to filter policies (default: all categories)

        Returns:
            List of PolicyEvaluation objects with results
        """
        start_time = datetime.now()

        # Get applicable policies
        if category_filter.lower() != "all":
            try:
                category = PolicyCategory(category_filter.lower())
                policies = self.policy_store.get_policies_by_category(category)
            except ValueError:
                self.logger.warning(f"Invalid policy category: {category_filter}")
                policies = self.policy_store.get_all_policies()
        else:
            policies = self.policy_store.get_all_policies()

        evaluations = []

        for policy in policies:
            # Check for exceptions first
            exception_found = False
            for exception in policy.exceptions:
                # In a real implementation, this would check if the current user/role matches the exception
                # For simplicity, we'll just log that an exception exists
                if exception.scope == "global":
                    self.logger.info(f"Found global exception for policy {policy.id}")

            if exception_found:
                continue

            # Evaluate policy conditions
            match_result = self.condition_evaluator.evaluate_conditions(policy.conditions, action_context)

            if match_result:
                # Apply policy actions
                for action_rule in policy.actions:
                    eval_result = PolicyEvaluation(
                        policy_id=policy.id,
                        policy_name=policy.name,
                        action_taken=action_rule.type,
                        matched=True,
                        reason=f"Action matched policy conditions: {policy.description}",
                        timestamp=datetime.now().isoformat(),
                        execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                        context=action_context
                    )

                    evaluations.append(eval_result)

                    # Log the evaluation
                    self.logger.info(f"Policy {policy.id} evaluated: {action_rule.type.value} - {policy.description}")

                    # For critical policies, we may want to stop processing
                    if policy.priority == PolicyPriority.CRITICAL and action_rule.type == PolicyAction.BLOCK:
                        break
            else:
                # Log non-matching policies if in debug mode
                self.logger.debug(f"Policy {policy.id} did not match action context")

        # Calculate total execution time
        total_execution_time = (datetime.now() - start_time).total_seconds() * 1000

        # Add execution time to each evaluation
        for eval_item in evaluations:
            eval_item.execution_time_ms = total_execution_time / len(evaluations) if evaluations else 0

        return evaluations

    def is_action_allowed(self, action_context: Dict[str, Any], category_filter: str = "all") -> tuple[bool, List[PolicyEvaluation]]:
        """
        Check if an action is allowed based on policy evaluation.

        Args:
            action_context: Dictionary containing details about the action to evaluate
            category_filter: Category to filter policies (default: all categories)

        Returns:
            Tuple of (is_allowed: bool, evaluations: List[PolicyEvaluation])
        """
        evaluations = self.evaluate_action(action_context, category_filter)

        # Determine if action is allowed
        is_allowed = True
        for evaluation in evaluations:
            if evaluation.action_taken == PolicyAction.BLOCK:
                is_allowed = False
                break
            elif evaluation.action_taken == PolicyAction.REVIEW:
                # For review actions, we typically still allow but with additional steps
                # This could be configured differently based on policy priority
                pass

        return is_allowed, evaluations

    def add_policy(self, policy: Policy) -> bool:
        """Add a new policy to the enforcer."""
        return self.policy_store.add_policy(policy)

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Retrieve a policy by ID."""
        return self.policy_store.get_policy(policy_id)

    def update_policy(self, policy: Policy) -> bool:
        """Update an existing policy."""
        return self.policy_store.update_policy(policy)

    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy."""
        return self.policy_store.delete_policy(policy_id)

    def get_policies_by_category(self, category: PolicyCategory) -> List[Policy]:
        """Get policies by category."""
        return self.policy_store.get_policies_by_category(category)

    def get_policies_by_priority(self, priority: PolicyPriority) -> List[Policy]:
        """Get policies by priority."""
        return self.policy_store.get_policies_by_priority(priority)

    def get_all_policies(self) -> List[Policy]:
        """Get all policies."""
        return self.policy_store.get_all_policies()

    def check_exceptions(self, user_role: str, policy_id: str) -> bool:
        """
        Check if a user has an exception for a specific policy.

        Args:
            user_role: Role of the user requesting the action
            policy_id: ID of the policy to check

        Returns:
            Boolean indicating if an exception exists
        """
        policy = self.policy_store.get_policy(policy_id)
        if not policy:
            return False

        for exception in policy.exceptions:
            if exception.role == user_role:
                return True

        return False

    def log_policy_violation(self, policy_id: str, action_context: Dict[str, Any], violation_details: str):
        """Log a policy violation for audit purposes."""
        self.logger.warning(f"POLICY VIOLATION - Policy ID: {policy_id}, Context: {action_context}, Details: {violation_details}")

    def generate_compliance_report(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        Generate a compliance report showing policy adherence.

        Args:
            start_date: Start date for the report (ISO format)
            end_date: End date for the report (ISO format)

        Returns:
            Dictionary containing compliance report data
        """
        all_policies = self.policy_store.get_all_policies()

        report = {
            "generated_at": datetime.now().isoformat(),
            "period_start": start_date or (datetime.now() - timedelta(days=30)).isoformat(),
            "period_end": end_date or datetime.now().isoformat(),
            "total_policies": len(all_policies),
            "policies_by_category": {},
            "policies_by_priority": {},
            "compliance_summary": {
                "fully_compliant": 0,
                "partially_compliant": 0,
                "non_compliant": 0
            }
        }

        # Count policies by category
        for policy in all_policies:
            category = policy.category.value
            if category not in report["policies_by_category"]:
                report["policies_by_category"][category] = 0
            report["policies_by_category"][category] += 1

            priority = policy.priority.value
            if priority not in report["policies_by_priority"]:
                report["policies_by_priority"][priority] = 0
            report["policies_by_priority"][priority] += 1

        # This would normally aggregate data from logs about actual compliance
        # For now, we'll provide a basic structure
        report["recent_violations"] = []  # Would come from audit logs

        return report


def main():
    """Main function for testing and demonstration."""
    print("Policy Enforcer Skill")
    print("=====================")

    # Initialize the policy enforcer
    enforcer = PolicyEnforcer()

    # Example action context to evaluate
    test_action = {
        "action": {
            "type": "expense_submission",
            "amount": 750,
            "description": "Business dinner with client",
            "category": "meals"
        },
        "user": {
            "id": "user123",
            "name": "John Doe",
            "role": "employee",
            "department": "sales"
        },
        "organization": {
            "department_budget": 10000,
            "remaining_budget": 8000
        }
    }

    print("\nTesting action evaluation:")
    print(f"Action: {test_action['action']['type']} - ${test_action['action']['amount']}")

    # Evaluate the action
    is_allowed, evaluations = enforcer.is_action_allowed(test_action)

    print(f"\nAction allowed: {is_allowed}")
    print(f"Number of policy evaluations: {len(evaluations)}")

    for eval_item in evaluations:
        print(f"- Policy: {eval_item.policy_name}")
        print(f"  Action taken: {eval_item.action_taken.value}")
        print(f"  Matched: {eval_item.matched}")
        print(f"  Reason: {eval_item.reason}")
        print()

    # Add a new custom policy
    custom_policy = Policy(
        id="custom-expense-policy-001",
        name="Custom Expense Policy",
        category=PolicyCategory.FINANCIAL,
        priority=PolicyPriority.MEDIUM,
        description="Special policy for sales team expenses",
        conditions=[
            PolicyCondition("user.department", "equals", "sales"),
            PolicyCondition("action.amount", "greater_than", 1000)
        ],
        actions=[
            PolicyActionRule(PolicyAction.REVIEW, {"reason": "High-value sales expense requires review"})
        ],
        exceptions=[],
        enabled=True,
        created_date=datetime.now().isoformat()
    )

    print("Adding custom policy...")
    success = enforcer.add_policy(custom_policy)
    print(f"Policy added successfully: {success}")

    # Test the new policy
    test_sales_action = {
        "action": {
            "type": "expense_submission",
            "amount": 1500,
            "description": "Sales conference registration",
            "category": "training"
        },
        "user": {
            "id": "user456",
            "name": "Jane Smith",
            "role": "employee",
            "department": "sales"
        }
    }

    print("\nTesting with custom policy:")
    print(f"Action: {test_sales_action['action']['type']} - ${test_sales_action['action']['amount']} by sales team")

    is_allowed, evaluations = enforcer.is_action_allowed(test_sales_action)
    print(f"Action allowed: {is_allowed}")

    for eval_item in evaluations:
        print(f"- Policy: {eval_item.policy_name}")
        print(f"  Action taken: {eval_item.action_taken.value}")
        print(f"  Matched: {eval_item.matched}")
        print()


if __name__ == "__main__":
    main()