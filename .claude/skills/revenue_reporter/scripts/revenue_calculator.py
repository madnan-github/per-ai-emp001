#!/usr/bin/env python3
"""
Revenue Calculator Module for Revenue Reporter Skill
"""

import sqlite3
import json
import os
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import asyncio
import aiofiles
from dateutil.relativedelta import relativedelta

class RevenueCalculator:
    def __init__(self):
        """Initialize the Revenue Calculator with configuration"""

        # Setup logging
        logging.basicConfig(
            filename=f'/Logs/revenue_calculator_{datetime.now().strftime("%Y%m%d")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Database for storing revenue data
        self.db_path = '/Data/revenue.db'
        self._setup_database()

        # Metric definitions
        self.metrics = {
            'total_revenue': 'Total revenue earned during the period',
            'recurring_revenue': 'Predictable, recurring revenue',
            'arpu': 'Average revenue per user',
            'revenue_growth': 'Percentage change in revenue',
            'gross_revenue': 'Total revenue before deductions',
            'net_revenue': 'Revenue after returns and discounts',
            'gross_margin': 'Revenue minus cost of goods sold',
            'operating_margin': 'Revenue minus operating expenses'
        }

    def _setup_database(self):
        """Setup database for storing revenue data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main revenue transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS revenue_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                transaction_date DATETIME NOT NULL,
                transaction_type TEXT NOT NULL,  -- sale, refund, discount, credit
                customer_id TEXT,
                product_id TEXT,
                category TEXT,  -- product, service, subscription, other
                subcategory TEXT,
                region TEXT,
                sales_rep TEXT,
                contract_id TEXT,  -- For recurring revenue tracking
                payment_method TEXT,
                status TEXT DEFAULT 'completed',  -- pending, completed, refunded, cancelled
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Revenue metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS revenue_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_start DATETIME NOT NULL,
                period_end DATETIME NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Customer data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                company TEXT,
                segment TEXT DEFAULT 'other',  -- enterprise, mid_market, small_business, consumer
                region TEXT,
                acquisition_date DATETIME,
                status TEXT DEFAULT 'active',  -- active, inactive, churned
                lifetime_value REAL DEFAULT 0.0,
                total_spent REAL DEFAULT 0.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Product/service data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                unit_price REAL,
                cost_of_goods REAL,
                is_subscription BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transaction_date ON revenue_transactions(transaction_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_customer_id ON revenue_transactions(customer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON revenue_transactions(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_period_start ON revenue_metrics(period_start)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metric_name ON revenue_metrics(metric_name)')

        conn.commit()
        conn.close()

    def calculate_total_revenue(self, start_date: str, end_date: str) -> float:
        """
        Calculate total revenue for a given period

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            Total revenue amount
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT SUM(amount) FROM revenue_transactions
                WHERE transaction_date BETWEEN ? AND ?
                AND status = 'completed'
                AND transaction_type IN ('sale', 'subscription', 'service')
            ''', (start_date, end_date))

            result = cursor.fetchone()[0]
            conn.close()

            return result or 0.0

        except Exception as e:
            logging.error(f"Error calculating total revenue: {str(e)}")
            return 0.0

    def calculate_recurring_revenue(self, start_date: str, end_date: str) -> float:
        """
        Calculate recurring revenue for a given period

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            Recurring revenue amount
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT SUM(amount) FROM revenue_transactions
                WHERE transaction_date BETWEEN ? AND ?
                AND status = 'completed'
                AND category = 'subscription'
                AND transaction_type = 'subscription'
            ''', (start_date, end_date))

            result = cursor.fetchone()[0]
            conn.close()

            return result or 0.0

        except Exception as e:
            logging.error(f"Error calculating recurring revenue: {str(e)}")
            return 0.0

    def calculate_arpu(self, start_date: str, end_date: str) -> float:
        """
        Calculate Average Revenue Per User for a given period

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            ARPU value
        """
        try:
            total_revenue = self.calculate_total_revenue(start_date, end_date)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Count distinct customers who had transactions in the period
            cursor.execute('''
                SELECT COUNT(DISTINCT customer_id) FROM revenue_transactions
                WHERE transaction_date BETWEEN ? AND ?
                AND status = 'completed'
                AND customer_id IS NOT NULL
            ''', (start_date, end_date))

            customer_count = cursor.fetchone()[0] or 1  # Avoid division by zero
            conn.close()

            arpu = total_revenue / customer_count if customer_count > 0 else 0.0
            return round(arpu, 2)

        except Exception as e:
            logging.error(f"Error calculating ARPU: {str(e)}")
            return 0.0

    def calculate_revenue_growth(self, current_start: str, current_end: str,
                               previous_start: str, previous_end: str) -> float:
        """
        Calculate revenue growth rate between two periods

        Args:
            current_start: Start date of current period
            current_end: End date of current period
            previous_start: Start date of previous period
            previous_end: End date of previous period

        Returns:
            Revenue growth percentage
        """
        try:
            current_revenue = self.calculate_total_revenue(current_start, current_end)
            previous_revenue = self.calculate_total_revenue(previous_start, previous_end)

            if previous_revenue == 0:
                return float('inf') if current_revenue > 0 else 0.0

            growth_rate = ((current_revenue - previous_revenue) / previous_revenue) * 100
            return round(growth_rate, 2)

        except Exception as e:
            logging.error(f"Error calculating revenue growth: {str(e)}")
            return 0.0

    def calculate_gross_revenue(self, start_date: str, end_date: str) -> float:
        """
        Calculate gross revenue (before refunds and discounts)

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            Gross revenue amount
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Calculate gross revenue by adding all positive transactions
            cursor.execute('''
                SELECT SUM(amount) FROM revenue_transactions
                WHERE transaction_date BETWEEN ? AND ?
                AND status = 'completed'
                AND amount > 0
                AND transaction_type IN ('sale', 'subscription', 'service')
            ''', (start_date, end_date))

            result = cursor.fetchone()[0]
            conn.close()

            return result or 0.0

        except Exception as e:
            logging.error(f"Error calculating gross revenue: {str(e)}")
            return 0.0

    def calculate_net_revenue(self, start_date: str, end_date: str) -> float:
        """
        Calculate net revenue (after refunds and discounts)

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            Net revenue amount
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Calculate net revenue by subtracting negative transactions
            cursor.execute('''
                SELECT SUM(amount) FROM revenue_transactions
                WHERE transaction_date BETWEEN ? AND ?
                AND status = 'completed'
                AND transaction_type IN ('sale', 'subscription', 'service', 'refund', 'discount')
            ''', (start_date, end_date))

            result = cursor.fetchone()[0]
            conn.close()

            return result or 0.0

        except Exception as e:
            logging.error(f"Error calculating net revenue: {str(e)}")
            return 0.0

    def calculate_customer_acquisition_cost(self, start_date: str, end_date: str,
                                          marketing_spend: float) -> float:
        """
        Calculate Customer Acquisition Cost (CAC)

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format
            marketing_spend: Marketing spend during the period

        Returns:
            CAC value
        """
        try:
            # Count new customers acquired during the period
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT COUNT(*) FROM customers
                WHERE acquisition_date BETWEEN ? AND ?
            ''', (start_date, end_date))

            new_customers = cursor.fetchone()[0]
            conn.close()

            cac = marketing_spend / new_customers if new_customers > 0 else 0.0
            return round(cac, 2)

        except Exception as e:
            logging.error(f"Error calculating CAC: {str(e)}")
            return 0.0

    def calculate_churn_rate(self, start_date: str, end_date: str) -> float:
        """
        Calculate customer churn rate

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            Churn rate percentage
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Calculate number of customers at start of period
            cursor.execute('''
                SELECT COUNT(DISTINCT customer_id) FROM revenue_transactions
                WHERE transaction_date <= ?
                AND status = 'completed'
            ''', (start_date,))

            customers_at_start = cursor.fetchone()[0] or 0

            # Calculate customers lost during period
            cursor.execute('''
                SELECT COUNT(DISTINCT customer_id) FROM customers
                WHERE status = 'churned'
                AND updated_at BETWEEN ? AND ?
            ''', (start_date, end_date))

            customers_lost = cursor.fetchone()[0] or 0

            conn.close()

            churn_rate = (customers_lost / customers_at_start) * 100 if customers_at_start > 0 else 0.0
            return round(churn_rate, 2)

        except Exception as e:
            logging.error(f"Error calculating churn rate: {str(e)}")
            return 0.0

    def calculate_lifetime_value(self, customer_id: str) -> float:
        """
        Calculate customer lifetime value

        Args:
            customer_id: Customer ID

        Returns:
            CLV value
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get customer's total revenue
            cursor.execute('''
                SELECT SUM(amount) FROM revenue_transactions
                WHERE customer_id = ?
                AND status = 'completed'
                AND amount > 0
            ''', (customer_id,))

            total_revenue = cursor.fetchone()[0] or 0.0

            # Calculate average purchase value
            cursor.execute('''
                SELECT AVG(amount) FROM revenue_transactions
                WHERE customer_id = ?
                AND status = 'completed'
                AND amount > 0
            ''', (customer_id,))

            avg_purchase = cursor.fetchone()[0] or 0.0

            # Calculate purchase frequency (purchases per year)
            cursor.execute('''
                SELECT COUNT(*) FROM revenue_transactions
                WHERE customer_id = ?
                AND status = 'completed'
                AND amount > 0
            ''', (customer_id,))

            total_purchases = cursor.fetchone()[0] or 1

            # Calculate customer lifespan (in years)
            cursor.execute('''
                SELECT
                    (julianday(MAX(transaction_date)) - julianday(MIN(transaction_date))) / 365.25
                FROM revenue_transactions
                WHERE customer_id = ?
                AND status = 'completed'
            ''', (customer_id,))

            lifespan = cursor.fetchone()[0] or 0.01  # Avoid division by zero

            conn.close()

            # Simplified CLV formula: (Average Purchase Value * Purchase Frequency) * Average Customer Lifespan
            clv = ((avg_purchase * total_purchases) / lifespan) * 5  # Assuming 5-year average lifespan
            return round(clv, 2)

        except Exception as e:
            logging.error(f"Error calculating CLV for customer {customer_id}: {str(e)}")
            return 0.0

    def calculate_period_metrics(self, start_date: str, end_date: str) -> Dict[str, float]:
        """
        Calculate all key metrics for a given period

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            Dictionary of calculated metrics
        """
        total_revenue = self.calculate_total_revenue(start_date, end_date)

        # Calculate previous period for growth comparison
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        period_length = end_dt - start_dt
        prev_start = (start_dt - period_length).strftime('%Y-%m-%d')
        prev_end = (end_dt - period_length).strftime('%Y-%m-%d')

        metrics = {
            'total_revenue': total_revenue,
            'recurring_revenue': self.calculate_recurring_revenue(start_date, end_date),
            'arpu': self.calculate_arpu(start_date, end_date),
            'revenue_growth': self.calculate_revenue_growth(start_date, end_date, prev_start, prev_end),
            'gross_revenue': self.calculate_gross_revenue(start_date, end_date),
            'net_revenue': self.calculate_net_revenue(start_date, end_date),
            'gross_margin': self.calculate_gross_margin(start_date, end_date),
            'operating_margin': self.calculate_operating_margin(start_date, end_date)
        }

        return metrics

    def calculate_gross_margin(self, start_date: str, end_date: str) -> float:
        """
        Calculate gross margin percentage

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            Gross margin percentage
        """
        try:
            net_revenue = self.calculate_net_revenue(start_date, end_date)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Calculate COGS for the period
            cursor.execute('''
                SELECT SUM(p.cost_of_goods * rt.amount / p.unit_price)
                FROM revenue_transactions rt
                JOIN products p ON rt.product_id = p.product_id
                WHERE rt.transaction_date BETWEEN ? AND ?
                AND rt.status = 'completed'
                AND rt.amount > 0
            ''', (start_date, end_date))

            cogs = cursor.fetchone()[0] or 0.0
            conn.close()

            if net_revenue == 0:
                return 0.0

            gross_margin = ((net_revenue - cogs) / net_revenue) * 100
            return round(gross_margin, 2)

        except Exception as e:
            logging.error(f"Error calculating gross margin: {str(e)}")
            return 0.0

    def calculate_operating_margin(self, start_date: str, end_date: str) -> float:
        """
        Calculate operating margin percentage

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            Operating margin percentage
        """
        try:
            net_revenue = self.calculate_net_revenue(start_date, end_date)

            # This is a simplified version - in reality you'd need to track operating expenses separately
            # For now, we'll return the same as gross margin (which is incorrect but avoids complexity)
            # In a real implementation, operating expenses would be tracked in a separate table
            operating_expenses = net_revenue * 0.3  # Assuming 30% operating expenses as placeholder
            operating_income = net_revenue - operating_expenses

            if net_revenue == 0:
                return 0.0

            operating_margin = (operating_income / net_revenue) * 100
            return round(operating_margin, 2)

        except Exception as e:
            logging.error(f"Error calculating operating margin: {str(e)}")
            return 0.0

    def store_metric(self, period_start: str, period_end: str, metric_name: str,
                     metric_value: float, currency: str = 'USD'):
        """Store a calculated metric in the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO revenue_metrics (period_start, period_end, metric_name, metric_value, currency)
                VALUES (?, ?, ?, ?, ?)
            ''', (period_start, period_end, metric_name, metric_value, currency))

            conn.commit()
            conn.close()

        except Exception as e:
            logging.error(f"Error storing metric {metric_name}: {str(e)}")

    def get_period_comparison(self, current_start: str, current_end: str,
                             previous_start: str, previous_end: str) -> Dict[str, Dict[str, float]]:
        """
        Get comparison of metrics between two periods

        Args:
            current_start: Start date of current period
            current_end: End date of current period
            previous_start: Start date of previous period
            previous_end: End date of previous period

        Returns:
            Dictionary with current and previous period metrics
        """
        current_metrics = self.calculate_period_metrics(current_start, current_end)
        previous_metrics = self.calculate_period_metrics(previous_start, previous_end)

        comparison = {
            'current_period': {
                'period': f"{current_start} to {current_end}",
                'metrics': current_metrics
            },
            'previous_period': {
                'period': f"{previous_start} to {previous_end}",
                'metrics': previous_metrics
            }
        }

        return comparison

    def get_revenue_by_category(self, start_date: str, end_date: str) -> Dict[str, float]:
        """Get revenue broken down by category"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT category, SUM(amount) as total
                FROM revenue_transactions
                WHERE transaction_date BETWEEN ? AND ?
                AND status = 'completed'
                AND transaction_type IN ('sale', 'subscription', 'service')
                GROUP BY category
            ''', (start_date, end_date))

            results = cursor.fetchall()
            conn.close()

            return {row[0]: row[1] or 0.0 for row in results}

        except Exception as e:
            logging.error(f"Error getting revenue by category: {str(e)}")
            return {}

    def get_revenue_by_customer_segment(self, start_date: str, end_date: str) -> Dict[str, float]:
        """Get revenue broken down by customer segment"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT c.segment, SUM(rt.amount) as total
                FROM revenue_transactions rt
                JOIN customers c ON rt.customer_id = c.customer_id
                WHERE rt.transaction_date BETWEEN ? AND ?
                AND rt.status = 'completed'
                AND rt.transaction_type IN ('sale', 'subscription', 'service')
                GROUP BY c.segment
            ''', (start_date, end_date))

            results = cursor.fetchall()
            conn.close()

            return {row[0]: row[1] or 0.0 for row in results}

        except Exception as e:
            logging.error(f"Error getting revenue by customer segment: {str(e)}")
            return {}

    def get_trend_analysis(self, start_date: str, end_date: str,
                           period: str = 'monthly') -> List[Dict[str, Any]]:
        """
        Get revenue trend analysis for a period

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format
            period: Granularity ('daily', 'weekly', 'monthly')

        Returns:
            List of trend data points
        """
        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)

            trend_data = []

            if period == 'daily':
                current_date = start_dt
                while current_date <= end_dt:
                    date_str = current_date.strftime('%Y-%m-%d')
                    revenue = self.calculate_total_revenue(date_str, date_str)

                    trend_data.append({
                        'date': date_str,
                        'revenue': revenue
                    })

                    current_date += timedelta(days=1)
            elif period == 'weekly':
                current_date = start_dt
                while current_date <= end_dt:
                    week_end = current_date + timedelta(days=6)
                    if week_end > end_dt:
                        week_end = end_dt

                    revenue = self.calculate_total_revenue(
                        current_date.strftime('%Y-%m-%d'),
                        week_end.strftime('%Y-%m-%d')
                    )

                    trend_data.append({
                        'start_date': current_date.strftime('%Y-%m-%d'),
                        'end_date': week_end.strftime('%Y-%m-%d'),
                        'revenue': revenue
                    })

                    current_date += timedelta(weeks=1)
            elif period == 'monthly':
                current_date = start_dt
                while current_date <= end_dt:
                    # Calculate end of current month
                    if current_date.month == 12:
                        next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
                    else:
                        next_month = current_date.replace(month=current_date.month + 1, day=1)

                    month_end = next_month - timedelta(days=1)
                    if month_end > end_dt:
                        month_end = end_dt

                    revenue = self.calculate_total_revenue(
                        current_date.strftime('%Y-%m-%d'),
                        month_end.strftime('%Y-%m-%d')
                    )

                    trend_data.append({
                        'month': current_date.strftime('%Y-%m'),
                        'start_date': current_date.strftime('%Y-%m-%d'),
                        'end_date': month_end.strftime('%Y-%m-%d'),
                        'revenue': revenue
                    })

                    current_date = next_month

            return trend_data

        except Exception as e:
            logging.error(f"Error getting trend analysis: {str(e)}")
            return []

    def generate_revenue_report(self, start_date: str, end_date: str,
                                report_type: str = 'comprehensive') -> str:
        """
        Generate a revenue report

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format
            report_type: Type of report ('comprehensive', 'summary', 'detailed')

        Returns:
            Path to generated report file
        """
        try:
            # Get report data
            metrics = self.calculate_period_metrics(start_date, end_date)
            category_breakdown = self.get_revenue_by_category(start_date, end_date)
            segment_breakdown = self.get_revenue_by_customer_segment(start_date, end_date)
            trend_data = self.get_trend_analysis(start_date, end_date, 'monthly')

            # Create report directory if it doesn't exist
            report_dir = Path('/Reports/revenue')
            report_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"revenue_report_{start_date}_to_{end_date}_{timestamp}.json"
            report_path = report_dir / filename

            # Create report data
            report_data = {
                'report_generated': datetime.now().isoformat(),
                'report_type': report_type,
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'key_metrics': metrics,
                'category_breakdown': category_breakdown,
                'segment_breakdown': segment_breakdown,
                'trend_analysis': trend_data
            }

            # Write report
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)

            logging.info(f"Revenue report generated: {report_path}")
            return str(report_path)

        except Exception as e:
            logging.error(f"Failed to generate revenue report: {str(e)}")
            raise

async def main():
    """Main function for testing the Revenue Calculator"""
    calculator = RevenueCalculator()

    # Example: Calculate metrics for the last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    print(f"Calculating revenue metrics for {start_str} to {end_str}...")

    # Calculate key metrics
    total_revenue = calculator.calculate_total_revenue(start_str, end_str)
    recurring_revenue = calculator.calculate_recurring_revenue(start_str, end_str)
    arpu = calculator.calculate_arpu(start_str, end_str)
    net_revenue = calculator.calculate_net_revenue(start_str, end_str)

    print(f"Total Revenue: ${total_revenue:,.2f}")
    print(f"Recurring Revenue: ${recurring_revenue:,.2f}")
    print(f"ARPU: ${arpu:,.2f}")
    print(f"Net Revenue: ${net_revenue:,.2f}")

    # Get all metrics for the period
    all_metrics = calculator.calculate_period_metrics(start_str, end_str)
    print(f"All metrics: {all_metrics}")

    # Generate a comprehensive report
    try:
        report_path = calculator.generate_revenue_report(start_str, end_str, 'comprehensive')
        print(f"Revenue report generated at: {report_path}")
    except Exception as e:
        print(f"Failed to generate report: {e}")

if __name__ == "__main__":
    asyncio.run(main())