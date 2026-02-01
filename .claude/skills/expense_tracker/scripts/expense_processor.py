#!/usr/bin/env python3
"""
Expense Processor Module for Expense Tracker Skill
"""

import sqlite3
import json
import os
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import asyncio
import aiofiles
from PIL import Image
import pytesseract
import re

class ExpenseProcessor:
    def __init__(self):
        """Initialize the Expense Processor with configuration"""

        # Setup logging
        logging.basicConfig(
            filename=f'/Logs/expense_processor_{datetime.now().strftime("%Y%m%d")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Database for storing expenses
        self.db_path = '/Data/expenses.db'
        self._setup_database()

        # Expense categories and policies
        self.categories = {
            'travel': ['airfare', 'lodging', 'meals', 'ground_transportation', 'parking', 'car_rental'],
            'office': ['rent', 'utilities', 'office_supplies', 'equipment', 'maintenance'],
            'meals_entertainment': ['business_meals', 'entertainment', 'gifts'],
            'marketing': ['online_ads', 'print_ads', 'trade_shows', 'promotional_items'],
            'professional_services': ['legal', 'accounting', 'consulting', 'recruitment'],
            'technology': ['software', 'hardware', 'cloud_services', 'telecom'],
            'insurance': ['general_liability', 'professional_liability', 'property_insurance', 'health_insurance'],
            'payroll_benefits': ['salaries', 'benefits', 'bonuses', 'payroll_taxes'],
            'banking_finance': ['bank_fees', 'loan_interest', 'credit_card_fees', 'investment_expenses'],
            'utilities_services': ['electricity', 'water_sewer', 'internet', 'phone']
        }

        # Approval thresholds
        self.approval_thresholds = {
            'employee': 50,
            'manager': 200,
            'department_head': 1000,
            'vp': 5000,
            'executive': float('inf')
        }

        # Receipt requirements by amount
        self.receipt_thresholds = {
            'amount': 25,
            'required': True
        }

    def _setup_database(self):
        """Setup database for storing expenses"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main expenses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_id TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                category TEXT NOT NULL,
                subcategory TEXT,
                vendor TEXT,
                description TEXT NOT NULL,
                date DATETIME NOT NULL,
                receipt_image_path TEXT,
                receipt_text TEXT,
                receipt_amount REAL,
                receipt_date TEXT,
                receipt_vendor TEXT,
                payment_method TEXT,
                project_code TEXT,
                employee_id TEXT NOT NULL,
                status TEXT DEFAULT 'submitted',  -- submitted, approved, rejected, reimbursed, archived
                approval_level TEXT DEFAULT 'employee',
                approved_by TEXT,
                approved_at DATETIME,
                created_by TEXT DEFAULT 'system',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Expense validation results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_id TEXT NOT NULL,
                validation_rule TEXT NOT NULL,
                result TEXT NOT NULL,  -- pass, fail, warning
                message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (expense_id) REFERENCES expenses (expense_id)
            )
        ''')

        # Approval workflow table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS approval_workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_id TEXT NOT NULL,
                level TEXT NOT NULL,  -- employee, manager, department_head, vp, executive
                approver TEXT,
                status TEXT DEFAULT 'pending',  -- pending, approved, rejected
                comments TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (expense_id) REFERENCES expenses (expense_id)
            )
        ''')

        # Indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_expense_id ON expenses(expense_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON expenses(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON expenses(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_employee_id ON expenses(employee_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON expenses(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_project_code ON expenses(project_code)')

        conn.commit()
        conn.close()

    def validate_expense_data(self, expense_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate expense data before processing

        Args:
            expense_data: Dictionary containing expense information

        Returns:
            Dict with validation results and corrected data
        """
        errors = []
        warnings = []
        corrected_data = expense_data.copy()

        # Validate amount
        amount = expense_data.get('amount', 0)
        if not isinstance(amount, (int, float)) or amount <= 0:
            errors.append("Amount must be a positive number")
        else:
            corrected_data['amount'] = round(float(amount), 2)

        # Validate date
        date_str = expense_data.get('date')
        if not date_str:
            errors.append("Date is required")
        else:
            try:
                expense_date = datetime.fromisoformat(str(date_str))
                if expense_date.date() > datetime.now().date():
                    errors.append("Expense date cannot be in the future")
                elif expense_date.year < datetime.now().year - 2:
                    warnings.append("Expense date is more than 2 years old")
            except ValueError:
                errors.append("Invalid date format")

        # Validate category
        category = expense_data.get('category', '').lower()
        if not category:
            errors.append("Category is required")
        elif category not in self.categories:
            errors.append(f"Invalid category: {category}")
        else:
            corrected_data['category'] = category

        # Validate description
        description = expense_data.get('description', '')
        if not description or len(description.strip()) < 10:
            errors.append("Description must be at least 10 characters with business purpose")
        else:
            corrected_data['description'] = description.strip()

        # Validate receipt requirement
        receipt_path = expense_data.get('receipt_image_path')
        if amount >= self.receipt_thresholds['amount'] and not receipt_path:
            errors.append(f"Receipt required for expenses over ${self.receipt_thresholds['amount']}")

        # Validate payment method
        payment_method = expense_data.get('payment_method', 'personal').lower()
        allowed_methods = ['personal', 'corporate_card', 'company_check', 'cash_advance']
        if payment_method not in allowed_methods:
            corrected_data['payment_method'] = 'personal'
            warnings.append(f"Payment method '{payment_method}' not recognized, defaulting to 'personal'")

        # Validate employee ID
        employee_id = expense_data.get('employee_id')
        if not employee_id:
            errors.append("Employee ID is required")

        # Validate project code if provided
        project_code = expense_data.get('project_code')
        if project_code:
            # In a real implementation, you'd validate against project database
            pass

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'corrected_data': corrected_data
        }

    def extract_receipt_info(self, receipt_path: str) -> Dict[str, Any]:
        """
        Extract information from receipt image

        Args:
            receipt_path: Path to receipt image file

        Returns:
            Dict containing extracted receipt information
        """
        try:
            # Open and preprocess image
            image = Image.open(receipt_path)

            # Convert to text using OCR
            text = pytesseract.image_to_string(image)

            # Extract amount using regex
            amount_pattern = r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})|\d+(?:\.\d{2}))'
            amounts = re.findall(amount_pattern, text)
            receipt_amount = None
            if amounts:
                # Take the largest amount as the receipt amount
                receipt_amount = max(float(a.replace(',', '')) for a in amounts)

            # Extract date using common date patterns
            date_patterns = [
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
                r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{2,4}'
            ]
            receipt_date = None
            for pattern in date_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    receipt_date = matches[0]
                    break

            # Extract vendor name (first line or common vendor patterns)
            lines = text.split('\n')
            vendor = ''
            for line in lines[:10]:  # Check first 10 lines
                clean_line = line.strip()
                if clean_line and len(clean_line) > 3:
                    vendor = clean_line
                    break

            return {
                'text': text,
                'amount': receipt_amount,
                'date': receipt_date,
                'vendor': vendor,
                'raw_lines': lines
            }

        except Exception as e:
            logging.error(f"Error extracting receipt info from {receipt_path}: {str(e)}")
            return {
                'text': '',
                'amount': None,
                'date': None,
                'vendor': '',
                'raw_lines': []
            }

    def determine_approval_level(self, amount: float) -> str:
        """Determine the approval level needed for an expense"""
        if amount <= self.approval_thresholds['employee']:
            return 'employee'
        elif amount <= self.approval_thresholds['manager']:
            return 'manager'
        elif amount <= self.approval_thresholds['department_head']:
            return 'department_head'
        elif amount <= self.approval_thresholds['vp']:
            return 'vp'
        else:
            return 'executive'

    def process_expense(self, expense_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a new expense

        Args:
            expense_data: Dictionary containing expense information

        Returns:
            Dict with expense processing results
        """
        try:
            # Validate data
            validation_result = self.validate_expense_data(expense_data)

            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'errors': validation_result['errors'],
                    'warnings': validation_result['warnings'],
                    'expense_id': None
                }

            # Use corrected data
            corrected_data = validation_result['corrected_data']

            # Generate unique expense ID
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            expense_id = f"EXP-{timestamp}-{hashlib.md5(str(corrected_data).encode()).hexdigest()[:8].upper()}"

            # Extract receipt information if available
            receipt_info = {}
            receipt_path = corrected_data.get('receipt_image_path')
            if receipt_path and Path(receipt_path).exists():
                receipt_info = self.extract_receipt_info(receipt_path)

            # Determine approval level
            approval_level = self.determine_approval_level(corrected_data['amount'])

            # Determine initial status based on approval level
            initial_status = 'approved' if approval_level == 'employee' else 'submitted'

            # Insert into database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO expenses (
                    expense_id, amount, currency, category, subcategory, vendor,
                    description, date, receipt_image_path, receipt_text, receipt_amount,
                    receipt_date, receipt_vendor, payment_method, project_code,
                    employee_id, status, approval_level, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                expense_id,
                corrected_data['amount'],
                corrected_data.get('currency', 'USD'),
                corrected_data['category'],
                corrected_data.get('subcategory'),
                corrected_data.get('vendor'),
                corrected_data['description'],
                corrected_data['date'],
                receipt_path,
                receipt_info.get('text'),
                receipt_info.get('amount'),
                receipt_info.get('date'),
                receipt_info.get('vendor'),
                corrected_data.get('payment_method', 'personal'),
                corrected_data.get('project_code'),
                corrected_data['employee_id'],
                initial_status,
                approval_level,
                corrected_data.get('created_by', 'system')
            ))

            expense_db_id = cursor.lastrowid

            # Insert validation results
            for error in validation_result['errors']:
                cursor.execute('''
                    INSERT INTO validation_results (expense_id, validation_rule, result, message)
                    VALUES (?, ?, ?, ?)
                ''', (expense_id, 'expense_validation', 'fail', error))

            for warning in validation_result['warnings']:
                cursor.execute('''
                    INSERT INTO validation_results (expense_id, validation_rule, result, message)
                    VALUES (?, ?, ?, ?)
                ''', (expense_id, 'expense_validation', 'warning', warning))

            # Create approval workflow if needed
            if approval_level != 'employee':
                cursor.execute('''
                    INSERT INTO approval_workflows (expense_id, level)
                    VALUES (?, ?)
                ''', (expense_id, approval_level))

            conn.commit()
            conn.close()

            logging.info(f"Expense {expense_id} processed successfully")

            return {
                'success': True,
                'expense_id': expense_id,
                'status': initial_status,
                'requires_approval': approval_level != 'employee',
                'warnings': validation_result['warnings']
            }

        except Exception as e:
            logging.error(f"Failed to process expense: {str(e)}")
            return {
                'success': False,
                'errors': [str(e)],
                'warnings': [],
                'expense_id': None
            }

    def submit_for_approval(self, expense_id: str, approver: str) -> bool:
        """Submit an expense for approval"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Update expense status
            cursor.execute('''
                UPDATE expenses
                SET status = 'submitted', updated_at = ?
                WHERE expense_id = ? AND status = 'draft'
            ''', (datetime.now(), expense_id))

            # Update approval workflow
            cursor.execute('''
                UPDATE approval_workflows
                SET approver = ?, status = 'pending', updated_at = ?
                WHERE expense_id = ? AND status = 'pending'
            ''', (approver, datetime.now(), expense_id))

            conn.commit()
            success = cursor.rowcount > 0
            conn.close()

            if success:
                logging.info(f"Expense {expense_id} submitted for approval to {approver}")
            else:
                logging.warning(f"Failed to submit expense {expense_id} for approval")

            return success

        except Exception as e:
            logging.error(f"Failed to submit expense {expense_id} for approval: {str(e)}")
            return False

    def approve_expense(self, expense_id: str, approver: str, comments: str = None) -> bool:
        """Approve an expense"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get current expense status and approval level
            cursor.execute('''
                SELECT status, approval_level FROM expenses WHERE expense_id = ?
            ''', (expense_id,))
            result = cursor.fetchone()

            if not result:
                logging.warning(f"Expense {expense_id} not found")
                return False

            current_status, approval_level = result

            if current_status != 'submitted':
                logging.warning(f"Expense {expense_id} is not in submitted status")
                return False

            # Update expense status
            new_status = 'approved'  # If this is the final approval level
            cursor.execute('''
                UPDATE expenses
                SET status = ?, approved_by = ?, approved_at = ?, updated_at = ?
                WHERE expense_id = ?
            ''', (new_status, approver, datetime.now(), datetime.now(), expense_id))

            # Update approval workflow
            cursor.execute('''
                UPDATE approval_workflows
                SET status = 'approved', comments = ?, updated_at = ?
                WHERE expense_id = ? AND approver = ?
            ''', (comments, datetime.now(), expense_id, approver))

            conn.commit()
            success = cursor.rowcount > 0
            conn.close()

            if success:
                logging.info(f"Expense {expense_id} approved by {approver}")
            else:
                logging.warning(f"Failed to approve expense {expense_id}")

            return success

        except Exception as e:
            logging.error(f"Failed to approve expense {expense_id}: {str(e)}")
            return False

    def reject_expense(self, expense_id: str, approver: str, reason: str) -> bool:
        """Reject an expense"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Update expense status
            cursor.execute('''
                UPDATE expenses
                SET status = 'rejected', updated_at = ?
                WHERE expense_id = ? AND status = 'submitted'
            ''', (datetime.now(), expense_id))

            # Update approval workflow
            cursor.execute('''
                UPDATE approval_workflows
                SET status = 'rejected', comments = ?, updated_at = ?
                WHERE expense_id = ? AND approver = ?
            ''', (reason, datetime.now(), expense_id, approver))

            conn.commit()
            success = cursor.rowcount > 0
            conn.close()

            if success:
                logging.info(f"Expense {expense_id} rejected by {approver}: {reason}")
            else:
                logging.warning(f"Failed to reject expense {expense_id}")

            return success

        except Exception as e:
            logging.error(f"Failed to reject expense {expense_id}: {str(e)}")
            return False

    def get_expense(self, expense_id: str) -> Dict[str, Any]:
        """Retrieve an expense by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM expenses WHERE expense_id = ?
            ''', (expense_id,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return {
                'id': row[0],
                'expense_id': row[1],
                'amount': row[2],
                'currency': row[3],
                'category': row[4],
                'subcategory': row[5],
                'vendor': row[6],
                'description': row[7],
                'date': row[8],
                'receipt_image_path': row[9],
                'receipt_text': row[10],
                'receipt_amount': row[11],
                'receipt_date': row[12],
                'receipt_vendor': row[13],
                'payment_method': row[14],
                'project_code': row[15],
                'employee_id': row[16],
                'status': row[17],
                'approval_level': row[18],
                'approved_by': row[19],
                'approved_at': row[20],
                'created_by': row[21],
                'created_at': row[22],
                'updated_at': row[23]
            }

        except Exception as e:
            logging.error(f"Failed to retrieve expense {expense_id}: {str(e)}")
            return None

    def search_expenses(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search for expenses with various filters"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query_parts = ["SELECT * FROM expenses WHERE 1=1"]
            params = []

            if filters:
                if filters.get('status'):
                    query_parts.append("AND status = ?")
                    params.append(filters['status'])

                if filters.get('date_from'):
                    query_parts.append("AND date >= ?")
                    params.append(filters['date_from'])

                if filters.get('date_to'):
                    query_parts.append("AND date <= ?")
                    params.append(filters['date_to'])

                if filters.get('category'):
                    query_parts.append("AND category = ?")
                    params.append(filters['category'])

                if filters.get('employee_id'):
                    query_parts.append("AND employee_id = ?")
                    params.append(filters['employee_id'])

                if filters.get('min_amount'):
                    query_parts.append("AND amount >= ?")
                    params.append(filters['min_amount'])

                if filters.get('max_amount'):
                    query_parts.append("AND amount <= ?")
                    params.append(filters['max_amount'])

                if filters.get('project_code'):
                    query_parts.append("AND project_code = ?")
                    params.append(filters['project_code'])

            query_parts.append("ORDER BY date DESC")
            query = " ".join(query_parts)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            expenses = []
            for row in rows:
                expenses.append({
                    'id': row[0],
                    'expense_id': row[1],
                    'amount': row[2],
                    'currency': row[3],
                    'category': row[4],
                    'subcategory': row[5],
                    'vendor': row[6],
                    'description': row[7],
                    'date': row[8],
                    'receipt_image_path': row[9],
                    'payment_method': row[14],
                    'project_code': row[15],
                    'employee_id': row[16],
                    'status': row[17],
                    'approval_level': row[18],
                    'created_at': row[22]
                })

            return expenses

        except Exception as e:
            logging.error(f"Failed to search expenses: {str(e)}")
            return []

    def get_employee_expenses(self, employee_id: str, month: int = None, year: int = None) -> List[Dict[str, Any]]:
        """Get expenses for an employee, optionally filtered by month/year"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "SELECT * FROM expenses WHERE employee_id = ?"
            params = [employee_id]

            if month and year:
                query += " AND strftime('%m', date) = ? AND strftime('%Y', date) = ?"
                params.extend([f"{month:02d}", str(year)])

            query += " ORDER BY date DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            expenses = []
            for row in rows:
                expenses.append({
                    'id': row[0],
                    'expense_id': row[1],
                    'amount': row[2],
                    'category': row[4],
                    'description': row[7],
                    'date': row[8],
                    'status': row[17],
                    'created_at': row[22]
                })

            return expenses

        except Exception as e:
            logging.error(f"Failed to get expenses for employee {employee_id}: {str(e)}")
            return []

    def get_expense_statistics(self, employee_id: str = None) -> Dict[str, Any]:
        """Get expense statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Base query
            base_query = "SELECT COUNT(*), SUM(amount), AVG(amount) FROM expenses WHERE status IN ('approved', 'reimbursed')"
            params = []

            if employee_id:
                base_query += " AND employee_id = ?"
                params.append(employee_id)

            # Total expenses
            cursor.execute(base_query, params)
            count, total_sum, avg_amount = cursor.fetchone()
            total_expenses = count or 0
            total_amount = total_sum or 0
            average_amount = avg_amount or 0

            # Expenses by status
            status_query = "SELECT status, COUNT(*) FROM expenses"
            if employee_id:
                status_query += " WHERE employee_id = ?"
                cursor.execute(status_query + " GROUP BY status", [employee_id] if employee_id else [])
            else:
                cursor.execute(status_query + " GROUP BY status")

            status_counts = dict(cursor.fetchall())

            # Expenses by category
            category_query = "SELECT category, COUNT(*), SUM(amount) FROM expenses"
            if employee_id:
                category_query += " WHERE employee_id = ?"
                cursor.execute(category_query + " GROUP BY category", [employee_id])
            else:
                cursor.execute(category_query + " GROUP BY category")

            category_data = cursor.fetchall()
            category_totals = {}
            for cat, count, amount in category_data:
                category_totals[cat] = {
                    'count': count,
                    'total_amount': amount or 0
                }

            conn.close()

            return {
                'total_expenses': total_expenses,
                'total_amount': round(total_amount, 2),
                'average_amount': round(average_amount, 2),
                'status_breakdown': status_counts,
                'category_breakdown': category_totals
            }

        except Exception as e:
            logging.error(f"Failed to get expense statistics: {str(e)}")
            return {}

    def generate_expense_report(self, employee_id: str = None, start_date: str = None, end_date: str = None) -> str:
        """Generate an expense report"""
        try:
            # Get filtered expenses
            filters = {}
            if start_date:
                filters['date_from'] = start_date
            if end_date:
                filters['date_to'] = end_date
            if employee_id:
                filters['employee_id'] = employee_id

            expenses = self.search_expenses(filters)

            # Create report directory if it doesn't exist
            report_dir = Path('/Reports/expenses')
            report_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_prefix = f"expense_report_{employee_id or 'all'}_{timestamp}"
            report_path = report_dir / f"{filename_prefix}.json"

            # Create report data
            report_data = {
                'report_generated': datetime.now().isoformat(),
                'filters': filters,
                'expenses': expenses,
                'statistics': self.get_expense_statistics(employee_id)
            }

            # Write report
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)

            logging.info(f"Expense report generated: {report_path}")
            return str(report_path)

        except Exception as e:
            logging.error(f"Failed to generate expense report: {str(e)}")
            raise

async def main():
    """Main function for testing the Expense Processor"""
    processor = ExpenseProcessor()

    # Example: Process a new expense
    sample_expense = {
        'amount': 125.50,
        'currency': 'USD',
        'category': 'travel',
        'subcategory': 'meals',
        'vendor': 'Airport Restaurant',
        'description': 'Dinner during business trip to meet client',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'receipt_image_path': '/tmp/sample_receipt.jpg',  # This would be a real path
        'payment_method': 'corporate_card',
        'project_code': 'PROJ-2023-Q4',
        'employee_id': 'EMP-001'
    }

    result = processor.process_expense(sample_expense)
    print(f"Expense processing result: {result}")

    # Get expense statistics
    stats = processor.get_expense_statistics()
    print(f"Expense statistics: {stats}")

    # Generate a report
    try:
        report_path = processor.generate_expense_report(employee_id='EMP-001')
        print(f"Expense report generated at: {report_path}")
    except Exception as e:
        print(f"Failed to generate report: {e}")

if __name__ == "__main__":
    asyncio.run(main())