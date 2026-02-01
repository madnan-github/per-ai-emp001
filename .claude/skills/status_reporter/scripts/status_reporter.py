#!/usr/bin/env python3
"""
StatusReporter: Generates regular status reports for projects, teams, and business metrics.

This module provides automated status reporting capabilities with customizable
templates, distribution options, and integration with various data sources.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import base64


class ReportType(Enum):
    """Types of status reports."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    PROJECT = "project"
    TEAM = "team"
    BUSINESS = "business"


class ReportFormat(Enum):
    """Formats for status reports."""
    EMAIL = "email"
    PDF = "pdf"
    HTML = "html"
    CSV = "csv"
    JSON = "json"


@dataclass
class StatusReport:
    """Represents a status report."""
    id: str
    title: str
    report_type: ReportType
    period_start: datetime
    period_end: datetime
    created_at: datetime = field(default_factory=datetime.now)
    content: str = ""
    recipients: List[str] = field(default_factory=list)
    status: str = "draft"  # draft, pending, sent, failed
    format_type: ReportFormat = ReportFormat.EMAIL
    metadata: Dict[str, Any] = field(default_factory=dict)
    charts: List[str] = field(default_factory=list)  # Base64 encoded chart images


@dataclass
class ReportTemplate:
    """Represents a report template."""
    id: str
    name: str
    report_type: ReportType
    content_template: str
    variables: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True


