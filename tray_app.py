#!/usr/bin/env python3
"""
System Tray Application for LMU Telemetry Logger

This application runs the telemetry logger with a system tray icon instead
of as a command-line application.

Features:
- System tray icon with state indicators (gray/yellow/green)
- Right-click menu for Start/Stop, Pause/Resume, Open Folder, Quit
- Runs silently in background
- Auto-detects LMU and logs telemetry

Usage:
    python tray_app.py              # Run with saved settings
    python tray_app.py --settings   # Open settings dialog first

On macOS: Will use mock telemetry and detect python process
On Windows: Will use real LMU telemetry
"""

import time
import sys
import os
import argparse
import threading
import logging
from datetime import datetime
from src.telemetry_loop import TelemetryLoop
from src.csv_formatter import CSVFormatter
from src.file_manager import FileManager
from src.mvp_format import build_metadata_block, detect_sector_boundaries
from src.telemetry.telemetry_interface import get_telemetry_reader
from src.settings_ui import SettingsConfig, show_settings_dialog
from src.tray_ui import TrayUI
from src.session_manager import SessionState
from src.update_manager import UpdateManager
from src.app_paths import get_log_file_path, get_config_file_path, migrate_config_if_needed


def setup_logging():
    """
    Configure logging to write to file instead of console

    Creates telemetry_logger.log in user's app data directory with:
    - INFO level and above
    - Timestamps for each log entry
    - Both file and console output (console only if not running as .exe)

    Location:
    - Windows: %LOCALAPPDATA%\\LMU Telemetry Logger\\telemetry_logger.log
    - macOS: ~/Library/Application Support/LMU Telemetry Logger/telemetry_logger.log
    - Linux: ~/.local/share/lmu-telemetry-logger/telemetry_logger.log
    """
    log_file = get_log_file_path()

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, mode='a', encoding='utf-8'),
            # Also output to console when running as script (for development)
            logging.StreamHandler(sys.stdout) if not getattr(sys, 'frozen', False) else logging.NullHandler()
        ]
    )

    return log_file


# Configure logging at module level
LOG_FILE_PATH = setup_logging()
logger = logging.getLogger(__name__)


