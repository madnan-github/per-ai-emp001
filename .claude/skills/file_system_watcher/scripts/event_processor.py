#!/usr/bin/env python3
"""
File System Event Processor - Processes file system events based on defined rules

This script processes file system events according to the rules and patterns
defined in the configuration files, implementing the logic for filtering,
prioritizing, and taking appropriate actions based on the event characteristics.
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class FileEventProcessor:
    """Processes file system events according to configured rules"""

    def __init__(self, config_path: str = None):
        self.config = self.load_config(config_path)
        self.event_handlers = {
            'critical': self.handle_critical_event,
            'high': self.handle_high_priority_event,
            'medium': self.handle_medium_priority_event,
            'low': self.handle_low_priority_event
        }

    def load_config(self, config_path: str = None) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'critical_patterns': [
                r'.*\.(exe|bat|scr|pif|com|vbs|js|jse|wsf|msi|msp|dll|sys)$',
                r'.*(malware|virus|trojan|ransom|crypt|encrypt).*',
                r'.*(password|credential|auth|security).*\.(txt|cfg|conf|ini|log)$',
                r'.*\.tmp\..*',  # Suspicious temp files with extensions
            ],
            'high_priority_patterns': [
                r'.*\.(pdf|doc|docx|xlsx|xls|csv)$',
                r'.*(finance|bank|payment|invoice|tax|payroll).*',
                r'.*(confidential|private|secret|classified).*',
                r'.*\.(pem|key|cer|crt|p12|pfx)$',  # Certificate/key files
            ],
            'medium_priority_patterns': [
                r'.*\.(txt|rtf|odt|ppt|pptx|odp)$',
                r'.*(project|plan|schedule|agenda).*',
                r'.*\.(zip|rar|7z|tar|gz)$',  # Archives
            ],
            'low_priority_patterns': [
                r'.*\.(tmp|temp)$',
                r'.*\.(log)$',
                r'.*(cache|thumbnail).*',
            ],
            'whitelist_extensions': [],
            'blacklist_extensions': ['.scr', '.pif', '.com', '.vbs', '.js', '.jse', '.wsf'],
            'size_thresholds': {
                'small': 1024,          # < 1KB
                'medium': 1048576,      # < 1MB
                'large': 104857600,     # < 100MB
                'huge': 1073741824      # > 1GB
            },
            'time_windows': {
                'business_hours_start': 9,   # 9 AM
                'business_hours_end': 17,    # 5 PM
                'weekend_filter': False,
                'holiday_filter': []
            }
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    for key, value in loaded_config.items():
                        if isinstance(value, dict) and key in default_config:
                            default_config[key].update(value)
                        else:
                            default_config[key] = value
            except Exception as e:
                print(f"Warning: Could not load config {config_path}: {e}")

        return default_config

    def classify_event(self, file_path: str) -> Tuple[str, int]:
        """
        Classify an event based on file path and name patterns
        Returns (priority_level, numeric_priority)
        """
        path_obj = Path(file_path)
        extension = path_obj.suffix.lower()
        file_name = path_obj.name.lower()
        file_content = path_obj.stem.lower()

        # Check for critical patterns first
        for pattern in self.config['critical_patterns']:
            if re.search(pattern, file_path.lower()):
                return 'critical', 1

        # Check for high priority patterns
        for pattern in self.config['high_priority_patterns']:
            if re.search(pattern, file_path.lower()):
                return 'high', 2

        # Check for medium priority patterns
        for pattern in self.config['medium_priority_patterns']:
            if re.search(pattern, file_path.lower()):
                return 'medium', 3

        # Check for low priority patterns
        for pattern in self.config['low_priority_patterns']:
            if re.search(pattern, file_path.lower()):
                return 'low', 4

        # Default to low priority
        return 'low', 4

    def should_process_event(self, file_path: str, event_type: str = 'created') -> bool:
        """Determine if an event should be processed based on filters"""
        path_obj = Path(file_path)
        extension = path_obj.suffix.lower()

        # Check blacklist extensions
        if extension in self.config['blacklist_extensions']:
            print(f"File {file_path} blocked by blacklist extension: {extension}")
            return False

        # Check whitelist extensions (if specified)
        if self.config['whitelist_extensions'] and extension not in self.config['whitelist_extensions']:
            print(f"File {file_path} not in whitelist extensions: {extension}")
            return False

        # Check for critical patterns regardless of other filters
        for pattern in self.config['critical_patterns']:
            if re.search(pattern, file_path.lower()):
                return True  # Critical files should always be processed

        # Apply time-based filters
        if not self.is_valid_time():
            # Only process critical events outside business hours
            for pattern in self.config['critical_patterns']:
                if re.search(pattern, file_path.lower()):
                    return True
            return False

        return True

    def is_valid_time(self) -> bool:
        """Check if the current time is within acceptable processing windows"""
        now = datetime.now()

        # Check weekend filter
        if self.config['time_windows']['weekend_filter'] and now.weekday() >= 5:
            return False

        # Check business hours
        current_hour = now.hour
        start_hour = self.config['time_windows']['business_hours_start']
        end_hour = self.config['time_windows']['business_hours_end']

        if not (start_hour <= current_hour < end_hour):
            return False

        # Check holiday filter (simplified)
        # In a real implementation, you'd check against actual holiday dates
        return True

    def get_file_metadata(self, file_path: str) -> Dict:
        """Extract metadata from the file"""
        metadata = {
            'path': file_path,
            'name': os.path.basename(file_path),
            'extension': os.path.splitext(file_path)[1],
            'size': 0,
            'created': None,
            'modified': None,
            'is_executable': False,
            'is_archive': False,
            'is_document': False,
            'is_image': False,
            'is_video': False,
            'is_audio': False,
            'is_code': False,
            'is_config': False,
            'is_encrypted': False,
            'contains_keywords': []
        }

        try:
            stat_info = os.stat(file_path)
            metadata['size'] = stat_info.st_size
            metadata['created'] = datetime.fromtimestamp(stat_info.st_ctime).isoformat()
            metadata['modified'] = datetime.fromtimestamp(stat_info.st_mtime).isoformat()

            # Determine file type based on extension
            ext = metadata['extension'].lower()

            if ext in ['.exe', '.bat', '.sh', '.app']:
                metadata['is_executable'] = True
            elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2']:
                metadata['is_archive'] = True
            elif ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf']:
                metadata['is_document'] = True
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.tiff']:
                metadata['is_image'] = True
            elif ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']:
                metadata['is_video'] = True
            elif ext in ['.mp3', '.wav', '.aac', '.flac', '.ogg']:
                metadata['is_audio'] = True
            elif ext in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs', '.go', '.rs', '.php', '.html', '.css']:
                metadata['is_code'] = True
            elif ext in ['.json', '.yml', '.yaml', '.xml', '.ini', '.cfg', '.conf', '.env']:
                metadata['is_config'] = True

            # Check for encryption indicators in filename
            if any(keyword in metadata['name'].lower() for keyword in ['encrypt', 'locked', 'ransom', 'decrypt']):
                metadata['is_encrypted'] = True

            # Look for specific keywords in the file path
            path_lower = file_path.lower()
            for keyword in ['password', 'credential', 'auth', 'secret', 'key', 'token', 'api', 'private']:
                if keyword in path_lower:
                    metadata['contains_keywords'].append(keyword)

        except Exception as e:
            print(f"Error getting metadata for {file_path}: {e}")

        return metadata

    def analyze_file_content(self, file_path: str) -> Dict:
        """Perform basic content analysis of the file"""
        analysis = {
            'has_executables': False,
            'has_suspicious_strings': [],
            'has_personal_info': [],
            'file_encoding': 'unknown',
            'is_binary': False
        }

        try:
            # Determine if file is binary
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                if b'\x00' in chunk:
                    analysis['is_binary'] = True
                else:
                    try:
                        chunk.decode('utf-8')
                        analysis['file_encoding'] = 'utf-8'
                    except UnicodeDecodeError:
                        analysis['file_encoding'] = 'binary'

            # Only analyze text files
            if not analysis['is_binary']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(10240)  # Read first 10KB for analysis
                    content_lower = content.lower()

                    # Check for suspicious strings
                    suspicious_patterns = [
                        r'eval\s*\(',  # eval() calls
                        r'exec\s*\(',  # exec() calls
                        r'import\s+os',  # os imports
                        r'import\s+subprocess',  # subprocess imports
                        r'import\s+sys',  # sys imports in unexpected contexts
                        r'open\s*\([^)]*("|\')[>&]{1,2}',  # Redirection attempts
                    ]

                    for pattern in suspicious_patterns:
                        if re.search(pattern, content_lower):
                            analysis['has_suspicious_strings'].append(pattern)

                    # Check for personal information
                    personal_patterns = [
                        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
                        r'\b\d{16}\b',  # Credit card (basic)
                        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
                    ]

                    for pattern in personal_patterns:
                        matches = re.findall(pattern, content)
                        if matches:
                            analysis['has_personal_info'].extend(matches[:5])  # Limit to first 5 matches

        except Exception as e:
            print(f"Error analyzing content of {file_path}: {e}")

        return analysis

    def handle_critical_event(self, file_path: str, metadata: Dict, analysis: Dict):
        """Handle critical priority events"""
        print(f"🚨 CRITICAL EVENT: Processing {file_path}")

        # Actions for critical events
        actions_taken = []

        # Check if file is suspicious executable
        if metadata['is_executable'] or analysis['has_suspicious_strings']:
            actions_taken.append("File flagged as potentially malicious")
            # In a real implementation, this might quarantine the file
            print(f"  - File {file_path} flagged as potentially malicious")

        # Check for personal information exposure
        if analysis['has_personal_info']:
            actions_taken.append("Personal information detected")
            print(f"  - Personal information detected in {file_path}: {analysis['has_personal_info'][:3]}...")

        # Log the critical event
        self.log_event('critical', file_path, actions_taken)

    def handle_high_priority_event(self, file_path: str, metadata: Dict, analysis: Dict):
        """Handle high priority events"""
        print(f"⚠️ HIGH PRIORITY: Processing {file_path}")

        # Actions for high priority events
        actions_taken = []

        # Log the high priority event
        self.log_event('high', file_path, actions_taken)

    def handle_medium_priority_event(self, file_path: str, metadata: Dict, analysis: Dict):
        """Handle medium priority events"""
        print(f"📝 MEDIUM PRIORITY: Processing {file_path}")

        # Actions for medium priority events
        actions_taken = []

        # Log the medium priority event
        self.log_event('medium', file_path, actions_taken)

    def handle_low_priority_event(self, file_path: str, metadata: Dict, analysis: Dict):
        """Handle low priority events"""
        print(f"✅ LOW PRIORITY: Processing {file_path}")

        # Actions for low priority events
        actions_taken = []

        # Log the low priority event
        self.log_event('low', file_path, actions_taken)

    def log_event(self, priority: str, file_path: str, actions: List[str]):
        """Log the event to console and/or file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = {
            'timestamp': timestamp,
            'priority': priority,
            'file_path': file_path,
            'actions_taken': actions
        }

        # Print to console
        print(f"[{timestamp}] {priority.upper()} EVENT LOGGED: {file_path}")

        # In a real implementation, you might save to a log file or database
        # For now, we'll just print the log entry
        print(f"  - Log entry: {log_entry}")

    def process_event(self, file_path: str, event_type: str = 'created'):
        """Process a single file system event"""
        if not self.should_process_event(file_path, event_type):
            print(f"Skipping event for {file_path} - filtered by rules")
            return

        # Classify the event
        priority_level, priority_num = self.classify_event(file_path)

        # Get file metadata
        metadata = self.get_file_metadata(file_path)

        # Analyze file content (for text files)
        analysis = self.analyze_file_content(file_path)

        # Handle the event based on its priority
        handler = self.event_handlers.get(priority_level, self.handle_low_priority_event)
        handler(file_path, metadata, analysis)

    def process_event_batch(self, file_paths: List[str], event_type: str = 'created'):
        """Process a batch of file system events"""
        results = []

        for file_path in file_paths:
            try:
                result = self.process_event(file_path, event_type)
                results.append(result)
            except Exception as e:
                print(f"Error processing event for {file_path}: {e}")
                results.append(None)

        return results


def main():
    """Main entry point for the event processor"""
    import argparse

    parser = argparse.ArgumentParser(description="File System Event Processor")
    parser.add_argument('files', nargs='*', help='Files to process')
    parser.add_argument('--config', '-c', help='Path to configuration file')
    parser.add_argument('--event-type', '-t', default='created',
                       choices=['created', 'modified', 'deleted', 'renamed'],
                       help='Type of event to simulate')

    args = parser.parse_args()

    # Initialize processor
    processor = FileEventProcessor(args.config)

    if args.files:
        # Process specified files
        for file_path in args.files:
            if os.path.exists(file_path):
                print(f"Processing: {file_path}")
                processor.process_event(file_path, args.event_type)
            else:
                print(f"File does not exist: {file_path}")
    else:
        # Interactive mode - wait for file paths from stdin
        print("File System Event Processor - Enter file paths to process (Ctrl+C to exit):")
        try:
            while True:
                file_path = input("Enter file path: ").strip()
                if file_path:
                    if os.path.exists(file_path):
                        processor.process_event(file_path, args.event_type)
                    else:
                        print(f"File does not exist: {file_path}")
        except KeyboardInterrupt:
            print("\nExiting...")


if __name__ == "__main__":
    main()