#!/usr/bin/env python3
"""
File System Watcher - Monitors file system events and triggers appropriate actions

This script implements a file system watcher that monitors specified directories
for file system events (creation, modification, deletion, etc.) and processes
them according to the configured rules and priorities.
"""

import os
import sys
import json
import time
import hashlib
import threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
except ImportError:
    print("Error: watchdog module not found. Please install with 'pip install watchdog'")
    sys.exit(1)


@dataclass
class FileEvent:
    """Represents a file system event with metadata"""
    event_type: str  # 'created', 'modified', 'deleted', 'moved'
    file_path: str
    timestamp: float
    file_size: int = 0
    file_hash: str = ""
    event_priority: int = 3  # 1=critical, 2=high, 3=medium, 4=low
    source_directory: str = ""
    is_sensitive: bool = False


class FileWatcherHandler(FileSystemEventHandler):
    """Handles file system events and queues them for processing"""

    def __init__(self, event_queue: queue.Queue, config: Dict):
        super().__init__()
        self.event_queue = event_queue
        self.config = config
        self.ignore_patterns = config.get('ignore_patterns', [])
        self.include_patterns = config.get('include_patterns', [])

    def should_process_event(self, event_path: str) -> bool:
        """Check if an event should be processed based on filters"""
        path_obj = Path(event_path)

        # Check if path matches include patterns
        if self.include_patterns:
            matched = False
            for pattern in self.include_patterns:
                if path_obj.match(pattern):
                    matched = True
                    break
            if not matched:
                return False

        # Check if path matches ignore patterns
        for pattern in self.ignore_patterns:
            if path_obj.match(pattern):
                return False

        return True

    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file"""
        if not os.path.isfile(file_path):
            return ""

        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return ""

    def get_file_size(self, file_path: str) -> int:
        """Get file size with error handling"""
        try:
            return os.path.getsize(file_path) if os.path.exists(file_path) else 0
        except OSError:
            return 0

    def determine_priority(self, event: FileSystemEvent, file_path: str) -> int:
        """Determine the priority of the event based on file type and location"""
        # Determine priority based on file path and extension
        path_obj = Path(file_path)
        extension = path_obj.suffix.lower()

        # Critical events (Priority 1)
        if any(keyword in file_path.lower() for keyword in ['malware', 'virus', 'trojan', 'ransom']):
            return 1
        if any(keyword in file_path.lower() for keyword in ['security', 'auth', 'password', 'credential']):
            return 1
        if any(ext in extension for ext in ['.exe', '.dll', '.sys', '.bat', '.scr']):
            # Executables in unusual locations get higher priority
            if any(keyword in file_path.lower() for keyword in ['downloads', 'desktop', 'temp']):
                return 2

        # High priority events (Priority 2)
        if any(keyword in file_path.lower() for keyword in ['finance', 'bank', 'payment', 'invoice', 'tax']):
            return 2
        if any(keyword in file_path.lower() for keyword in ['confidential', 'private', 'secret']):
            return 2
        if any(ext in extension for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv']):
            return 2  # Business documents

        # Medium priority events (Priority 3)
        if any(ext in extension for ext in ['.txt', '.rtf', '.odt', '.ppt', '.pptx']):
            return 3

        # Low priority events (Priority 4) - default
        return 4

    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return

        if not self.should_process_event(event.src_path):
            return

        file_size = self.get_file_size(event.src_path)
        file_hash = self.calculate_file_hash(event.src_path)
        priority = self.determine_priority(event, event.src_path)

        file_event = FileEvent(
            event_type='created',
            file_path=event.src_path,
            timestamp=time.time(),
            file_size=file_size,
            file_hash=file_hash,
            event_priority=priority,
            source_directory=os.path.dirname(event.src_path)
        )

        self.event_queue.put(file_event)

    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return

        if not self.should_process_event(event.src_path):
            return

        file_size = self.get_file_size(event.src_path)
        file_hash = self.calculate_file_hash(event.src_path)
        priority = self.determine_priority(event, event.src_path)

        file_event = FileEvent(
            event_type='modified',
            file_path=event.src_path,
            timestamp=time.time(),
            file_size=file_size,
            file_hash=file_hash,
            event_priority=priority,
            source_directory=os.path.dirname(event.src_path)
        )

        self.event_queue.put(file_event)

    def on_deleted(self, event):
        """Handle file deletion events"""
        if event.is_directory:
            return

        if not self.should_process_event(event.src_path):
            return

        priority = self.determine_priority(event, event.src_path)

        file_event = FileEvent(
            event_type='deleted',
            file_path=event.src_path,
            timestamp=time.time(),
            event_priority=priority,
            source_directory=os.path.dirname(event.src_path)
        )

        self.event_queue.put(file_event)

    def on_moved(self, event):
        """Handle file move events"""
        if event.is_directory:
            return

        # Process both source and destination if they match our criteria
        if self.should_process_event(event.src_path):
            priority = self.determine_priority(event, event.src_path)

            file_event = FileEvent(
                event_type='moved_from',
                file_path=event.src_path,
                timestamp=time.time(),
                event_priority=priority,
                source_directory=os.path.dirname(event.src_path)
            )

            self.event_queue.put(file_event)

        if self.should_process_event(event.dest_path):
            priority = self.determine_priority(event, event.dest_path)

            file_event = FileEvent(
                event_type='moved_to',
                file_path=event.dest_path,
                timestamp=time.time(),
                event_priority=priority,
                source_directory=os.path.dirname(event.dest_path)
            )

            self.event_queue.put(file_event)


class FileWatcher:
    """Main file watcher class that manages monitoring and event processing"""

    def __init__(self, config_path: str = None):
        self.config = self.load_config(config_path)
        self.event_queue = queue.Queue()
        self.observer = Observer()
        self.handler = FileWatcherHandler(self.event_queue, self.config)
        self.running = False
        self.process_thread = None

        # Initialize watched directories
        self.watched_dirs = self.config.get('watched_directories', [])

    def load_config(self, config_path: str = None) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'watched_directories': [
                os.path.expanduser('~/Downloads'),
                os.path.expanduser('~/Documents'),
                os.path.expanduser('~/Desktop')
            ],
            'ignore_patterns': [
                '*.tmp', '*.temp', '*/tmp/*', '*/cache/*', '*/.git/*', '*.log'
            ],
            'include_patterns': [
                '*.*'
            ],
            'event_batch_size': 10,
            'batch_interval': 5.0,  # seconds
            'rate_limit_per_minute': 1000,
            'enable_deduplication': True,
            'hash_history_size': 1000,
            'notification_channels': ['console'],
            'auto_actions_enabled': True
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    default_config.update(loaded_config)
            except Exception as e:
                print(f"Warning: Could not load config {config_path}: {e}")

        return default_config

    def start_monitoring(self):
        """Start the file system monitoring"""
        if self.running:
            return

        # Schedule watched directories
        for directory in self.watched_dirs:
            if os.path.isdir(directory):
                self.observer.schedule(self.handler, directory, recursive=True)
                print(f"Watching directory: {directory}")
            else:
                print(f"Warning: Directory does not exist: {directory}")

        self.observer.start()
        self.running = True

        # Start event processing thread
        self.process_thread = threading.Thread(target=self.process_events, daemon=True)
        self.process_thread.start()

        print(f"File watcher started. Watching {len(self.watched_dirs)} directories.")

    def stop_monitoring(self):
        """Stop the file system monitoring"""
        if not self.running:
            return

        self.running = False
        self.observer.stop()
        self.observer.join()

        if self.process_thread:
            self.process_thread.join(timeout=5.0)  # Wait up to 5 seconds for thread to finish

        print("File watcher stopped.")

    def process_events(self):
        """Process queued events in batches"""
        event_buffer = []
        last_batch_time = time.time()
        hash_history = {}

        while self.running:
            try:
                # Get events from queue with timeout
                try:
                    event = self.event_queue.get(timeout=1.0)
                    event_buffer.append(event)

                    # Check if we should process the batch
                    current_time = time.time()
                    time_since_last_batch = current_time - last_batch_time

                    # Process batch if it's full or enough time has passed
                    if (len(event_buffer) >= self.config['event_batch_size'] or
                        time_since_last_batch >= self.config['batch_interval']):

                        # Process the batch
                        self.handle_event_batch(event_buffer, hash_history)
                        event_buffer = []
                        last_batch_time = current_time

                except queue.Empty:
                    # Process remaining events if timeout reached
                    if event_buffer:
                        current_time = time.time()
                        if current_time - last_batch_time >= self.config['batch_interval']:
                            self.handle_event_batch(event_buffer, hash_history)
                            event_buffer = []
                            last_batch_time = current_time

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error processing events: {e}")

    def handle_event_batch(self, events: List[FileEvent], hash_history: Dict):
        """Handle a batch of events with deduplication and prioritization"""
        # Filter out duplicates if deduplication is enabled
        if self.config['enable_deduplication']:
            events = self.filter_duplicates(events, hash_history)

        # Sort events by priority (critical first)
        events.sort(key=lambda e: e.event_priority)

        # Process each event according to its priority
        for event in events:
            self.process_single_event(event)

    def filter_duplicates(self, events: List[FileEvent], hash_history: Dict) -> List[FileEvent]:
        """Filter out duplicate events based on file hash and path"""
        filtered_events = []

        for event in events:
            # Create a unique identifier for the event
            event_key = f"{event.file_path}_{event.event_type}"
            event_hash = hashlib.md5(event_key.encode()).hexdigest()

            # Check if this event has been seen recently
            if event_hash not in hash_history:
                hash_history[event_hash] = time.time()
                filtered_events.append(event)

                # Clean up old entries from hash history
                current_time = time.time()
                expired_keys = [
                    key for key, timestamp in hash_history.items()
                    if current_time - timestamp > 300  # 5 minutes
                ]
                for key in expired_keys:
                    del hash_history[key]

        return filtered_events

    def process_single_event(self, event: FileEvent):
        """Process a single file event according to its priority and type"""
        # Log the event
        self.log_event(event)

        # Take action based on priority
        if event.event_priority == 1:  # Critical
            self.handle_critical_event(event)
        elif event.event_priority == 2:  # High
            self.handle_high_priority_event(event)
        elif event.event_priority == 3:  # Medium
            self.handle_medium_priority_event(event)
        else:  # Low
            self.handle_low_priority_event(event)

    def log_event(self, event: FileEvent):
        """Log the event to console and/or file"""
        timestamp_str = datetime.fromtimestamp(event.timestamp).strftime('%Y-%m-%d %H:%M:%S')
        priority_str = {1: 'CRITICAL', 2: 'HIGH', 3: 'MEDIUM', 4: 'LOW'}.get(event.event_priority, 'UNKNOWN')

        print(f"[{timestamp_str}] [{priority_str}] {event.event_type.upper()}: {event.file_path} ({event.file_size} bytes)")

        # Additional logging could go here (to file, database, etc.)

    def handle_critical_event(self, event: FileEvent):
        """Handle critical priority events"""
        print(f"🚨 CRITICAL EVENT: {event.event_type} - {event.file_path}")

        # Take immediate action for critical events
        if self.config['auto_actions_enabled']:
            # Quarantine suspicious files
            if any(ext in event.file_path.lower() for ext in ['.exe', '.bat', '.scr']):
                self.quarantine_file(event.file_path)

            # Send immediate notification
            self.send_notification(f"Critical security event: {event.event_type} {event.file_path}", priority='critical')

    def handle_high_priority_event(self, event: FileEvent):
        """Handle high priority events"""
        print(f"⚠️ HIGH PRIORITY: {event.event_type} - {event.file_path}")

        if self.config['auto_actions_enabled']:
            # Send notification for high priority events
            self.send_notification(f"High priority event: {event.event_type} {event.file_path}", priority='high')

    def handle_medium_priority_event(self, event: FileEvent):
        """Handle medium priority events"""
        print(f"📝 MEDIUM PRIORITY: {event.event_type} - {event.file_path}")

        # Medium priority events are typically logged but not acted upon automatically
        pass

    def handle_low_priority_event(self, event: FileEvent):
        """Handle low priority events"""
        # Low priority events are just logged silently
        pass

    def quarantine_file(self, file_path: str):
        """Move suspicious file to quarantine location"""
        try:
            from pathlib import Path
            import shutil

            # Create quarantine directory if it doesn't exist
            quarantine_dir = os.path.expanduser('~/.quarantine')
            os.makedirs(quarantine_dir, exist_ok=True)

            filename = os.path.basename(file_path)
            quarantine_path = os.path.join(quarantine_dir, f"quarantine_{int(time.time())}_{filename}")

            shutil.move(file_path, quarantine_path)
            print(f"File quarantined: {file_path} -> {quarantine_path}")

            # Create incident report
            self.create_incident_report(file_path, quarantine_path)

        except Exception as e:
            print(f"Error quarantining file {file_path}: {e}")

    def create_incident_report(self, original_path: str, quarantine_path: str):
        """Create an incident report for quarantined files"""
        try:
            report_dir = os.path.expanduser('~/.incident_reports')
            os.makedirs(report_dir, exist_ok=True)

            report_path = os.path.join(report_dir, f"incident_{int(time.time())}.json")

            report_data = {
                'timestamp': datetime.now().isoformat(),
                'original_path': original_path,
                'quarantine_path': quarantine_path,
                'action_taken': 'file_quarantine',
                'severity': 'critical'
            }

            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2)

            print(f"Incident report created: {report_path}")

        except Exception as e:
            print(f"Error creating incident report: {e}")

    def send_notification(self, message: str, priority: str = 'normal'):
        """Send notification through configured channels"""
        channels = self.config.get('notification_channels', ['console'])

        for channel in channels:
            if channel == 'console':
                print(f"NOTIFICATION ({priority}): {message}")
            # Additional notification channels could be implemented here
            # (email, SMS, Slack, etc.)


def main():
    """Main entry point for the file watcher"""
    import argparse

    parser = argparse.ArgumentParser(description="File System Watcher")
    parser.add_argument('--config', '-c', help='Path to configuration file')
    parser.add_argument('--watch-dir', '-d', action='append', help='Directory to watch (can be used multiple times)')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode (no actual actions)')

    args = parser.parse_args()

    # Initialize watcher
    watcher = FileWatcher(args.config)

    # Override watched directories if specified
    if args.watch_dir:
        watcher.watched_dirs = args.watch_dir

    # Disable auto-actions in dry-run mode
    if args.dry_run:
        watcher.config['auto_actions_enabled'] = False
        print("Running in DRY RUN mode - no actions will be taken")

    try:
        print("Starting file system watcher...")
        watcher.start_monitoring()

        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nReceived interrupt signal, stopping watcher...")

    finally:
        watcher.stop_monitoring()


if __name__ == "__main__":
    main()