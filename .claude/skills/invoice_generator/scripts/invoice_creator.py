#!/usr/bin/env python3
"""
Invoice Generator Module for Invoice Generator Skill
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
from jinja2 import Template
import pdfkit
import csv

class InvoiceGenerator:
    def __init__(self):
        """Initialize the Invoice Generator with configuration"""

        # Setup logging
        logging.basicConfig(
            filename=f'/Logs/invoice_generator_{datetime.now().strftime("%Y%m%d")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Database for storing invoices
        self.db_path = '/Data/invoices.db'
        self._setup_database()

        # Approval thresholds
        self.approval_thresholds = {
            'auto_approve': 500,
            'manager_approve': 5000,
            'executive_approve': float('inf')
        }

        # Tax rates by location
        self.tax_rates = {
            'US-NORMAL': 0.0,  # Varies by state
            'US-CA': 0.0725,
            'US-NY': 0.08,
            'US-TX': 0.0625,
            'EU-VAT': 0.20,  # Standard EU VAT
            'DEFAULT': 0.0
        }

    def _setup_database(self):
        """Setup database for storing invoices"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main invoices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT UNIQUE NOT NULL,
                client_info TEXT NOT NULL,
                invoice_date DATETIME NOT NULL,
                due_date DATETIME NOT NULL,
                items TEXT NOT NULL,  -- JSON of items
                subtotal REAL NOT NULL,
                tax_amount REAL DEFAULT 0.0,
                discount_amount REAL DEFAULT 0.0,
                total_amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                payment_terms TEXT DEFAULT 'Net30',
                status TEXT DEFAULT 'draft',  -- draft, pending_approval, approved, sent, paid, overdue, cancelled
                notes TEXT,
                created_by TEXT DEFAULT 'system',
                approved_by TEXT,
                approved_at DATETIME,
                sent_at DATETIME,
                paid_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Invoice items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                total_price REAL NOT NULL,
                tax_rate REAL DEFAULT 0.0,
                taxable BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (invoice_id) REFERENCES invoices (id)
            )
        ''')

        # Client database
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                address TEXT,
                email TEXT,
                phone TEXT,
                tax_id TEXT,
                credit_limit REAL DEFAULT 100000.0,
                payment_terms TEXT DEFAULT 'Net30',
                status TEXT DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_invoice_number ON invoices(invoice_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_invoice_date ON invoices(invoice_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_due_date ON invoices(due_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON invoices(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_client_info ON invoices(client_info)')

        conn.commit()
        conn.close()

    def validate_invoice_data(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate invoice data before creation

        Args:
            invoice_data: Dictionary containing invoice information

        Returns:
            Dict with validation results and corrected data
        """
        errors = []
        warnings = []
        corrected_data = invoice_data.copy()

        # Validate client information
        if not invoice_data.get('client_info'):
            errors.append("Client information is required")
        else:
            client_info = invoice_data['client_info']
            if not isinstance(client_info, dict):
                errors.append("Client information must be a dictionary")
            else:
                required_fields = ['name', 'address']
                for field in required_fields:
                    if not client_info.get(field):
                        errors.append(f"Client {field} is required")

        # Validate invoice date
        if not invoice_data.get('invoice_date'):
            corrected_data['invoice_date'] = datetime.now().strftime('%Y-%m-%d')
            warnings.append("Invoice date set to today's date")
        else:
            try:
                inv_date = datetime.fromisoformat(str(invoice_data['invoice_date']))
                if inv_date.date() > datetime.now().date():
                    errors.append("Invoice date cannot be in the future")
            except ValueError:
                errors.append("Invalid invoice date format")

        # Validate due date
        if not invoice_data.get('due_date'):
            due_date = datetime.now() + timedelta(days=30)
            corrected_data['due_date'] = due_date.strftime('%Y-%m-%d')
            warnings.append("Due date set to 30 days from invoice date")
        else:
            try:
                due_date = datetime.fromisoformat(str(invoice_data['due_date']))
                inv_date = datetime.fromisoformat(str(corrected_data['invoice_date']))

                if due_date.date() <= inv_date.date():
                    errors.append("Due date must be after invoice date")
            except ValueError:
                errors.append("Invalid due date format")

        # Validate items
        if not invoice_data.get('items') or not isinstance(invoice_data['items'], list):
            errors.append("Invoice items are required and must be a list")
        else:
            total_subtotal = 0
            for i, item in enumerate(invoice_data['items']):
                if not isinstance(item, dict):
                    errors.append(f"Item {i+1} must be a dictionary")
                    continue

                required_item_fields = ['description', 'quantity', 'unit_price']
                for field in required_item_fields:
                    if field not in item:
                        errors.append(f"Item {i+1} missing required field: {field}")

                if item.get('quantity') and item.get('unit_price'):
                    calculated_total = item['quantity'] * item['unit_price']
                    total_subtotal += calculated_total

                    if abs(calculated_total - item.get('total_price', calculated_total)) > 0.01:
                        corrected_data['items'][i]['total_price'] = calculated_total
                        warnings.append(f"Corrected total price for item {i+1}")

            if abs(total_subtotal - invoice_data.get('subtotal', total_subtotal)) > 0.01:
                corrected_data['subtotal'] = round(total_subtotal, 2)
                warnings.append("Subtotal corrected based on items")

        # Validate amounts
        if corrected_data.get('total_amount', 0) <= 0:
            errors.append("Total amount must be positive")

        # Validate payment terms
        allowed_terms = ['Net30', 'Net15', 'DueOnReceipt', 'Net60', 'Net90']
        payment_terms = corrected_data.get('payment_terms', 'Net30')
        if payment_terms not in allowed_terms:
            corrected_data['payment_terms'] = 'Net30'
            warnings.append("Payment terms corrected to default")

        # Validate currency
        allowed_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY']
        currency = corrected_data.get('currency', 'USD')
        if currency not in allowed_currencies:
            corrected_data['currency'] = 'USD'
            warnings.append("Currency corrected to USD")

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'corrected_data': corrected_data
        }

    def generate_invoice_number(self, client_id: str) -> str:
        """Generate a unique invoice number"""
        timestamp = datetime.now().strftime('%Y%m%d')

        # Get next invoice number for this date
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) FROM invoices
            WHERE invoice_number LIKE ?
        ''', (f"INV-{timestamp}-%",))

        count = cursor.fetchone()[0]
        conn.close()

        return f"INV-{timestamp}-{count + 1:03d}"

    def calculate_taxes(self, items: List[Dict], client_info: Dict) -> Dict[str, float]:
        """
        Calculate taxes for invoice items

        Args:
            items: List of invoice items
            client_info: Client information including location

        Returns:
            Dict with tax calculations
        """
        subtotal = sum(item['quantity'] * item['unit_price'] for item in items)
        tax_amount = 0.0

        # Determine tax rate based on client location
        client_location = client_info.get('address', '').split('\n')[-1].strip()  # Assume last line is state/country
        tax_rate = self.determine_tax_rate(client_location)

        # Calculate tax for taxable items only
        for item in items:
            if item.get('taxable', True):
                item_taxable_amount = item['quantity'] * item['unit_price']
                item_tax = item_taxable_amount * tax_rate
                tax_amount += item_tax

        total_amount = subtotal + tax_amount

        # Apply discount if any
        discount_percent = 0.0  # For now, hardcoded; would come from invoice data
        discount_amount = total_amount * (discount_percent / 100)
        final_total = total_amount - discount_amount

        return {
            'subtotal': round(subtotal, 2),
            'tax_rate': tax_rate,
            'tax_amount': round(tax_amount, 2),
            'discount_amount': round(discount_amount, 2),
            'total_amount': round(final_total, 2)
        }

    def determine_tax_rate(self, location: str) -> float:
        """Determine tax rate based on location"""
        location_upper = location.upper()

        if 'CALIFORNIA' in location_upper or 'CA' in location_upper:
            return self.tax_rates['US-CA']
        elif 'NEW YORK' in location_upper or 'NY' in location_upper:
            return self.tax_rates['US-NY']
        elif 'TEXAS' in location_upper or 'TX' in location_upper:
            return self.tax_rates['US-TX']
        elif 'EU' in location_upper:
            return self.tax_rates['EU-VAT']
        else:
            return self.tax_rates['DEFAULT']

    def create_invoice(self, invoice_data: Dict[str, Any], client_id: str = None) -> Dict[str, Any]:
        """
        Create a new invoice

        Args:
            invoice_data: Dictionary containing invoice information
            client_id: Optional client ID to link to existing client

        Returns:
            Dict with invoice creation results
        """
        try:
            # Validate data
            validation_result = self.validate_invoice_data(invoice_data)

            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'errors': validation_result['errors'],
                    'warnings': validation_result['warnings'],
                    'invoice_id': None
                }

            # Use corrected data
            corrected_data = validation_result['corrected_data']

            # Generate invoice number
            if not corrected_data.get('invoice_number'):
                corrected_data['invoice_number'] = self.generate_invoice_number(client_id or 'TEMP')

            # Calculate taxes and totals
            if 'items' in corrected_data:
                tax_calculation = self.calculate_taxes(corrected_data['items'], corrected_data['client_info'])

                corrected_data['subtotal'] = tax_calculation['subtotal']
                corrected_data['tax_amount'] = tax_calculation['tax_amount']
                corrected_data['total_amount'] = tax_calculation['total_amount']
                corrected_data['discount_amount'] = tax_calculation['discount_amount']

            # Determine approval level
            amount = corrected_data['total_amount']
            approval_level = self.determine_approval_level(amount)

            # Set initial status based on approval
            initial_status = 'draft' if approval_level == 'auto_approve' else 'pending_approval'

            # Insert into database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO invoices (
                    invoice_number, client_info, invoice_date, due_date,
                    items, subtotal, tax_amount, discount_amount, total_amount,
                    currency, payment_terms, status, notes, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                corrected_data['invoice_number'],
                json.dumps(corrected_data['client_info']),
                corrected_data['invoice_date'],
                corrected_data['due_date'],
                json.dumps(corrected_data['items']),
                corrected_data['subtotal'],
                corrected_data['tax_amount'],
                corrected_data['discount_amount'],
                corrected_data['total_amount'],
                corrected_data['currency'],
                corrected_data['payment_terms'],
                initial_status,
                corrected_data.get('notes', ''),
                corrected_data.get('created_by', 'system')
            ))

            invoice_id = cursor.lastrowid

            # Insert invoice items
            for item in corrected_data['items']:
                cursor.execute('''
                    INSERT INTO invoice_items (
                        invoice_id, description, quantity, unit_price,
                        total_price, tax_rate, taxable
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    invoice_id,
                    item['description'],
                    item['quantity'],
                    item['unit_price'],
                    item['total_price'],
                    item.get('tax_rate', 0.0),
                    item.get('taxable', True)
                ))

            conn.commit()
            conn.close()

            # If auto-approved, mark as approved
            if approval_level == 'auto_approve':
                self.approve_invoice(invoice_id, 'system')

            logging.info(f"Invoice {corrected_data['invoice_number']} created with ID {invoice_id}")

            return {
                'success': True,
                'invoice_id': invoice_id,
                'invoice_number': corrected_data['invoice_number'],
                'status': initial_status,
                'approval_required': approval_level != 'auto_approve',
                'warnings': validation_result['warnings']
            }

        except Exception as e:
            logging.error(f"Failed to create invoice: {str(e)}")
            return {
                'success': False,
                'errors': [str(e)],
                'warnings': [],
                'invoice_id': None
            }

    def determine_approval_level(self, amount: float) -> str:
        """Determine the approval level needed for an invoice"""
        if amount <= self.approval_thresholds['auto_approve']:
            return 'auto_approve'
        elif amount <= self.approval_thresholds['manager_approve']:
            return 'manager_approve'
        else:
            return 'executive_approve'

    def approve_invoice(self, invoice_id: int, approver: str) -> bool:
        """Approve an invoice that requires approval"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE invoices
                SET status = 'approved', approved_by = ?, approved_at = ?
                WHERE id = ? AND status = 'pending_approval'
            ''', (approver, datetime.now(), invoice_id))

            success = cursor.rowcount > 0
            conn.commit()
            conn.close()

            if success:
                logging.info(f"Invoice {invoice_id} approved by {approver}")
            else:
                logging.warning(f"Failed to approve invoice {invoice_id} (may already be approved or invalid status)")

            return success

        except Exception as e:
            logging.error(f"Failed to approve invoice {invoice_id}: {str(e)}")
            return False

    def generate_invoice_pdf(self, invoice_id: int) -> str:
        """Generate PDF invoice"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT invoice_number, client_info, invoice_date, due_date,
                       items, subtotal, tax_amount, discount_amount, total_amount,
                       currency, payment_terms, notes, status
                FROM invoices
                WHERE id = ?
            ''', (invoice_id,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                raise ValueError(f"Invoice {invoice_id} not found")

            # Parse data
            invoice_number, client_info_str, invoice_date, due_date, items_str = row[:5]
            subtotal, tax_amount, discount_amount, total_amount = row[5:9]
            currency, payment_terms, notes, status = row[9:]

            client_info = json.loads(client_info_str)
            items = json.loads(items_str)

            # Invoice template
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; }
                    .header { text-align: center; margin-bottom: 20px; }
                    .invoice-details { float: right; text-align: right; }
                    .client-info { margin-top: 30px; }
                    .items-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                    .items-table th, .items-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    .items-table th { background-color: #f2f2f2; }
                    .totals { margin-top: 20px; float: right; }
                    .footer { margin-top: 50px; clear: both; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>INVOICE</h1>
                </div>

                <div class="invoice-details">
                    <strong>Invoice #:</strong> {{ invoice_number }}<br>
                    <strong>Date:</strong> {{ invoice_date }}<br>
                    <strong>Due Date:</strong> {{ due_date }}<br>
                    <strong>Status:</strong> {{ status }}
                </div>

                <div class="client-info">
                    <h3>Bill To:</h3>
                    <p>{{ client_name }}</p>
                    <p>{{ client_address }}</p>
                </div>

                <table class="items-table">
                    <thead>
                        <tr>
                            <th>Description</th>
                            <th>Quantity</th>
                            <th>Unit Price ({{ currency }})</th>
                            <th>Total ({{ currency }})</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in items %}
                        <tr>
                            <td>{{ item.description }}</td>
                            <td>{{ item.quantity }}</td>
                            <td>{{ "%.2f"|format(item.unit_price) }}</td>
                            <td>{{ "%.2f"|format(item.total_price) }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>

                <div class="totals">
                    <p><strong>Subtotal:</strong> {{ currency }} {{ "%.2f"|format(subtotal) }}</p>
                    {% if tax_amount > 0 %}
                    <p><strong>Tax:</strong> {{ currency }} {{ "%.2f"|format(tax_amount) }}</p>
                    {% endif %}
                    {% if discount_amount > 0 %}
                    <p><strong>Discount:</strong> -{{ currency }} {{ "%.2f"|format(discount_amount) }}</p>
                    {% endif %}
                    <p><strong>Total:</strong> {{ currency }} {{ "%.2f"|format(total_amount) }}</p>
                </div>

                <div class="footer">
                    <p><strong>Payment Terms:</strong> {{ payment_terms }}</p>
                    {% if notes %}
                    <p><strong>Notes:</strong> {{ notes }}</p>
                    {% endif %}
                    <p>Thank you for your business!</p>
                </div>
            </body>
            </html>
            """

            # Create Jinja2 template
            template = Template(html_template)

            # Render HTML
            html_content = template.render(
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                due_date=due_date,
                status=status,
                client_name=client_info.get('name', ''),
                client_address=client_info.get('address', '').replace('\n', '<br>'),
                items=items,
                currency=currency,
                subtotal=subtotal,
                tax_amount=tax_amount,
                discount_amount=discount_amount,
                total_amount=total_amount,
                payment_terms=payment_terms,
                notes=notes
            )

            # Create PDF directory if it doesn't exist
            pdf_dir = Path('/Documents/Invoices')
            pdf_dir.mkdir(parents=True, exist_ok=True)

            # Generate PDF filename
            filename = f"Invoice_{invoice_number}_{invoice_date.replace('-', '')}.pdf"
            pdf_path = pdf_dir / filename

            # Generate PDF
            pdfkit.from_string(html_content, str(pdf_path), options={'page-size': 'Letter'})

            logging.info(f"PDF generated for invoice {invoice_id}: {pdf_path}")
            return str(pdf_path)

        except Exception as e:
            logging.error(f"Failed to generate PDF for invoice {invoice_id}: {str(e)}")
            raise

    def get_invoice(self, invoice_id: int) -> Dict[str, Any]:
        """Retrieve an invoice by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, invoice_number, client_info, invoice_date, due_date,
                       items, subtotal, tax_amount, discount_amount, total_amount,
                       currency, payment_terms, status, notes, created_at, updated_at
                FROM invoices
                WHERE id = ?
            ''', (invoice_id,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            # Parse the client info and items from JSON
            client_info = json.loads(row[2])
            items = json.loads(row[5])

            return {
                'id': row[0],
                'invoice_number': row[1],
                'client_info': client_info,
                'invoice_date': row[3],
                'due_date': row[4],
                'items': items,
                'subtotal': row[6],
                'tax_amount': row[7],
                'discount_amount': row[8],
                'total_amount': row[9],
                'currency': row[10],
                'payment_terms': row[11],
                'status': row[12],
                'notes': row[13],
                'created_at': row[14],
                'updated_at': row[15]
            }

        except Exception as e:
            logging.error(f"Failed to retrieve invoice {invoice_id}: {str(e)}")
            return None

    def search_invoices(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search for invoices with various filters"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query_parts = ["SELECT id, invoice_number, client_info, invoice_date, due_date, total_amount, status FROM invoices WHERE 1=1"]
            params = []

            if filters:
                if filters.get('status'):
                    query_parts.append("AND status = ?")
                    params.append(filters['status'])

                if filters.get('date_from'):
                    query_parts.append("AND invoice_date >= ?")
                    params.append(filters['date_from'])

                if filters.get('date_to'):
                    query_parts.append("AND invoice_date <= ?")
                    params.append(filters['date_to'])

                if filters.get('client_name'):
                    query_parts.append("AND client_info LIKE ?")
                    params.append(f"%{filters['client_name']}%")

                if filters.get('min_amount'):
                    query_parts.append("AND total_amount >= ?")
                    params.append(filters['min_amount'])

                if filters.get('max_amount'):
                    query_parts.append("AND total_amount <= ?")
                    params.append(filters['max_amount'])

            query_parts.append("ORDER BY invoice_date DESC")
            query = " ".join(query_parts)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            invoices = []
            for row in rows:
                client_info = json.loads(row[2])
                invoices.append({
                    'id': row[0],
                    'invoice_number': row[1],
                    'client_name': client_info.get('name', 'Unknown'),
                    'invoice_date': row[3],
                    'due_date': row[4],
                    'total_amount': row[5],
                    'status': row[6]
                })

            return invoices

        except Exception as e:
            logging.error(f"Failed to search invoices: {str(e)}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get invoice statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Total invoices
            cursor.execute("SELECT COUNT(*) FROM invoices")
            total_invoices = cursor.fetchone()[0]

            # Invoices by status
            cursor.execute("SELECT status, COUNT(*) FROM invoices GROUP BY status")
            status_counts = dict(cursor.fetchall())

            # Total amount billed
            cursor.execute("SELECT SUM(total_amount) FROM invoices WHERE status IN ('approved', 'sent', 'paid')")
            total_billed = cursor.fetchone()[0] or 0

            # Outstanding amount
            cursor.execute("""
                SELECT SUM(total_amount) FROM invoices
                WHERE status IN ('approved', 'sent') AND due_date >= ?
            """, (datetime.now().date().isoformat(),))
            outstanding = cursor.fetchone()[0] or 0

            # Overdue amount
            cursor.execute("""
                SELECT SUM(total_amount) FROM invoices
                WHERE status IN ('approved', 'sent') AND due_date < ? AND paid_at IS NULL
            """, (datetime.now().date().isoformat(),))
            overdue = cursor.fetchone()[0] or 0

            conn.close()

            return {
                'total_invoices': total_invoices,
                'status_breakdown': status_counts,
                'total_billed': round(total_billed, 2),
                'outstanding': round(outstanding, 2),
                'overdue': round(overdue, 2),
                'average_invoice_value': round(total_billed / total_invoices if total_invoices > 0 else 0, 2)
            }

        except Exception as e:
            logging.error(f"Failed to get invoice statistics: {str(e)}")
            return {}

async def main():
    """Main function for testing the Invoice Generator"""
    generator = InvoiceGenerator()

    # Example: Create a new invoice
    sample_invoice = {
        'client_info': {
            'name': 'Acme Corporation',
            'address': '123 Business Rd\nNew York, NY 10001\nUSA',
            'email': 'billing@acme.com',
            'phone': '+1-555-123-4567'
        },
        'invoice_date': datetime.now().strftime('%Y-%m-%d'),
        'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
        'items': [
            {
                'description': 'Consulting Services - Project Alpha',
                'quantity': 40,
                'unit_price': 150.00,
                'total_price': 6000.00,
                'taxable': True
            },
            {
                'description': 'Software License',
                'quantity': 1,
                'unit_price': 500.00,
                'total_price': 500.00,
                'taxable': True
            }
        ],
        'payment_terms': 'Net30',
        'notes': 'Thank you for your business!',
        'currency': 'USD'
    }

    result = generator.create_invoice(sample_invoice)
    print(f"Invoice creation result: {result}")

    if result['success']:
        # Generate PDF for the invoice
        try:
            pdf_path = generator.generate_invoice_pdf(result['invoice_id'])
            print(f"Invoice PDF generated at: {pdf_path}")
        except Exception as e:
            print(f"Failed to generate PDF: {e}")

        # Get invoice statistics
        stats = generator.get_statistics()
        print(f"Invoice statistics: {stats}")

if __name__ == "__main__":
    asyncio.run(main())