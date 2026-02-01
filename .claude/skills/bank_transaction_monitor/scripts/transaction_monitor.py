#!/usr/bin/env python3
"""
BankTransactionMonitor: Parses bank statements, categorizes transactions, and flags anomalies.

This module monitors bank transactions to identify unusual patterns, categorize expenses,
and flag potential fraud or errors for review.
"""

import os
import json
import sqlite3
import csv
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal


@dataclass
class Transaction:
    """Represents a bank transaction."""
    id: str
    date: datetime
    amount: Decimal
    description: str
    merchant: str
    category: str
    account: str
    transaction_type: str  # debit, credit
    status: str  # pending, cleared
    location: Optional[str] = None
    currency: str = 'USD'
    notes: Optional[str] = None
    user_category: Optional[str] = None
    is_business: bool = False
    requires_review: bool = False


class AlertLevel(Enum):
    """Levels of transaction alerts."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class TransactionCategory(Enum):
    """Standard transaction categories."""
    INCOME_SALARY = "salary/wages"
    INCOME_FREELANCE = "freelance_income"
    INCOME_INVESTMENT = "investment_income"
    INCOME_BUSINESS = "business_revenue"
    EXPENSE_RENT = "rent/mortgage"
    EXPENSE_UTILITIES = "utilities"
    EXPENSE_GROCERIES = "groceries"
    EXPENSE_DINING = "dining_out"
    EXPENSE_TRANSPORTATION = "transportation"
    EXPENSE_HEALTHCARE = "healthcare"
    EXPENSE_INSURANCE = "insurance"
    EXPENSE_ENTERTAINMENT = "entertainment"
    EXPENSE_TRAVEL = "travel"
    EXPENSE_SHOPPING = "shopping"
    EXPENSE_EDUCATION = "education"
    EXPENSE_CHARITY = "charitable_giving"
    EXPENSE_BUSINESS = "business_expenses"
    EXPENSE_PROFESSIONAL = "professional_services"


@dataclass
class TransactionAlert:
    """Represents an alert about a transaction."""
    transaction_id: str
    alert_level: AlertLevel
    rule_triggered: str
    message: str
    timestamp: datetime
    requires_action: bool = False


class BankTransactionMonitor:
    """
    Monitors bank transactions to identify unusual patterns, categorize expenses,
    and flag potential fraud or errors for review.

    The monitor performs several functions:
    1. Transaction categorization based on merchant and description
    2. Anomaly detection using statistical methods
    3. Fraud detection based on known patterns
    4. Budget monitoring and alerts
    5. Business vs. personal expense separation
    """

    def __init__(self, db_path: str = "./bank_transactions.db"):
        self.db_path = db_path
        self.setup_database()

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('bank_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Load average spending patterns
        self.avg_spending = {}
        self.merchant_patterns = {}
        self.location_history = []

    def setup_database(self):
        """Initialize the database schema for transaction tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                date DATETIME,
                amount REAL,
                description TEXT,
                merchant TEXT,
                category TEXT,
                account TEXT,
                transaction_type TEXT,
                status TEXT,
                location TEXT,
                currency TEXT,
                notes TEXT,
                user_category TEXT,
                is_business BOOLEAN,
                requires_review BOOLEAN,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT,
                alert_level TEXT,
                rule_triggered TEXT,
                message TEXT,
                timestamp DATETIME,
                requires_action BOOLEAN,
                resolved BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (transaction_id) REFERENCES transactions (id)
            )
        ''')

        # Create categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                parent_category TEXT,
                is_business BOOLEAN DEFAULT FALSE
            )
        ''')

        # Create merchant mappings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS merchant_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_name TEXT,
                normalized_name TEXT,
                category TEXT,
                is_business BOOLEAN,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def parse_bank_statement(self, statement_path: str) -> List[Transaction]:
        """
        Parse a bank statement file and return a list of transactions.

        Supports CSV and OFX formats. For CSV, expects columns:
        Date, Description, Amount, Type
        """
        transactions = []

        if statement_path.endswith('.csv'):
            transactions = self._parse_csv_statement(statement_path)
        elif statement_path.endswith('.ofx'):
            transactions = self._parse_ofx_statement(statement_path)
        else:
            raise ValueError(f"Unsupported statement format: {statement_path}")

        return transactions

    def _parse_csv_statement(self, csv_path: str) -> List[Transaction]:
        """Parse a CSV bank statement file."""
        transactions = []

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    # Parse date (try common formats)
                    date_str = row['Date']
                    date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%Y-%m-%dT%H:%M:%S']

                    parsed_date = None
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue

                    if parsed_date is None:
                        raise ValueError(f"Could not parse date: {date_str}")

                    # Parse amount (handle negative amounts)
                    amount_str = str(row['Amount']).replace('$', '').replace(',', '')
                    amount = abs(Decimal(amount_str))

                    # Determine transaction type based on sign or column
                    trans_type = 'debit'
                    if float(amount_str) < 0:
                        trans_type = 'credit'
                    elif 'Type' in row and 'credit' in row['Type'].lower():
                        trans_type = 'credit'

                    # Extract merchant name from description
                    description = row.get('Description', row.get('Desc', ''))
                    merchant = self._extract_merchant(description)

                    transaction = Transaction(
                        id=self._generate_id(),
                        date=parsed_date,
                        amount=amount,
                        description=description,
                        merchant=merchant,
                        category='',  # Will categorize later
                        account=row.get('Account', 'primary'),
                        transaction_type=trans_type,
                        status='cleared',
                        location=None,
                        currency='USD',
                        notes=None,
                        user_category=None,
                        is_business=False,
                        requires_review=False
                    )

                    transactions.append(transaction)

                except Exception as e:
                    self.logger.warning(f"Error parsing row: {e}. Row data: {row}")
                    continue

        return transactions

    def _parse_ofx_statement(self, ofx_path: str) -> List[Transaction]:
        """Parse an OFX bank statement file."""
        # This is a simplified OFX parser
        # In a real implementation, you'd want to use a proper OFX library
        transactions = []

        with open(ofx_path, 'r') as f:
            content = f.read()

            # Simplified OFX parsing (real implementation would be more robust)
            # Look for STMTTRN blocks
            import re
            pattern = r'<STMTTRN>.*?</STMTTRN>'
            matches = re.findall(pattern, content, re.DOTALL)

            for match in matches:
                # Extract fields from OFX block
                dt posted_match = re.search(r'<DTPOSTED>(\d+)', match)
                trnamt_match = re.search(r'<TRNAMT>([-\d.]+)', match)
                name_match = re.search(r'<NAME>([^<]+)', match)

                if all([dt_posted_match, trnamt_match, name_match]):
                    # Parse date (OFX date format: YYYYMMDDHHMMSS)
                    date_str = dt_posted_match.group(1)[:8]  # Get just YYYYMMDD
                    parsed_date = datetime.strptime(date_str, '%Y%m%d')

                    amount = abs(Decimal(trnamt_match.group(1)))
                    merchant = name_match.group(1).strip()

                    transaction = Transaction(
                        id=self._generate_id(),
                        date=parsed_date,
                        amount=amount,
                        description=merchant,
                        merchant=merchant,
                        category='',
                        account='primary',
                        transaction_type='debit' if float(trnamt_match.group(1)) >= 0 else 'credit',
                        status='cleared',
                        location=None,
                        currency='USD',
                        notes=None,
                        user_category=None,
                        is_business=False,
                        requires_review=False
                    )

                    transactions.append(transaction)

        return transactions

    def _extract_merchant(self, description: str) -> str:
        """Extract merchant name from transaction description."""
        # Common patterns in transaction descriptions
        patterns = [
            r'STARBUCKS.*',  # Starbucks purchases
            r'AMAZON.*',     # Amazon purchases
            r'WALMART.*',    # Walmart purchases
            r'WHOLEFDS.*',   # Whole Foods
            r'COSTCO.*',     # Costco
            r'^([^,*]+)',    # Take everything before first comma or asterisk
        ]

        for pattern in patterns:
            match = re.search(pattern, description.upper())
            if match:
                return match.group(1).strip()

        # If no pattern matches, return original description
        return description.strip()

    def _generate_id(self) -> str:
        """Generate a unique transaction ID."""
        import uuid
        return str(uuid.uuid4())

    def add_transactions(self, transactions: List[Transaction]) -> None:
        """Add transactions to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for transaction in transactions:
            # First, try to categorize the transaction
            if not transaction.category:
                transaction.category = self.categorize_transaction(transaction)

            # Determine if business based on category and merchant
            if transaction.category and 'business' in transaction.category.lower():
                transaction.is_business = True

            cursor.execute('''
                INSERT OR REPLACE INTO transactions
                (id, date, amount, description, merchant, category, account,
                 transaction_type, status, location, currency, notes,
                 user_category, is_business, requires_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                transaction.id, transaction.date.isoformat(),
                float(transaction.amount), transaction.description,
                transaction.merchant, transaction.category, transaction.account,
                transaction.transaction_type, transaction.status,
                transaction.location, transaction.currency, transaction.notes,
                transaction.user_category, transaction.is_business,
                transaction.requires_review
            ))

        conn.commit()
        conn.close()

    def categorize_transaction(self, transaction: Transaction) -> str:
        """Categorize a transaction based on merchant and description."""
        description_lower = transaction.description.lower()
        merchant_lower = transaction.merchant.lower()

        # Check for business indicators
        business_indicators = ['business', 'office', 'consulting', 'software', 'web', 'online', 'digital']
        is_business = any(indicator in description_lower for indicator in business_indicators)

        # Define category mapping patterns
        category_mapping = {
            'groceries': ['grocery', 'market', 'food', 'whole', 'kroger', 'safeway', 'walmart'],
            'dining_out': ['restaurant', 'cafe', 'bar', 'pub', 'starbucks', 'mcdonalds', 'chipotle'],
            'transportation': ['gas', 'fuel', 'shell', 'chevron', 'uber', 'lyft', 'taxi'],
            'healthcare': ['hospital', 'clinic', 'drug', 'pharmacy', 'walgreens', 'cvs'],
            'entertainment': ['movie', 'cinema', 'netflix', 'spotify', 'itunes', 'ticketmaster'],
            'travel': ['airline', 'hotel', 'airbnb', 'expedia', 'uber'],
            'insurance': ['insurance', 'geico', 'progressive', 'aetna'],
            'utilities': ['electric', 'gas', 'water', 'comcast', 'verizon', 'att'],
            'rent/mortgage': ['rent', 'mortgage', 'property'],
            'education': ['school', 'university', 'college', 'textbook'],
            'charitable_giving': ['charity', 'donation', 'nonprofit'],
            'business_expenses': business_indicators
        }

        # Check merchant and description for category matches
        for category, keywords in category_mapping.items():
            for keyword in keywords:
                if keyword in merchant_lower or keyword in description_lower:
                    return category

        # Default to shopping if nothing else matches
        return 'shopping'

    def detect_anomalies(self) -> List[Tuple[Transaction, TransactionAlert]]:
        """Detect anomalies in transaction patterns."""
        anomalies = []

        # Get recent transactions for analysis
        recent_transactions = self._get_recent_transactions(days=30)

        # Calculate spending averages
        self._calculate_spending_averages(recent_transactions)

        for transaction in recent_transactions:
            transaction_anomalies = self._analyze_transaction(transaction, recent_transactions)
            anomalies.extend([(transaction, anomaly) for anomaly in transaction_anomalies])

        # Store detected anomalies in database
        self._store_alerts([alert for _, alert in anomalies])

        return anomalies

    def _get_recent_transactions(self, days: int = 30) -> List[Transaction]:
        """Get transactions from the past specified number of days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute('''
            SELECT id, date, amount, description, merchant, category, account,
                   transaction_type, status, location, currency, notes,
                   user_category, is_business, requires_review
            FROM transactions
            WHERE date >= ?
            ORDER BY date DESC
        ''', (cutoff_date,))

        transactions = []
        for row in cursor.fetchall():
            transaction = Transaction(
                id=row[0],
                date=datetime.fromisoformat(row[1]),
                amount=Decimal(str(row[2])),
                description=row[3],
                merchant=row[4],
                category=row[5],
                account=row[6],
                transaction_type=row[7],
                status=row[8],
                location=row[9],
                currency=row[10],
                notes=row[11],
                user_category=row[12],
                is_business=bool(row[13]),
                requires_review=bool(row[14])
            )
            transactions.append(transaction)

        conn.close()
        return transactions

    def _calculate_spending_averages(self, transactions: List[Transaction]) -> None:
        """Calculate average spending patterns for anomaly detection."""
        if not transactions:
            return

        # Group by category and calculate averages
        category_amounts = {}
        merchant_amounts = {}

        for transaction in transactions:
            cat = transaction.category or 'unknown'
            merchant = transaction.merchant or 'unknown'

            if cat not in category_amounts:
                category_amounts[cat] = []
            category_amounts[cat].append(float(transaction.amount))

            if merchant not in merchant_amounts:
                merchant_amounts[merchant] = []
            merchant_amounts[merchant].append(float(transaction.amount))

        # Calculate averages and standard deviations
        self.avg_spending = {}
        for cat, amounts in category_amounts.items():
            self.avg_spending[f"avg_{cat}"] = {
                'mean': np.mean(amounts),
                'std': np.std(amounts),
                'count': len(amounts)
            }

        for merch, amounts in merchant_amounts.items():
            self.avg_spending[f"avg_{merch}"] = {
                'mean': np.mean(amounts),
                'std': np.std(amounts),
                'count': len(amounts)
            }

    def _analyze_transaction(self, transaction: Transaction, all_transactions: List[Transaction]) -> List[TransactionAlert]:
        """Analyze a single transaction for anomalies."""
        alerts = []

        # Check for unusually large transactions
        avg_key = f"avg_{transaction.category or 'unknown'}"
        if avg_key in self.avg_spending:
            avg_data = self.avg_spending[avg_key]
            mean_amount = avg_data['mean']
            std_amount = avg_data['std']

            if std_amount > 0 and float(transaction.amount) > (mean_amount + 3 * std_amount):
                alerts.append(TransactionAlert(
                    transaction_id=transaction.id,
                    alert_level=AlertLevel.WARNING,
                    rule_triggered="large_transaction",
                    message=f"Transaction amount ${transaction.amount} is significantly higher than average ${mean_amount:.2f} for category {transaction.category}",
                    timestamp=datetime.now(),
                    requires_action=True
                ))

        # Check for round number amounts (potential fraud)
        amount_float = float(transaction.amount)
        if amount_float == int(amount_float) and amount_float > 50:
            alerts.append(TransactionAlert(
                transaction_id=transaction.id,
                alert_level=AlertLevel.INFO,
                rule_triggered="round_number",
                message=f"Transaction amount ${transaction.amount} is a round number, which may indicate potential fraud",
                timestamp=datetime.now()
            ))

        # Check for small test charges (card testing)
        if amount_float < 5 and len([t for t in all_transactions if t.merchant == transaction.merchant]) > 2:
            recent_similar = [t for t in all_transactions[:10] if
                              t.merchant == transaction.merchant and float(t.amount) < 5]
            if len(recent_similar) > 2:
                alerts.append(TransactionAlert(
                    transaction_id=transaction.id,
                    alert_level=AlertLevel.WARNING,
                    rule_triggered="card_testing",
                    message=f"Multiple small transactions detected with {transaction.merchant}, possibly indicating card testing",
                    timestamp=datetime.now(),
                    requires_action=True
                ))

        # Check for duplicate transactions
        recent_transactions = [t for t in all_transactions
                              if (datetime.now() - t.date).days <= 7]
        duplicates = [t for t in recent_transactions
                     if (t.merchant == transaction.merchant and
                         float(t.amount) == amount_float and
                         t.id != transaction.id)]

        if duplicates:
            alerts.append(TransactionAlert(
                transaction_id=transaction.id,
                alert_level=AlertLevel.WARNING,
                rule_triggered="duplicate_transaction",
                message=f"Possible duplicate transaction detected with {transaction.merchant} for ${transaction.amount}",
                timestamp=datetime.now(),
                requires_action=True
            ))

        return alerts

    def _store_alerts(self, alerts: List[TransactionAlert]) -> None:
        """Store alerts in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for alert in alerts:
            cursor.execute('''
                INSERT INTO alerts
                (transaction_id, alert_level, rule_triggered, message, timestamp, requires_action)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                alert.transaction_id,
                alert.alert_level.value,
                alert.rule_triggered,
                alert.message,
                alert.timestamp.isoformat(),
                alert.requires_action
            ))

        conn.commit()
        conn.close()

    def get_unreviewed_alerts(self) -> List[TransactionAlert]:
        """Get all alerts that require action."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT transaction_id, alert_level, rule_triggered, message, timestamp, requires_action
            FROM alerts
            WHERE resolved = FALSE AND requires_action = TRUE
            ORDER BY timestamp DESC
        ''')

        alerts = []
        for row in cursor.fetchall():
            alert = TransactionAlert(
                transaction_id=row[0],
                alert_level=AlertLevel(row[1]),
                rule_triggered=row[2],
                message=row[3],
                timestamp=datetime.fromisoformat(row[4]),
                requires_action=bool(row[5])
            )
            alerts.append(alert)

        conn.close()
        return alerts

    def generate_spending_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate a spending report for the specified period."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT category, SUM(amount), COUNT(*)
            FROM transactions
            WHERE date BETWEEN ? AND ? AND transaction_type = 'debit'
            GROUP BY category
        ''', (start_date.isoformat(), end_date.isoformat()))

        category_totals = {}
        total_spending = 0
        transaction_count = 0

        for row in cursor.fetchall():
            category, amount, count = row
            category_totals[category] = {
                'total': amount,
                'count': count
            }
            total_spending += amount
            transaction_count += count

        # Calculate percentages
        category_percentages = {}
        for category, data in category_totals.items():
            category_percentages[category] = {
                'total': data['total'],
                'percentage': (data['total'] / total_spending * 100) if total_spending > 0 else 0,
                'count': data['count']
            }

        conn.close()

        return {
            'period_start': start_date,
            'period_end': end_date,
            'total_spending': total_spending,
            'transaction_count': transaction_count,
            'category_breakdown': category_percentages,
            'average_daily_spending': total_spending / max(1, (end_date - start_date).days)
        }

    def get_suspicious_transactions(self) -> List[Transaction]:
        """Get transactions flagged with critical or warning alerts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get transaction IDs with critical or warning alerts
        cursor.execute('''
            SELECT DISTINCT a.transaction_id
            FROM alerts a
            WHERE a.alert_level IN ('critical', 'warning') AND a.resolved = FALSE
        ''')

        suspicious_ids = [row[0] for row in cursor.fetchall()]

        if not suspicious_ids:
            conn.close()
            return []

        # Get the full transaction details
        placeholders = ','.join(['?' for _ in suspicious_ids])
        cursor.execute(f'''
            SELECT id, date, amount, description, merchant, category, account,
                   transaction_type, status, location, currency, notes,
                   user_category, is_business, requires_review
            FROM transactions
            WHERE id IN ({placeholders})
        ''', suspicious_ids)

        transactions = []
        for row in cursor.fetchall():
            transaction = Transaction(
                id=row[0],
                date=datetime.fromisoformat(row[1]),
                amount=Decimal(str(row[2])),
                description=row[3],
                merchant=row[4],
                category=row[5],
                account=row[6],
                transaction_type=row[7],
                status=row[8],
                location=row[9],
                currency=row[10],
                notes=row[11],
                user_category=row[12],
                is_business=bool(row[13]),
                requires_review=bool(row[14])
            )
            transactions.append(transaction)

        conn.close()
        return transactions

    def export_alerts_to_csv(self, output_path: str) -> None:
        """Export all alerts to a CSV file."""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query('''
            SELECT a.timestamp, a.alert_level, a.rule_triggered, a.message,
                   t.description, t.amount, t.merchant, t.category
            FROM alerts a
            JOIN transactions t ON a.transaction_id = t.id
            WHERE a.resolved = FALSE
            ORDER BY a.timestamp DESC
        ''', conn)

        df.to_csv(output_path, index=False)
        conn.close()

        self.logger.info(f"Alerts exported to {output_path}")


def main():
    """Main function for running the bank transaction monitor."""
    import argparse

    parser = argparse.ArgumentParser(description='Monitor bank transactions for anomalies')
    parser.add_argument('--db-path', default='./bank_transactions.db', help='Path to database file')
    parser.add_argument('--statement', help='Path to bank statement file (CSV or OFX)')
    parser.add_argument('--detect-anomalies', action='store_true', help='Run anomaly detection')
    parser.add_argument('--generate-report', action='store_true', help='Generate spending report')
    parser.add_argument('--export-alerts', help='Export alerts to CSV file')

    args = parser.parse_args()

    monitor = BankTransactionMonitor(db_path=args.db_path)

    # Load transactions if statement file provided
    if args.statement:
        transactions = monitor.parse_bank_statement(args.statement)
        monitor.add_transactions(transactions)
        print(f"Loaded {len(transactions)} transactions from {args.statement}")

    # Run anomaly detection if requested
    if args.detect_anomalies:
        anomalies = monitor.detect_anomalies()
        print(f"Detected {len(anomalies)} potential anomalies")

    # Generate report if requested
    if args.generate_report:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        report = monitor.generate_spending_report(start_date, end_date)

        print("\n--- SPENDING REPORT ---")
        print(f"Period: {start_date.date()} to {end_date.date()}")
        print(f"Total Spending: ${report['total_spending']:.2f}")
        print(f"Transaction Count: {report['transaction_count']}")
        print(f"Average Daily Spending: ${report['average_daily_spending']:.2f}")
        print("\nCategory Breakdown:")
        for category, data in report['category_breakdown'].items():
            print(f"  {category}: ${data['total']:.2f} ({data['percentage']:.1f}%)")

    # Export alerts if requested
    if args.export_alerts:
        monitor.export_alerts_to_csv(args.export_alerts)
        print(f"Alerts exported to {args.export_alerts}")


if __name__ == "__main__":
    main()