class StatusReporter:
    """
    Automated status reporting system with customizable templates and distribution options.

    Features:
    - Multiple report types (daily, weekly, monthly, project, team, business)
    - Customizable templates with variable substitution
    - Multi-format output (email, PDF, HTML, CSV, JSON)
    - Automated distribution to configured recipients
    - Chart and visualization capabilities
    - Historical report tracking and comparison
    """

    def __init__(self, db_path: str = "./reports.db", smtp_config: Optional[Dict[str, Any]] = None):
        self.db_path = db_path
        self.smtp_config = smtp_config or {}
        self.setup_database()

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('status_reporter.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_database(self):
        """Initialize the database schema for report tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                report_type TEXT,
                period_start DATETIME,
                period_end DATETIME,
                created_at DATETIME,
                content TEXT,
                recipients_json TEXT,
                status TEXT,
                format_type TEXT,
                metadata_json TEXT,
                charts_json TEXT
            )
        ''')

        # Create templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                report_type TEXT,
                content_template TEXT,
                variables_json TEXT,
                created_at DATETIME,
                is_active BOOLEAN
            )
        ''')

        # Create metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT,
                metric_name TEXT,
                metric_value REAL,
                unit TEXT,
                recorded_at DATETIME,
                FOREIGN KEY (report_id) REFERENCES reports (id)
            )
        ''')

        # Create distribution_log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS distribution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT,
                recipient TEXT,
                status TEXT,
                sent_at DATETIME,
                error_message TEXT,
                FOREIGN KEY (report_id) REFERENCES reports (id)
            )
        ''')

        conn.commit()
        conn.close()

    def create_report(self, title: str, report_type: ReportType, period_start: datetime,
                     period_end: datetime, recipients: List[str],
                     content: str = "", format_type: ReportFormat = ReportFormat.EMAIL,
                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new status report."""
        report = StatusReport(
            id=str(uuid4()),
            title=title,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            recipients=recipients,
            content=content,
            format_type=format_type,
            metadata=metadata or {},
            status="draft"
        )

        self._save_report_to_db(report)
        self.logger.info(f"Created report '{title}' (ID: {report.id})")
        return report.id

    def _save_report_to_db(self, report: StatusReport) -> None:
        """Save report to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO reports
            (id, title, report_type, period_start, period_end, created_at,
             content, recipients_json, status, format_type, metadata_json, charts_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report.id, report.title, report.report_type.value,
            report.period_start.isoformat(), report.period_end.isoformat(),
            report.created_at.isoformat(), report.content,
            json.dumps(report.recipients), report.status, report.format_type.value,
            json.dumps(report.metadata), json.dumps(report.charts)
        ))

        conn.commit()
        conn.close()

    def generate_report_content(self, report_id: str, template_id: Optional[str] = None,
                              variables: Optional[Dict[str, Any]] = None) -> str:
        """Generate report content using a template and variables."""
        report = self.get_report(report_id)
        if not report:
            raise ValueError(f"Report with ID {report_id} not found")

        # Use provided template or find a default template for this report type
        if template_id:
            template = self.get_template(template_id)
        else:
            template = self.get_default_template(report.report_type)

        if not template:
            raise ValueError(f"No template found for report type {report.report_type.value}")

        # Prepare template variables
        default_vars = {
            'title': report.title,
            'report_type': report.report_type.value,
            'period_start': report.period_start.strftime("%B %d, %Y"),
            'period_end': report.period_end.strftime("%B %d, %Y"),
            'current_date': datetime.now().strftime("%B %d, %Y"),
            'duration_days': (report.period_end - report.period_start).days
        }

        # Merge provided variables with defaults (provided variables take precedence)
        all_vars = {**default_vars, **(variables or {})}

        # Replace template variables
        content = template.content_template
        for var_name, var_value in all_vars.items():
            placeholder = f"{{{{{var_name}}}}}"
            content = content.replace(placeholder, str(var_value))

        # Add any dynamic content based on report type
        content = self._add_dynamic_content(content, report, all_vars)

        report.content = content
        report.status = "pending"  # Ready for distribution

        self._save_report_to_db(report)
        self.logger.info(f"Generated content for report '{report.title}' (ID: {report.id})")
        return content

    def _add_dynamic_content(self, content: str, report: StatusReport, variables: Dict[str, Any]) -> str:
        """Add dynamic content based on report type and variables."""
        # Add metrics if they exist
        metrics = self.get_report_metrics(report.id)
        if metrics:
            metrics_section = "\n## Key Metrics\n"
            for metric in metrics:
                metrics_section += f"- {metric['name']}: {metric['value']} {metric['unit']}\n"
            content += metrics_section

        # Add charts if they exist
        if report.charts:
            content += "\n## Charts\n"
            for i, chart_base64 in enumerate(report.charts):
                content += f"<img src=\"data:image/png;base64,{chart_base64}\" alt=\"Chart {i+1}\">\n"

        # Customize based on report type
        if report.report_type == ReportType.DAILY:
            content += f"\n## Tomorrow's Priorities\n{variables.get('next_priorities', 'To be determined')}\n"
            content += f"## Blockers\n{variables.get('blockers', 'None identified')}\n"

        elif report.report_type == ReportType.WEEKLY:
            content += f"\n## This Week's Accomplishments\n{variables.get('accomplishments', 'None reported')}\n"
            content += f"## Next Week's Focus\n{variables.get('next_focus', 'To be planned')}\n"

        elif report.report_type == ReportType.PROJECT:
            content += f"\n## Milestone Progress\n{variables.get('milestone_progress', 'Not specified')}\n"
            content += f"## Resource Allocation\n{variables.get('resources', 'Not specified')}\n"

        elif report.report_type == ReportType.BUSINESS:
            content += f"\n## Financial Summary\n{variables.get('financial_summary', 'Not specified')}\n"
            content += f"## Market Insights\n{variables.get('market_insights', 'Not specified')}\n"

        return content

    def create_template(self, name: str, report_type: ReportType, content_template: str,
                       variables: List[str]) -> str:
        """Create a new report template."""
        template = ReportTemplate(
            id=str(uuid4()),
            name=name,
            report_type=report_type,
            content_template=content_template,
            variables=variables
        )

        self._save_template_to_db(template)
        self.logger.info(f"Created template '{name}' for report type {report_type.value}")
        return template.id

    def _save_template_to_db(self, template: ReportTemplate) -> None:
        """Save template to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO templates
            (id, name, report_type, content_template, variables_json, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            template.id, template.name, template.report_type.value,
            template.content_template, json.dumps(template.variables),
            template.created_at.isoformat(), template.is_active
        ))

        conn.commit()
        conn.close()

    def get_template(self, template_id: str) -> Optional[ReportTemplate]:
        """Retrieve a template by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, report_type, content_template, variables_json, created_at, is_active
            FROM templates WHERE id = ?
        ''', (template_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return ReportTemplate(
            id=row[0], name=row[1], report_type=ReportType(row[2]),
            content_template=row[3], variables=json.loads(row[4]),
            created_at=datetime.fromisoformat(row[5]), is_active=row[6]
        )

    def get_default_template(self, report_type: ReportType) -> Optional[ReportTemplate]:
        """Get a default template for a report type."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, report_type, content_template, variables_json, created_at, is_active
            FROM templates WHERE report_type = ? AND is_active = 1
            ORDER BY created_at DESC LIMIT 1
        ''', (report_type.value,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return ReportTemplate(
            id=row[0], name=row[1], report_type=ReportType(row[2]),
            content_template=row[3], variables=json.loads(row[4]),
            created_at=datetime.fromisoformat(row[5]), is_active=row[6]
        )

    def get_report(self, report_id: str) -> Optional[StatusReport]:
        """Retrieve a report by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, title, report_type, period_start, period_end, created_at,
                   content, recipients_json, status, format_type, metadata_json, charts_json
            FROM reports WHERE id = ?
        ''', (report_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return StatusReport(
            id=row[0], title=row[1], report_type=ReportType(row[2]),
            period_start=datetime.fromisoformat(row[3]),
            period_end=datetime.fromisoformat(row[4]),
            created_at=datetime.fromisoformat(row[5]),
            content=row[6], recipients=json.loads(row[7]),
            status=row[8], format_type=ReportFormat(row[9]),
            metadata=json.loads(row[10]) if row[10] else {},
            charts=json.loads(row[11]) if row[11] else []
        )

    def distribute_report(self, report_id: str) -> bool:
        """Distribute a report to its recipients."""
        report = self.get_report(report_id)
        if not report or report.status != "pending":
            self.logger.error(f"Report {report_id} not found or not ready for distribution")
            return False

        success = True
        for recipient in report.recipients:
            try:
                if report.format_type == ReportFormat.EMAIL:
                    sent = self._send_email_report(report, recipient)
                elif report.format_type == ReportFormat.HTML:
                    sent = self._save_html_report(report, recipient)
                elif report.format_type == ReportFormat.PDF:
                    sent = self._save_pdf_report(report, recipient)
                elif report.format_type == ReportFormat.CSV:
                    sent = self._save_csv_report(report, recipient)
                elif report.format_type == ReportFormat.JSON:
                    sent = self._save_json_report(report, recipient)
                else:
                    self.logger.error(f"Unsupported format: {report.format_type.value}")
                    sent = False

                # Log distribution result
                self._log_distribution_result(report_id, recipient, "sent" if sent else "failed")

                if not sent:
                    success = False
                    self.logger.error(f"Failed to distribute report to {recipient}")
            except Exception as e:
                self.logger.error(f"Error distributing report to {recipient}: {str(e)}")
                self._log_distribution_result(report_id, recipient, "failed", str(e))
                success = False

        if success:
            # Update report status to indicate it was sent
            self._update_report_status(report_id, "sent")
            self.logger.info(f"Distributed report '{report.title}' to {len(report.recipients)} recipients")
        else:
            self._update_report_status(report_id, "failed")
            self.logger.error(f"Failed to fully distribute report '{report.title}'")

        return success

    def _send_email_report(self, report: StatusReport, recipient: str) -> bool:
        """Send a report via email."""
        if not self.smtp_config:
            self.logger.error("SMTP configuration not provided")
            return False

        try:
            msg = MIMEMultipart()
            msg['Subject'] = f"Status Report: {report.title}"
            msg['From'] = self.smtp_config.get('from_email', 'noreply@example.com')
            msg['To'] = recipient

            # Create HTML content
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    h1, h2 {{ color: #333; }}
                    .section {{ margin: 20px 0; }}
                    .metric {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <h1>{report.title}</h1>
                <p><strong>Reporting Period:</strong> {report.period_start.strftime('%B %d, %Y')} to {report.period_end.strftime('%B %d, %Y')}</p>

                {report.content}

                <hr>
                <p><em>This report was automatically generated by StatusReporter</em></p>
            </body>
            </html>
            """

            msg.attach(MIMEText(html_content, 'html'))

            # Connect to server and send email
            server = smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['smtp_port'])
            server.starttls()
            server.login(self.smtp_config['username'], self.smtp_config['password'])

            server.send_message(msg)
            server.quit()

            return True
        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
            return False

    def _save_html_report(self, report: StatusReport, recipient: str) -> bool:
        """Save a report as HTML file."""
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Status Report: {report.title}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    h1, h2 {{ color: #333; }}
                    .section {{ margin: 20px 0; }}
                    .metric {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <h1>{report.title}</h1>
                <p><strong>Reporting Period:</strong> {report.period_start.strftime('%B %d, %Y')} to {report.period_end.strftime('%B %d, %Y')}</p>

                {report.content}

                <hr>
                <p><em>This report was automatically generated by StatusReporter</em></p>
            </body>
            </html>
            """

            filename = f"report_{report.id}_{report.period_start.strftime('%Y%m%d')}_{recipient.replace('@', '_at_').replace('.', '_dot_')}.html"
            filepath = os.path.join(self._get_output_dir(), filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)

            self.logger.info(f"Saved HTML report to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save HTML report: {str(e)}")
            return False

    def _save_pdf_report(self, report: StatusReport, recipient: str) -> bool:
        """Save a report as PDF file."""
        # For simplicity, we'll create a text file that could be converted to PDF
        # In a real implementation, this would use a library like ReportLab
        try:
            content = f"""
STATUS REPORT: {report.title}
Reporting Period: {report.period_start.strftime('%B %d, %Y')} to {report.period_end.strftime('%B %d, %Y')}

{report.content}

This report was automatically generated by StatusReporter
"""

            filename = f"report_{report.id}_{report.period_start.strftime('%Y%m%d')}_{recipient.replace('@', '_at_').replace('.', '_dot_')}.txt"
            filepath = os.path.join(self._get_output_dir(), filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            self.logger.info(f"Saved PDF-ready report to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save PDF report: {str(e)}")
            return False

    def _save_csv_report(self, report: StatusReport, recipient: str) -> bool:
        """Save report metrics as CSV file."""
        try:
            metrics = self.get_report_metrics(report.id)
            if not metrics:
                self.logger.warning(f"No metrics found for report {report.id}")
                return True

            import csv
            filename = f"report_metrics_{report.id}_{report.period_start.strftime('%Y%m%d')}_{recipient.replace('@', '_at_').replace('.', '_dot_')}.csv"
            filepath = os.path.join(self._get_output_dir(), filename)

            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['metric_name', 'value', 'unit', 'recorded_at']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for metric in metrics:
                    writer.writerow({
                        'metric_name': metric['name'],
                        'value': metric['value'],
                        'unit': metric['unit'],
                        'recorded_at': metric['recorded_at']
                    })

            self.logger.info(f"Saved CSV report to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save CSV report: {str(e)}")
            return False

    def _save_json_report(self, report: StatusReport, recipient: str) -> bool:
        """Save report as JSON file."""
        try:
            report_data = {
                'id': report.id,
                'title': report.title,
                'report_type': report.report_type.value,
                'period_start': report.period_start.isoformat(),
                'period_end': report.period_end.isoformat(),
                'created_at': report.created_at.isoformat(),
                'content': report.content,
                'recipients': report.recipients,
                'status': report.status,
                'format_type': report.format_type.value,
                'metadata': report.metadata,
                'charts_count': len(report.charts),
                'metrics': self.get_report_metrics(report.id)
            }

            filename = f"report_{report.id}_{report.period_start.strftime('%Y%m%d')}_{recipient.replace('@', '_at_').replace('.', '_dot_')}.json"
            filepath = os.path.join(self._get_output_dir(), filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Saved JSON report to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save JSON report: {str(e)}")
            return False

    def _get_output_dir(self) -> str:
        """Get the output directory for reports."""
        output_dir = "output_reports"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return output_dir

    def _log_distribution_result(self, report_id: str, recipient: str, status: str, error_msg: str = "") -> None:
        """Log the result of report distribution."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO distribution_log
            (report_id, recipient, status, sent_at, error_message)
            VALUES (?, ?, ?, ?, ?)
        ''', (report_id, recipient, status, datetime.now().isoformat(), error_msg))

        conn.commit()
        conn.close()

    def _update_report_status(self, report_id: str, status: str) -> None:
        """Update the status of a report."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE reports SET status = ?, updated_at = ?
            WHERE id = ?
        ''', (status, datetime.now().isoformat(), report_id))

        conn.commit()
        conn.close()

    def add_report_metric(self, report_id: str, metric_name: str, metric_value: float, unit: str = "") -> None:
        """Add a metric to a report."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO metrics
            (report_id, metric_name, metric_value, unit, recorded_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (report_id, metric_name, metric_value, unit, datetime.now().isoformat()))

        conn.commit()
        conn.close()

        self.logger.info(f"Added metric '{metric_name}' to report {report_id}")

    def get_report_metrics(self, report_id: str) -> List[Dict[str, Any]]:
        """Get metrics for a report."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT metric_name, metric_value, unit, recorded_at
            FROM metrics
            WHERE report_id = ?
            ORDER BY recorded_at DESC
        ''', (report_id,))

        metrics = []
        for row in cursor.fetchall():
            metrics.append({
                'name': row[0],
                'value': row[1],
                'unit': row[2],
                'recorded_at': row[3]
            })

        conn.close()
        return metrics

    def generate_chart(self, data: List[Tuple], title: str, chart_type: str = "line") -> str:
        """Generate a chart and return as base64 string."""
        fig, ax = plt.subplots(figsize=(10, 6))

        if chart_type == "line":
            dates, values = zip(*data)
            ax.plot(dates, values, marker='o')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        elif chart_type == "bar":
            labels, values = zip(*data)
            ax.bar(labels, values)
        elif chart_type == "pie":
            labels, values = zip(*data)
            ax.pie(values, labels=labels, autopct='%1.1f%%')

        ax.set_title(title)
        ax.grid(True)

        # Rotate x-axis labels if they're dates
        if chart_type == "line":
            plt.xticks(rotation=45)

        plt.tight_layout()

        # Save to bytes
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        plt.close(fig)

        # Convert to base64
        graphic = base64.b64encode(image_png)
        return graphic.decode('utf-8')

    def add_chart_to_report(self, report_id: str, chart_base64: str) -> None:
        """Add a chart to a report."""
        report = self.get_report(report_id)
        if not report:
            raise ValueError(f"Report with ID {report_id} not found")

        report.charts.append(chart_base64)
        self._save_report_to_db(report)

    def get_historical_reports(self, report_type: Optional[ReportType] = None,
                             days_back: int = 30) -> List[StatusReport]:
        """Get historical reports for a given period."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=days_back)

        query = "SELECT id, title, report_type, period_start, period_end, created_at, content, recipients_json, status, format_type, metadata_json, charts_json FROM reports WHERE created_at >= ?"
        params = [cutoff_date.isoformat()]

        if report_type:
            query += " AND report_type = ?"
            params.append(report_type.value)

        query += " ORDER BY created_at DESC"

        cursor.execute(query, params)

        reports = []
        for row in cursor.fetchall():
            reports.append(StatusReport(
                id=row[0], title=row[1], report_type=ReportType(row[2]),
                period_start=datetime.fromisoformat(row[3]),
                period_end=datetime.fromisoformat(row[4]),
                created_at=datetime.fromisoformat(row[5]),
                content=row[6], recipients=json.loads(row[7]),
                status=row[8], format_type=ReportFormat(row[9]),
                metadata=json.loads(row[10]) if row[10] else {},
                charts=json.loads(row[11]) if row[11] else []
            ))

        conn.close()
        return reports

    def get_distribution_stats(self, report_id: str) -> Dict[str, Any]:
        """Get distribution statistics for a report."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM distribution_log
            WHERE report_id = ?
            GROUP BY status
        ''', (report_id,))

        stats = {}
        for row in cursor.fetchall():
            stats[row[0]] = row[1]

        conn.close()
        return stats


def main():
    """Main function for running the status reporter."""
    import argparse

    parser = argparse.ArgumentParser(description='Status Reporter')
    parser.add_argument('--db-path', default='./reports.db', help='Path to database file')
    parser.add_argument('--demo', action='store_true', help='Run demonstration')

    args = parser.parse_args()

    reporter = StatusReporter(db_path=args.db_path)

    if args.demo:
        # Create some demo templates
        daily_template = """
<h2>Daily Standup Report - {{{period_start}}} to {{{period_end}}}</h2>

<h3>What I accomplished yesterday:</h3>
<ul>
<li>Task 1: {{{task_1_yesterday}}}</li>
<li>Task 2: {{{task_2_yesterday}}}</li>
</ul>

<h3>What I'm working on today:</h3>
<ul>
<li>Priority 1: {{{priority_1_today}}}</li>
<li>Priority 2: {{{priority_2_today}}}</li>
</ul>

<h3>Blockers/Challenges:</h3>
<ul>
<li>{{{blocker_1}}}</li>
<li>{{{blocker_2}}}</li>
</ul>

<p>Next priorities: {{{next_priorities}}}</p>
"""

        weekly_template = """
<h2>Weekly Status Report - {{{period_start}}} to {{{period_end}}}</h2>

<h3>Key Accomplishments:</h3>
<ul>
<li>{{{accomplishment_1}}}</li>
<li>{{{accomplishment_2}}}</li>
<li>{{{accomplishment_3}}}</li>
</ul>

<h3>Current Priorities:</h3>
<ul>
<li>{{{priority_1}}}</li>
<li>{{{priority_2}}}</li>
<li>{{{priority_3}}}</li>
</ul>

<h3>Risks & Concerns:</h3>
<ul>
<li>{{{risk_1}}}</li>
<li>{{{risk_2}}}</li>
</ul>

<h3>Next Week's Focus:</h3>
<p>{{{next_week_focus}}}</p>
"""

        # Create templates
        daily_template_id = reporter.create_template(
            name="Daily Standup",
            report_type=ReportType.DAILY,
            content_template=daily_template,
            variables=["task_1_yesterday", "task_2_yesterday", "priority_1_today", "priority_2_today",
                      "blocker_1", "blocker_2", "next_priorities"]
        )

        weekly_template_id = reporter.create_template(
            name="Weekly Status",
            report_type=ReportType.WEEKLY,
            content_template=weekly_template,
            variables=["accomplishment_1", "accomplishment_2", "accomplishment_3",
                      "priority_1", "priority_2", "priority_3", "risk_1", "risk_2", "next_week_focus"]
        )

        print(f"Created templates: Daily ({daily_template_id}), Weekly ({weekly_template_id})")

        # Create a demo report
        report_id = reporter.create_report(
            title="Week of February 1-5, 2026",
            report_type=ReportType.WEEKLY,
            period_start=datetime.now() - timedelta(days=7),
            period_end=datetime.now(),
            recipients=["manager@company.com", "team@company.com"],
            format_type=ReportFormat.EMAIL
        )

        print(f"Created report: {report_id}")

        # Generate content with variables
        content = reporter.generate_report_content(
            report_id,
            variables={
                "accomplishment_1": "Completed API integration for customer portal",
                "accomplishment_2": "Resolved critical security vulnerability",
                "accomplishment_3": "Deployed new analytics dashboard",
                "priority_1": "Finish user authentication system",
                "priority_2": "Prepare for Q1 planning session",
                "priority_3": "Review and refactor legacy code",
                "risk_1": "Potential delay in third-party API availability",
                "risk_2": "Resource constraint for upcoming sprint",
                "next_week_focus": "Focus on authentication system and sprint planning"
            }
        )

        print("Generated report content")

        # Add some metrics
        reporter.add_report_metric(report_id, "Tasks Completed", 12, "tasks")
        reporter.add_report_metric(report_id, "Bugs Resolved", 5, "bugs")
        reporter.add_report_metric(report_id, "Hours Worked", 40, "hours")

        print("Added metrics to report")

        # Generate a sample chart
        dates = [datetime.now() - timedelta(days=i) for i in range(5, -1, -1)]
        values = [10, 12, 14, 11, 15, 12]
        data_points = [(date, val) for date, val in zip(dates, values)]

        chart_base64 = reporter.generate_chart(data_points, "Weekly Task Completion", "line")
        reporter.add_chart_to_report(report_id, chart_base64)

        print("Added chart to report")

        # Print the generated content
        report = reporter.get_report(report_id)
        print("\n--- Generated Report Content ---")
        print(report.content)
        print("--- End Report Content ---")

        # Get historical reports
        historical = reporter.get_historical_reports(days_back=7)
        print(f"\nFound {len(historical)} historical reports")

    else:
        print("Status reporter initialized. Use the API to generate reports.")


if __name__ == "__main__":
    main()