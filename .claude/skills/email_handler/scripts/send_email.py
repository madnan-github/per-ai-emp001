#!/usr/bin/env python3
"""
Email Sending Module for Email Handler Skill
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import json
import logging
from datetime import datetime
import sqlite3
from typing import List, Dict, Optional

class EmailSender:
    def __init__(self):
        """Initialize the EmailSender with configuration"""
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.email_address = os.getenv('EMAIL_ADDRESS')
        self.password = os.getenv('EMAIL_PASSWORD')

        # Setup logging
        logging.basicConfig(
            filename=f'/Logs/email_sender_{datetime.now().strftime("%Y%m%d")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Database for tracking sent emails
        self.db_path = '/Data/sent_emails.db'
        self._setup_database()

    def _setup_database(self):
        """Setup database for tracking sent emails"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT NOT NULL,
                subject TEXT NOT NULL,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'sent',
                error_message TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def send_email(self,
                   to_emails: List[str],
                   subject: str,
                   body: str,
                   cc: List[str] = None,
                   bcc: List[str] = None,
                   attachments: List[str] = None) -> bool:
        """
        Send an email with the specified parameters

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body: Email body content
            cc: List of CC email addresses
            bcc: List of BCC email addresses
            attachments: List of file paths to attach

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.email_address
            message["To"] = ", ".join(to_emails)

            if cc:
                message["Cc"] = ", ".join(cc)

            # Add body to email
            message.attach(MIMEText(body, "plain"))

            # Add attachments if any
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())

                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {os.path.basename(file_path)}'
                        )
                        message.attach(part)

            # Combine all recipients
            all_recipients = to_emails.copy()
            if cc:
                all_recipients.extend(cc)
            if bcc:
                all_recipients.extend(bcc)

            # Create secure connection and send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.email_address, self.password)
                server.sendmail(self.email_address, all_recipients, message.as_string())

            # Log successful send
            self._log_email_status(to_emails, subject, "sent")
            logging.info(f"Successfully sent email to {len(all_recipients)} recipients: {subject}")
            return True

        except Exception as e:
            error_msg = str(e)
            logging.error(f"Failed to send email to {to_emails}: {error_msg}")
            self._log_email_status(to_emails, subject, "failed", error_msg)
            return False

    def _log_email_status(self, recipients: List[str], subject: str, status: str, error_msg: str = None):
        """Log email status to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for recipient in recipients:
            cursor.execute('''
                INSERT INTO sent_emails (recipient, subject, content, status, error_message)
                VALUES (?, ?, ?, ?, ?)
            ''', (recipient, subject, "", status, error_msg))

        conn.commit()
        conn.close()

    def create_draft(self, to_emails: List[str], subject: str, body: str, save_to_file: str = None) -> str:
        """
        Create an email draft without sending

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body: Email body content
            save_to_file: Optional file path to save the draft

        Returns:
            str: Draft content or file path if saved
        """
        draft_content = f"To: {', '.join(to_emails)}\n"
        draft_content += f"Subject: {subject}\n\n"
        draft_content += body

        if save_to_file:
            with open(save_to_file, 'w') as f:
                f.write(draft_content)
            logging.info(f"Draft saved to {save_to_file}")
            return save_to_file

        return draft_content

    def get_sent_email_stats(self) -> Dict[str, int]:
        """Get statistics on sent emails"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM sent_emails WHERE status = 'sent'")
        sent_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sent_emails WHERE status = 'failed'")
        failed_count = cursor.fetchone()[0]

        conn.close()

        return {
            "total_sent": sent_count,
            "total_failed": failed_count,
            "success_rate": sent_count / (sent_count + failed_count) if (sent_count + failed_count) > 0 else 0
        }

def main():
    """Main function for testing email sending"""
    sender = EmailSender()

    # Example usage
    recipients = ["test@example.com"]
    subject = "Test Email from AI Employee"
    body = "This is a test email sent by the AI Employee's Email Handler skill."

    success = sender.send_email(recipients, subject, body)
    if success:
        print("Email sent successfully!")
    else:
        print("Failed to send email.")

if __name__ == "__main__":
    main()