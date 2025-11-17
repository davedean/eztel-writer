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
from src.telemetry.telemetry_interface import get_telemetry_reader


class TelemetryApp:
    """Main application coordinating all components"""

    def __init__(self):
        """Initialize application"""
        self.running = False

        # Configuration
        self.config = {
            'target_process': 'python',  # Use 'python' on macOS for testing
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
            'on_lap_complete': self.on_lap_complete
        })

        # Track statistics
        self.laps_saved = 0
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
        print(f"\n🏁 Lap {lap_summary['lap']} completed!")
        print(f"   Lap time: {lap_summary.get('lap_time', 0.0):.3f}s")
        print(f"   Samples: {lap_summary.get('samples_count', 0)}")

        # Get session info from telemetry reader
        session_info = self.telemetry_reader.get_session_info()
        session_info['session_id'] = self.telemetry_loop.session_manager.current_session_id

        # Format as CSV
        csv_content = self.csv_formatter.format_lap(
            lap_data=lap_data,
            lap_summary=lap_summary,
            session_info=session_info
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

            print(f"   ✅ Saved to: {filepath}")
            print(f"   Total laps saved: {self.laps_saved}")

        except Exception as e:
            print(f"   ❌ Error saving lap: {e}")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print("\n\n🛑 Shutting down gracefully...")
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
        print(f"Laps saved: {self.laps_saved}")
        print(f"Samples collected: {self.samples_collected}")
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
        print("Goodbye! 👋")
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

        print(f"[{state.value if hasattr(state, 'value') else state}] "
              f"Process: {'✓' if process_detected else '✗'} | "
              f"Telemetry: {'✓' if telemetry_available else '✗'} | "
              f"Lap: {lap} | "
              f"Samples: {samples}")


def main():
    """Main entry point"""
    app = TelemetryApp()
    app.start()


if __name__ == '__main__':
    main()
