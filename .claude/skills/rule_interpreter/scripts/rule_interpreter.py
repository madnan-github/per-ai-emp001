#!/usr/bin/env python3
"""
Rule Interpreter - Evaluates business rules and company policies

This script implements a rule interpreter that evaluates business rules, company policies,
and operational guidelines to determine appropriate actions or responses based on input
situations and contexts.
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
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import operator


class RuleActionType(Enum):
    """Types of actions that rules can perform"""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    ESCALATE = "escalate"
    REDIRECT = "redirect"
    NOTIFY = "notify"
    LOG = "log"
    ALERT = "alert"
    MODIFY_FIELD = "modify_field"
    ADD_TAG = "add_tag"
    SET_PRIORITY = "set_priority"
    ASSIGN_OWNER = "assign_owner"


@dataclass
class RuleCondition:
    """Represents a condition in a rule"""
    field: str
    operator: str
    value: Any
    comparator: str = "AND"  # AND/OR with next condition


@dataclass
class RuleAction:
    """Represents an action in a rule"""
    type: RuleActionType
    parameters: Dict[str, Any]


@dataclass
class BusinessRule:
    """Represents a business rule"""
    id: str
    name: str
    description: str
    category: str
    priority: int
    enabled: bool
    conditions: List[RuleCondition]
    actions: List[RuleAction]
    metadata: Optional[Dict] = None


@dataclass
class RuleEvaluationResult:
    """Result of a rule evaluation"""
    rule_id: str
    matched: bool
    actions: List[RuleAction]
    execution_time: float
    details: Dict[str, Any]


class RuleStore:
    """Manages storage and retrieval of business rules"""

    def __init__(self, db_path: str = "rules.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create rules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rules (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                category TEXT,
                priority INTEGER,
                enabled BOOLEAN,
                conditions TEXT,
                actions TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON rules(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_priority ON rules(priority)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_enabled ON rules(enabled)')

        conn.commit()
        conn.close()

    def save_rule(self, rule: BusinessRule):
        """Save a rule to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO rules
            (id, name, description, category, priority, enabled, conditions, actions, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            rule.id,
            rule.name,
            rule.description,
            rule.category,
            rule.priority,
            rule.enabled,
            json.dumps([asdict(cond) for cond in rule.conditions]),
            json.dumps([asdict(action) for action in rule.actions]),
            json.dumps(rule.metadata or {})
        ))

        conn.commit()
        conn.close()

    def get_rules_by_category(self, category: str) -> List[BusinessRule]:
        """Get all enabled rules for a specific category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, description, category, priority, enabled, conditions, actions, metadata
            FROM rules
            WHERE category = ? AND enabled = 1
            ORDER BY priority DESC
        ''', (category,))

        rows = cursor.fetchall()
        conn.close()

        rules = []
        for row in rows:
            conditions = [RuleCondition(**cond) for cond in json.loads(row[6])]
            actions = [RuleAction(RuleActionType(act['type']), act.get('parameters', {})) for act in json.loads(row[7])]

            rule = BusinessRule(
                id=row[0],
                name=row[1],
                description=row[2],
                category=row[3],
                priority=row[4],
                enabled=row[5],
                conditions=conditions,
                actions=actions,
                metadata=json.loads(row[8]) if row[8] else {}
            )
            rules.append(rule)

        return rules

    def get_all_rules(self) -> List[BusinessRule]:
        """Get all rules from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, description, category, priority, enabled, conditions, actions, metadata
            FROM rules
            ORDER BY priority DESC
        ''')

        rows = cursor.fetchall()
        conn.close()

        rules = []
        for row in rows:
            conditions = [RuleCondition(**cond) for cond in json.loads(row[6])]
            actions = [RuleAction(RuleActionType(act['type']), act.get('parameters', {})) for act in json.loads(row[7])]

            rule = BusinessRule(
                id=row[0],
                name=row[1],
                description=row[2],
                category=row[3],
                priority=row[4],
                enabled=row[5],
                conditions=conditions,
                actions=actions,
                metadata=json.loads(row[8]) if row[8] else {}
            )
            rules.append(rule)

        return rules


class ConditionEvaluator:
    """Evaluates rule conditions against input data"""

    def __init__(self, config: Dict):
        self.config = config
        self.operators = self._load_operators()

    def _load_operators(self) -> Dict[str, Callable]:
        """Load condition operators"""
        return {
            # Comparison operators
            '=': operator.eq,
            '!=': operator.ne,
            '>': operator.gt,
            '<': operator.lt,
            '>=': operator.ge,
            '<=': operator.le,
            # String operators
            'contains': lambda x, y: isinstance(x, str) and y in x,
            'starts_with': lambda x, y: isinstance(x, str) and x.startswith(y),
            'ends_with': lambda x, y: isinstance(x, str) and x.endswith(y),
            'matches_regex': lambda x, y: isinstance(x, str) and re.search(y, x) is not None,
            # Collection operators
            'in': lambda x, y: x in y if isinstance(y, (list, tuple)) else False,
            'not_in': lambda x, y: x not in y if isinstance(y, (list, tuple)) else False,
            'has_any': lambda x, y: isinstance(x, list) and any(item in x for item in y),
            'has_all': lambda x, y: isinstance(x, list) and all(item in x for item in y)
        }

    def evaluate_condition(self, condition: RuleCondition, context: Dict[str, Any]) -> bool:
        """Evaluate a single condition against the context"""
        # Extract the value from context based on the field path
        field_value = self._get_nested_value(context, condition.field)

        if field_value is None:
            return False  # If field doesn't exist, condition fails

        # Get the operator function
        op_func = self.operators.get(condition.operator)
        if not op_func:
            logging.warning(f"Unknown operator: {condition.operator}")
            return False

        try:
            # Apply the operator
            result = op_func(field_value, condition.value)
            return result
        except Exception as e:
            logging.error(f"Error evaluating condition {condition.field} {condition.operator} {condition.value}: {e}")
            return False

    def evaluate_conditions(self, conditions: List[RuleCondition], context: Dict[str, Any]) -> bool:
        """Evaluate multiple conditions with logical operators"""
        if not conditions:
            return True  # Empty conditions should pass

        result = self.evaluate_condition(conditions[0], context)

        for i in range(1, len(conditions)):
            next_result = self.evaluate_condition(conditions[i], context)

            # Apply logical operator (from previous condition's comparator)
            if conditions[i-1].comparator.upper() == 'AND':
                result = result and next_result
            elif conditions[i-1].comparator.upper() == 'OR':
                result = result or next_result
            else:
                # Default to AND if not specified
                result = result and next_result

        return result

    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """Get nested value using dot notation"""
        parts = path.split('.')
        current = obj

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None  # Path doesn't exist

        return current


class ActionExecutor:
    """Executes actions specified by rules"""

    def __init__(self, config: Dict):
        self.config = config

    def execute_action(self, action: RuleAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single action"""
        try:
            if action.type == RuleActionType.ALLOW:
                return self._execute_allow(action.parameters, context)
            elif action.type == RuleActionType.DENY:
                return self._execute_deny(action.parameters, context)
            elif action.type == RuleActionType.REQUIRE_APPROVAL:
                return self._execute_require_approval(action.parameters, context)
            elif action.type == RuleActionType.ESCALATE:
                return self._execute_escalate(action.parameters, context)
            elif action.type == RuleActionType.REDIRECT:
                return self._execute_redirect(action.parameters, context)
            elif action.type == RuleActionType.NOTIFY:
                return self._execute_notify(action.parameters, context)
            elif action.type == RuleActionType.LOG:
                return self._execute_log(action.parameters, context)
            elif action.type == RuleActionType.ALERT:
                return self._execute_alert(action.parameters, context)
            elif action.type == RuleActionType.MODIFY_FIELD:
                return self._execute_modify_field(action.parameters, context)
            elif action.type == RuleActionType.ADD_TAG:
                return self._execute_add_tag(action.parameters, context)
            elif action.type == RuleActionType.SET_PRIORITY:
                return self._execute_set_priority(action.parameters, context)
            elif action.type == RuleActionType.ASSIGN_OWNER:
                return self._execute_assign_owner(action.parameters, context)
            else:
                logging.warning(f"Unknown action type: {action.type}")
                return {"success": False, "message": f"Unknown action type: {action.type}"}
        except Exception as e:
            logging.error(f"Error executing action {action.type}: {e}")
            return {"success": False, "message": str(e)}

    def execute_actions(self, actions: List[RuleAction], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute multiple actions"""
        results = []
        for action in actions:
            result = self.execute_action(action, context)
            results.append(result)
        return results

    def _execute_allow(self, parameters: Dict, context: Dict) -> Dict:
        """Execute allow action"""
        return {"success": True, "action": "allow", "context_modified": False}

    def _execute_deny(self, parameters: Dict, context: Dict) -> Dict:
        """Execute deny action"""
        reason = parameters.get('reason', 'Rule violation')
        return {"success": True, "action": "deny", "reason": reason, "context_modified": False}

    def _execute_require_approval(self, parameters: Dict, context: Dict) -> Dict:
        """Execute require approval action"""
        level = parameters.get('level', 'manager')
        deadline = parameters.get('deadline', 'PT24H')
        return {
            "success": True,
            "action": "require_approval",
            "level": level,
            "deadline": deadline,
            "context_modified": True
        }

    def _execute_escalate(self, parameters: Dict, context: Dict) -> Dict:
        """Execute escalate action"""
        target = parameters.get('to', 'management')
        reason = parameters.get('reason', 'Rule requirement')
        return {
            "success": True,
            "action": "escalate",
            "to": target,
            "reason": reason,
            "context_modified": True
        }

    def _execute_redirect(self, parameters: Dict, context: Dict) -> Dict:
        """Execute redirect action"""
        process = parameters.get('process', 'default')
        reason = parameters.get('reason', 'Rule requirement')
        return {
            "success": True,
            "action": "redirect",
            "process": process,
            "reason": reason,
            "context_modified": True
        }

    def _execute_notify(self, parameters: Dict, context: Dict) -> Dict:
        """Execute notify action"""
        recipients = parameters.get('recipients', [])
        message = parameters.get('message', 'Notification from rule evaluation')
        return {
            "success": True,
            "action": "notify",
            "recipients": recipients,
            "message": message,
            "context_modified": False
        }

    def _execute_log(self, parameters: Dict, context: Dict) -> Dict:
        """Execute log action"""
        level = parameters.get('level', 'info')
        message = parameters.get('message', 'Rule evaluation event')
        category = parameters.get('category', 'rule_evaluation')

        # Log the message (in a real system, this would go to proper logging)
        log_msg = f"[{level.upper()}] {category}: {message}"
        print(log_msg)  # For demo purposes

        return {
            "success": True,
            "action": "log",
            "level": level,
            "message": message,
            "context_modified": False
        }

    def _execute_alert(self, parameters: Dict, context: Dict) -> Dict:
        """Execute alert action"""
        severity = parameters.get('severity', 'medium')
        message = parameters.get('message', 'Rule evaluation alert')
        target = parameters.get('target_system', 'default_monitoring')

        # In a real system, this would send to monitoring system
        print(f"ALERT [{severity.upper()}]: {message}")  # For demo purposes

        return {
            "success": True,
            "action": "alert",
            "severity": severity,
            "message": message,
            "context_modified": False
        }

    def _execute_modify_field(self, parameters: Dict, context: Dict) -> Dict:
        """Execute modify field action"""
        field = parameters.get('field', '')
        value = parameters.get('value')
        operation = parameters.get('operation', 'set')

        # This is a simplified implementation - in a real system you'd modify the actual context
        # For this example, we'll just return what we'd do
        return {
            "success": True,
            "action": "modify_field",
            "field": field,
            "value": value,
            "operation": operation,
            "context_modified": True
        }

    def _execute_add_tag(self, parameters: Dict, context: Dict) -> Dict:
        """Execute add tag action"""
        tag = parameters.get('tag', '')
        category = parameters.get('category', 'classification')

        return {
            "success": True,
            "action": "add_tag",
            "tag": tag,
            "category": category,
            "context_modified": True
        }

    def _execute_set_priority(self, parameters: Dict, context: Dict) -> Dict:
        """Execute set priority action"""
        level = parameters.get('level', 'normal')

        return {
            "success": True,
            "action": "set_priority",
            "level": level,
            "context_modified": True
        }

    def _execute_assign_owner(self, parameters: Dict, context: Dict) -> Dict:
        """Execute assign owner action"""
        owner = parameters.get('owner', '')
        reason = parameters.get('reason', 'Rule assignment')

        return {
            "success": True,
            "action": "assign_owner",
            "owner": owner,
            "reason": reason,
            "context_modified": True
        }


class RuleInterpreter:
    """Main rule interpreter class"""

    def __init__(self, config_path: str = None):
        self.config = self.load_config(config_path)
        self.store = RuleStore()
        self.condition_evaluator = ConditionEvaluator(self.config)
        self.action_executor = ActionExecutor(self.config)
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=10)

        # Load default rules if store is empty
        self._ensure_default_rules()

    def load_config(self, config_path: str = None) -> Dict:
        """Load configuration from file"""
        default_config = {
            'processing': {
                'max_workers': 16,
                'timeout': 30000,  # milliseconds
                'max_concurrent_evaluations': 100
            },
            'evaluation_strategies': {
                'default_strategy': 'first_match'
            },
            'context_variables': {
                'request': {'enabled': True},
                'user': {'enabled': True},
                'organization': {'enabled': True},
                'temporal': {'enabled': True}
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

    def _ensure_default_rules(self):
        """Ensure default rules are in the store"""
        # Check if we have any rules
        rules = self.store.get_all_rules()
        if not rules:
            # Add some default rules for demonstration
            self._add_default_rules()

    def _add_default_rules(self):
        """Add default business rules"""
        # Rule 1: High-value requests require approval
        high_value_rule = BusinessRule(
            id="high_value_approval",
            name="High Value Approval Rule",
            description="Requests with high monetary value require approval",
            category="financial_controls",
            priority=90,
            enabled=True,
            conditions=[
                RuleCondition("request.amount", ">", 5000, "AND"),
                RuleCondition("request.category", "!=", "expense", "AND")
            ],
            actions=[
                RuleAction(RuleActionType.REQUIRE_APPROVAL, {"level": "director", "deadline": "PT24H"})
            ]
        )

        # Rule 2: Weekend requests get flagged
        weekend_rule = BusinessRule(
            id="weekend_flag",
            name="Weekend Request Flag",
            description="Flag requests made on weekends",
            category="operational_procedures",
            priority=70,
            enabled=True,
            conditions=[
                RuleCondition("temporal.business_hours", "==", False)
            ],
            actions=[
                RuleAction(RuleActionType.ADD_TAG, {"tag": "weekend_request", "category": "timing"}),
                RuleAction(RuleActionType.NOTIFY, {"recipients": ["supervisor"], "message": "Weekend request detected"})
            ]
        )

        # Rule 3: HR requests need special handling
        hr_rule = BusinessRule(
            id="hr_request",
            name="HR Request Handler",
            description="Special handling for HR-related requests",
            category="human_resources",
            priority=80,
            enabled=True,
            conditions=[
                RuleCondition("request.category", "contains", "hr")
            ],
            actions=[
                RuleAction(RuleActionType.REDIRECT, {"process": "hr_approval", "reason": "HR category request"}),
                RuleAction(RuleActionType.SET_PRIORITY, {"level": "high"})
            ]
        )

        # Save the default rules
        self.store.save_rule(high_value_rule)
        self.store.save_rule(weekend_rule)
        self.store.save_rule(hr_rule)

    def evaluate_rules(self, context: Dict[str, Any], category: str = "all") -> List[RuleEvaluationResult]:
        """Evaluate rules against the given context"""
        start_time = time.time()

        # Get rules for the specified category or all rules
        if category == "all":
            rules = self.store.get_all_rules()
        else:
            rules = self.store.get_rules_by_category(category)

        results = []

        for rule in rules:
            try:
                # Evaluate conditions
                condition_matched = self.condition_evaluator.evaluate_conditions(rule.conditions, context)

                if condition_matched:
                    # Execute actions
                    action_results = self.action_executor.execute_actions(rule.actions, context)

                    # Create evaluation result
                    result = RuleEvaluationResult(
                        rule_id=rule.id,
                        matched=True,
                        actions=rule.actions,
                        execution_time=time.time() - start_time,
                        details={
                            "rule_name": rule.name,
                            "action_results": action_results
                        }
                    )
                    results.append(result)

                    # For first_match strategy, stop after first match
                    strategy = self.config['evaluation_strategies']['default_strategy']
                    if strategy == 'first_match':
                        break
            except Exception as e:
                logging.error(f"Error evaluating rule {rule.id}: {e}")
                # Continue with other rules
                continue

        total_time = time.time() - start_time
        print(f"Rule evaluation completed in {total_time:.3f}s with {len(results)} matches")

        return results

    def add_rule(self, rule: BusinessRule):
        """Add a new rule to the system"""
        self.store.save_rule(rule)
        print(f"Added rule: {rule.name}")

    def update_rule(self, rule: BusinessRule):
        """Update an existing rule"""
        self.store.save_rule(rule)
        print(f"Updated rule: {rule.name}")

    def remove_rule(self, rule_id: str):
        """Remove a rule by ID"""
        # In a real implementation, you'd have a delete method
        # For this example, we'll just disable the rule
        all_rules = self.store.get_all_rules()
        for rule in all_rules:
            if rule.id == rule_id:
                rule.enabled = False
                self.store.save_rule(rule)
                print(f"Disabled rule: {rule.name}")
                return
        print(f"Rule not found: {rule_id}")

    async def run_continuous(self):
        """Run the rule interpreter continuously"""
        self.running = True
        print("Starting rule interpreter...")

        while self.running:
            # Perform any periodic maintenance tasks
            await asyncio.sleep(60)  # Check every minute

        print("Rule interpreter stopped")

    def stop(self):
        """Stop the rule interpreter"""
        self.running = False
        self.executor.shutdown(wait=True)


def main():
    """Main entry point for the rule interpreter"""
    import argparse
    import signal

    parser = argparse.ArgumentParser(description="Rule Interpretation Service")
    parser.add_argument('--config', '-c', help='Path to configuration file')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode with sample data')

    args = parser.parse_args()

    # Initialize rule interpreter
    interpreter = RuleInterpreter(args.config)

    if args.test_mode:
        # Create a sample context to test with
        sample_context = {
            "request": {
                "amount": 7500,
                "category": "software_purchase",
                "description": "New software license",
                "requestor_id": "user123"
            },
            "user": {
                "id": "user123",
                "name": "John Doe",
                "department": "Engineering",
                "role": "developer"
            },
            "organization": {
                "department_budget": 100000,
                "remaining_budget": 85000
            },
            "temporal": {
                "current_date": str(datetime.now()),
                "business_hours": True
            }
        }

        print("Testing rule evaluation with sample context...")
        results = interpreter.evaluate_rules(sample_context, "financial_controls")

        print(f"Found {len(results)} matching rules:")
        for result in results:
            print(f"  - {result.rule_id}: {len(result.actions)} actions executed")

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        interpreter.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the interpreter
    try:
        asyncio.run(interpreter.run_continuous())
    except KeyboardInterrupt:
        print("Shutting down...")


if __name__ == "__main__":
    main()