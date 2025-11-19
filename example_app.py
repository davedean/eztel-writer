#!/usr/bin/env python3
"""
Example application demonstrating the telemetry logger

This example shows how to use all components together:
1. ProcessMonitor - Detect when target process is running
2. TelemetryLoop - Poll telemetry at ~100Hz
3. SessionManager - Track laps and session state
4. CSVFormatter - Format data as CSV
5. FileManager - Save to disk

Usage:
    python example_app.py

On macOS: Will use mock telemetry and detect python process
On Windows: Will use real LMU telemetry (when implemented)
"""

import time
import signal
import sys
from src.telemetry_loop import TelemetryLoop
from src.csv_formatter import CSVFormatter
from src.file_manager import FileManager
from src.mvp_format import build_metadata_block, detect_sector_boundaries
from src.telemetry.telemetry_interface import get_telemetry_reader


class TelemetryApp:
    """Main application coordinating all components"""

    def __init__(self):
        """Initialize application"""
        self.running = False

        # Configuration
        import sys
        target_process = 'Le Mans Ultimate' if sys.platform == 'win32' else 'python'
        self.config = {
            'target_process': target_process,  # 'Le Mans Ultimate' on Windows, 'python' on other platforms
            'poll_interval': 0.01,  # 100Hz
            'output_dir': './telemetry_output',
        }

        # Initialize components
        self.csv_formatter = CSVFormatter()
        self.file_manager = FileManager({'output_dir': self.config['output_dir']})
        self.telemetry_reader = get_telemetry_reader()

        # Initialize telemetry loop with lap completion callback
        self.telemetry_loop = TelemetryLoop({
            **self.config,
            'on_lap_complete': self.on_lap_complete,
            'on_opponent_lap_complete': self.on_opponent_lap_complete,
            'track_opponents': True,  # Enable opponent tracking
            'track_opponent_ai': False,  # Only track remote players, not AI
        })

        # Track statistics
        self.laps_saved = 0
        self.opponent_laps_saved = 0
        self.samples_collected = 0

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

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
            # Discard incomplete laps (out laps, partial laps, teleports to pits, etc.)
            print(f"\n*** Lap {lap_summary['lap']} incomplete (reason: {stop_reason}) - discarding")
            print(f"    Lap time: {lap_summary.get('lap_time', 0.0):.3f}s")
            print(f"    Samples: {lap_summary.get('samples_count', 0)}")
            print(f"    [SKIPPED] Incomplete lap not saved")
            return

        print(f"\n*** Lap {lap_summary['lap']} completed!")
        print(f"    Lap time: {lap_summary.get('lap_time', 0.0):.3f}s")
        print(f"    Samples: {lap_summary.get('samples_count', 0)}")

        # Get session info from telemetry reader
        session_info = self.telemetry_reader.get_session_info()
        session_info['session_id'] = self.telemetry_loop.session_manager.current_session_id

        # Detect sector boundaries from lap data
        track_length = session_info.get('track_length', 0.0)
        if track_length > 0 and lap_data:
            sector_boundaries, num_sectors = detect_sector_boundaries(lap_data, track_length)
            session_info['sector_boundaries'] = sector_boundaries
            session_info['num_sectors'] = num_sectors
            print(f"    Sectors: {num_sectors} detected at {[f'{b:.0f}m' for b in sector_boundaries]}")

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

            print(f"    [OK] Saved to: {filepath}")
            print(f"    Total laps saved: {self.laps_saved}")

        except Exception as e:
            print(f"    [ERROR] Error saving lap: {e}")

    def on_opponent_lap_complete(self, opponent_lap_data):
        """
        Callback when an opponent completes a lap (fastest lap only)

        Args:
            opponent_lap_data: OpponentLapData with driver name, lap time, samples, etc.
        """
        from src.opponent_tracker import OpponentLapData

        print(f"\n*** Opponent lap completed: {opponent_lap_data.driver_name}")
        print(f"    Lap {opponent_lap_data.lap_number}: {opponent_lap_data.lap_time:.3f}s")
        print(f"    Position: P{opponent_lap_data.position if opponent_lap_data.position else '?'}")
        print(f"    Car: {opponent_lap_data.car_name or 'Unknown'}")
        print(f"    Samples: {len(opponent_lap_data.samples)}")
        print(f"    Fastest: {opponent_lap_data.is_fastest}")

        # Build session info specifically for opponent (don't use player's info!)
        session_info = {
            'player_name': opponent_lap_data.driver_name,
            'car_name': opponent_lap_data.car_name or 'Unknown',
            'track_name': self._get_track_name(),
            'session_type': self._get_session_type(),
            'game_version': '1.0',
            'date': datetime.now(),
            'track_length': self._get_track_length(),
            'session_id': self.telemetry_loop.session_manager.current_session_id,
        }

        # Detect sector boundaries from lap data
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

        # Save to file using same format as player laps
        try:
            # Create lap summary with opponent data
            lap_summary = {
                'lap': opponent_lap_data.lap_number,
                'lap_time': opponent_lap_data.lap_time,
            }

            # Use the standard save_lap method for consistent naming
            # Format will be: {date}_{time}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv
            filepath = self.file_manager.save_lap(
                csv_content=csv_content,
                lap_summary=lap_summary,
                session_info=session_info
            )

            self.opponent_laps_saved += 1

            print(f"    [OK] Saved to: {filepath}")
            print(f"    Total opponent laps saved: {self.opponent_laps_saved}")

        except Exception as e:
            print(f"    [ERROR] Error saving opponent lap: {e}")

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

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print("\n\nShutting down gracefully...")
        self.stop()

    def start(self):
        """Start the application"""
        print("=" * 60)
        print("LMU Telemetry Logger - Example Application")
        print("=" * 60)
        print()
        print(f"Target process: {self.config['target_process']}")
        print(f"Output directory: {self.config['output_dir']}")
        print(f"Poll rate: ~{1.0 / self.config['poll_interval']:.0f}Hz")
        print("CSV format: MVP 12-channel LMUTelemetry v2")
        print()
        print("Waiting for target process...")
        print("(Press Ctrl+C to stop)")
        print()

        self.running = True
        self.telemetry_loop.start()

        # Main loop
        last_status_time = time.time()
        status_interval = 5.0  # Print status every 5 seconds

        try:
            while self.running:
                # Run one loop iteration
                status = self.telemetry_loop.run_once()

                # Print status periodically
                now = time.time()
                if now - last_status_time >= status_interval:
                    self._print_status(status)
                    last_status_time = now

                # Sleep for poll interval
                time.sleep(self.config['poll_interval'])

        except KeyboardInterrupt:
            # Handled by signal_handler
            pass

    def stop(self):
        """Stop the application"""
        self.running = False
        self.telemetry_loop.stop()

        print()
        print("=" * 60)
        print("Session Summary")
        print("=" * 60)
        print(f"Player laps saved: {self.laps_saved}")
        print(f"Opponent laps saved: {self.opponent_laps_saved}")
        print(f"Samples collected: {self.samples_collected}")
        print(f"Opponents tracked: {self.telemetry_loop.opponent_tracker.get_opponent_count()}")
        print(f"Output directory: {self.file_manager.get_output_directory()}")
        print()

        # List saved files
        saved_files = self.file_manager.list_saved_laps()
        if saved_files:
            print("Saved files:")
            for filename in saved_files:
                print(f"  - {filename}")
        else:
            print("No laps saved")

        print()
        print("Goodbye!")
        sys.exit(0)

    def _print_status(self, status):
        """Print current status"""
        if not status:
            return

        state = status.get('state', 'UNKNOWN')
        process_detected = status.get('process_detected', False)
        telemetry_available = status.get('telemetry_available', False)
        lap = status.get('lap', 0)
        samples = status.get('samples_buffered', 0)
        opponents = status.get('opponents_tracked', 0)

        print(f"[{state.value if hasattr(state, 'value') else state}] "
              f"Process: {'YES' if process_detected else 'NO'} | "
              f"Telemetry: {'YES' if telemetry_available else 'NO'} | "
              f"Lap: {lap} | "
              f"Samples: {samples} | "
              f"Opponents: {opponents}")


def main():
    """Main entry point"""
    app = TelemetryApp()
    app.start()


if __name__ == '__main__':
    main()