class TrayTelemetryApp:
    """
    Main application with system tray UI

    This wraps the telemetry loop and integrates it with the tray UI,
    running the loop in a background thread while the tray runs in the main thread.
    """

    def __init__(self, config_file='config.json'):
        """
        Initialize tray application

        Args:
            config_file: Path to config JSON file
        """
        # Load configuration
        settings = SettingsConfig(config_file)
        self.config = settings.get_all()

        # If target_process not set, use platform default
        if not self.config.get('target_process'):
            self.config['target_process'] = 'Le Mans Ultimate' if sys.platform == 'win32' else 'python'

        # Initialize components
        self.csv_formatter = CSVFormatter()
        self.file_manager = FileManager({'output_dir': self.config['output_dir']})
        self.telemetry_reader = get_telemetry_reader()

        # Initialize telemetry loop with lap completion callback
        self.telemetry_loop = TelemetryLoop({
            'target_process': self.config['target_process'],
            'poll_interval': self.config['poll_interval'],
            'on_lap_complete': self.on_lap_complete,
            'on_opponent_lap_complete': self.on_opponent_lap_complete,
            'track_opponents': self.config.get('track_opponents', True),
            'track_opponent_ai': self.config.get('track_opponent_ai', False),
        })

        # Track statistics
        self.laps_saved = 0
        self.opponent_laps_saved = 0
        self.samples_collected = 0

        # Initialize tray UI
        self.tray_ui = TrayUI(self)

        # Background thread for telemetry loop
        self.telemetry_thread = None
        self.running = False

        # Initialize update manager
        update_config = {
            'check_on_startup': self.config.get('check_updates_on_startup', True),
            'skipped_versions': self.config.get('skipped_update_versions', [])
        }
        self.update_manager = UpdateManager(update_config)

        # Check for updates on startup (non-blocking)
        if self.update_manager.should_check_for_updates():
            self.update_manager.check_for_updates_async(self.on_update_checked)

    def on_lap_complete(self, lap_data, lap_summary):
        """
        Callback when a lap is completed

        Args:
            lap_data: List of telemetry samples for the lap
            lap_summary: Summary data (lap time, sectors, etc.)
        """
        # Check if lap was completed normally (not interrupted/incomplete)
        lap_completed = lap_summary.get('lap_completed', True)
        stop_reason = lap_summary.get('stop_reason')

        if not lap_completed:
            # Discard incomplete laps
            logger.info(f"Lap {lap_summary['lap']} incomplete ({stop_reason}) - discarding")
            return

        logger.info(f"Lap {lap_summary['lap']} completed: {lap_summary.get('lap_time', 0.0):.3f}s")

        # Get session info
        session_info = self.telemetry_reader.get_session_info()
        session_info['session_id'] = self.telemetry_loop.session_manager.current_session_id

        # Enrich with REST API data if available
        if hasattr(self.telemetry_reader, 'rest_api') and self.telemetry_reader.rest_api:
            if hasattr(self.telemetry_reader, 'ensure_rest_api_data'):
                self.telemetry_reader.ensure_rest_api_data()

            car_name = session_info.get('car_name')
            if car_name:
                vehicle_meta = self.telemetry_reader.rest_api.lookup_vehicle(car_name)
                if vehicle_meta:
                    session_info['car_model'] = vehicle_meta.get('car_model', '')
                    session_info['manufacturer'] = vehicle_meta.get('manufacturer', '')
                    session_info['car_class'] = vehicle_meta.get('class', '')
                    session_info['team_name'] = vehicle_meta.get('team', '')

        # Detect sector boundaries
        track_length = session_info.get('track_length', 0.0)
        if track_length > 0 and lap_data:
            sector_boundaries, num_sectors = detect_sector_boundaries(lap_data, track_length)
            session_info['sector_boundaries'] = sector_boundaries
            session_info['num_sectors'] = num_sectors

        metadata = build_metadata_block(session_info, lap_data)

        # Format as CSV
        csv_content = self.csv_formatter.format_lap(
            lap_data=lap_data,
            metadata=metadata,
        )

        # Save to file
        try:
            filepath = self.file_manager.save_lap(
                csv_content=csv_content,
                lap_summary=lap_summary,
                session_info=session_info
            )

            self.laps_saved += 1
            self.samples_collected += len(lap_data)

            logger.info(f"Saved to: {filepath}")

        except Exception as e:
            logger.error(f"Error saving lap: {e}")

    def on_opponent_lap_complete(self, opponent_lap_data):
        """
        Callback when an opponent completes a lap

        Args:
            opponent_lap_data: OpponentLapData with driver name, lap time, samples, etc.
        """
        from src.opponent_tracker import OpponentLapData

        logger.info(f"Opponent lap: {opponent_lap_data.driver_name} - {opponent_lap_data.lap_time:.3f}s")

        # Validate lap time
        MIN_LAP_TIME = 30.0
        if opponent_lap_data.lap_time < MIN_LAP_TIME:
            return

        # Validate samples count
        MIN_SAMPLES = 10
        if len(opponent_lap_data.samples) < MIN_SAMPLES:
            return

        # Build session info
        session_info = {
            'player_name': opponent_lap_data.driver_name,
            'car_name': opponent_lap_data.car_name or 'Unknown',
            'car_model': opponent_lap_data.car_model or 'Unknown',
            'team_name': opponent_lap_data.team_name or 'Unknown',
            'manufacturer': opponent_lap_data.manufacturer or 'Unknown',
            'car_class': opponent_lap_data.car_class or 'Unknown',
            'track_name': self._get_track_name(),
            'session_type': self._get_session_type(),
            'game_version': '1.0',
            'date': datetime.now(),
            'track_length': self._get_track_length(),
            'session_id': self.telemetry_loop.session_manager.current_session_id,
        }

        # Detect sector boundaries
        track_length = session_info.get('track_length', 0.0)
        if track_length > 0 and opponent_lap_data.samples:
            sector_boundaries, num_sectors = detect_sector_boundaries(opponent_lap_data.samples, track_length)
            session_info['sector_boundaries'] = sector_boundaries
            session_info['num_sectors'] = num_sectors

        metadata = build_metadata_block(session_info, opponent_lap_data.samples)

        # Format as CSV
        csv_content = self.csv_formatter.format_lap(
            lap_data=opponent_lap_data.samples,
            metadata=metadata,
        )

        # Save to file
        try:
            lap_summary = {
                'lap': opponent_lap_data.lap_number,
                'lap_time': opponent_lap_data.lap_time,
            }

            opponent_filename_format = '{session_id}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv'

            filepath = self.file_manager.save_lap(
                csv_content=csv_content,
                lap_summary=lap_summary,
                session_info=session_info,
                filename_format=opponent_filename_format
            )

            self.opponent_laps_saved += 1
            logger.info(f"Saved opponent lap to: {filepath}")

        except Exception as e:
            logger.error(f"Error saving opponent lap: {e}")

    def _get_track_name(self) -> str:
        """Get current track name from session info"""
        info = self.telemetry_reader.get_session_info()
        return info.get('track_name', 'Unknown Track')

    def _get_session_type(self) -> str:
        """Get current session type from session info"""
        info = self.telemetry_reader.get_session_info()
        return info.get('session_type', 'Practice')

    def _get_track_length(self) -> float:
        """Get current track length from session info"""
        info = self.telemetry_reader.get_session_info()
        return info.get('track_length', 0.0)

    def run_telemetry_loop(self):
        """
        Run telemetry loop in background thread

        This method runs the telemetry loop and periodically updates the tray UI status.
        """
        self.telemetry_loop.start()

        status_update_interval = 1.0  # Update tray every second
        last_status_update = time.time()

        while self.running and self.telemetry_loop.is_running():
            # Run one iteration
            status = self.telemetry_loop.run_once()

            # Update tray UI status periodically
            now = time.time()
            if now - last_status_update >= status_update_interval:
                if status:
                    state = status.get('state', SessionState.IDLE)
                    lap = status.get('lap', 0)
                    samples = status.get('samples_buffered', 0)
                    self.tray_ui.update_status(state, lap, samples)
                last_status_update = now

            # Sleep for poll interval
            time.sleep(self.config['poll_interval'])

    def on_update_checked(self, update_info):
        """
        Callback when update check completes

        Args:
            update_info: Update information dict or None if check failed
        """
        if update_info and update_info.get('available'):
            logger.info(f"Update available: {update_info['latest_version']}")
            # Handle update in main thread if tray is available
            if hasattr(self, 'tray_ui') and self.tray_ui:
                # Show notification
                self.update_manager.show_notification(
                    self.tray_ui.icon if hasattr(self.tray_ui, 'icon') else None,
                    update_info['latest_version']
                )

    def check_for_updates_manual(self):
        """Manually check for updates (called from menu)"""
        logger.info("Checking for updates...")

        def on_checked(update_info):
            if update_info is None:
                logger.info("Could not check for updates (network error)")
            elif update_info.get('available'):
                logger.info(f"Update available: {update_info['latest_version']}")
                # Show dialog
                self.update_manager.handle_update_available(update_info)
            else:
                logger.info("Already using the latest version")

        self.update_manager.check_for_updates_async(on_checked)

    def start(self):
        """Start the application with system tray UI"""
        logger.info("=" * 60)
        logger.info("LMU Telemetry Logger - System Tray Application")
        logger.info("=" * 60)
        logger.info(f"Target process: {self.config['target_process']}")
        logger.info(f"Output directory: {self.config['output_dir']}")
        logger.info(f"Poll rate: ~{1.0 / self.config['poll_interval']:.0f}Hz")
        logger.info(f"Log file: {LOG_FILE_PATH}")
        logger.info("Starting system tray icon...")
        logger.info("Right-click icon for menu (Start/Stop, Pause/Resume, etc.)")

        self.running = True

        # Start telemetry loop in background thread
        self.telemetry_thread = threading.Thread(
            target=self.run_telemetry_loop,
            daemon=True  # Thread will exit when main thread exits
        )
        self.telemetry_thread.start()

        # Run tray UI in main thread (required by pystray)
        try:
            self.tray_ui.start()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.stop()

    def stop(self):
        """Stop the application"""
        self.running = False
        self.telemetry_loop.stop()

        # Wait for telemetry thread to finish
        if self.telemetry_thread and self.telemetry_thread.is_alive():
            self.telemetry_thread.join(timeout=2.0)

        logger.info("=" * 60)
        logger.info("Session Summary")
        logger.info("=" * 60)
        logger.info(f"Player laps saved: {self.laps_saved}")
        logger.info(f"Opponent laps saved: {self.opponent_laps_saved}")
        logger.info(f"Samples collected: {self.samples_collected}")
        logger.info(f"Output directory: {self.file_manager.get_output_directory()}")
        logger.info("Goodbye!")


def main():
    """Main entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='LMU Telemetry Logger - System Tray Application',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s              # Run with saved settings
  %(prog)s --settings   # Open settings dialog first
        """
    )
    parser.add_argument(
        '--settings',
        action='store_true',
        help='Open settings dialog before starting'
    )
    parser.add_argument(
        '--config',
        default=None,
        help='Path to config file (default: platform-specific app data directory)'
    )

    args = parser.parse_args()

    # Migrate config from old location if needed
    migrate_config_if_needed()

    # Use platform-appropriate config path if not specified
    config_path = args.config if args.config else str(get_config_file_path())

    # Show settings dialog if requested
    if args.settings:
        logger.info("Opening settings dialog...")
        saved = show_settings_dialog(config_path)
        if not saved:
            logger.info("Settings cancelled. Exiting.")
            sys.exit(0)
        logger.info("Settings saved!")

    # Start application
    app = TrayTelemetryApp(config_file=config_path)
    app.start()


if __name__ == '__main__':
    main()
