"""Main telemetry polling loop"""

import time
from typing import Dict, Any, Optional, Callable
from src.process_monitor import ProcessMonitor
from src.session_manager import SessionManager, SessionState
from src.telemetry.telemetry_interface import get_telemetry_reader


class TelemetryLoop:
    """
    Main telemetry polling loop that integrates all components

    Responsibilities:
    - Poll telemetry at ~100Hz
    - Monitor for target process (LMU)
    - Manage session state transitions
    - Buffer lap data
    - Trigger callbacks on lap completion
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize telemetry loop

        Args:
            config: Configuration dictionary with optional keys:
                - target_process: Process name to monitor (default: "LMU.exe")
                - poll_interval: Seconds between polls (default: 0.01 for ~100Hz)
                - on_lap_complete: Callback function(lap_data, lap_summary)
        """
        self.config = config or {}
        self.poll_interval = self.config.get('poll_interval', 0.01)

        # Initialize components
        self.process_monitor = ProcessMonitor(self.config)
        idle_timeout = float(self.config.get('idle_timeout_seconds', 5.0))
        min_speed = float(self.config.get('min_speed_kmh', 1.0))
        lap_reset_tolerance = float(self.config.get('lap_reset_tolerance_m', 5.0))
        self.session_manager = SessionManager(
            idle_timeout=idle_timeout,
            min_speed_kmh=min_speed,
            lap_reset_tolerance=lap_reset_tolerance,
        )
        self.telemetry_reader = get_telemetry_reader()
        self._min_speed_kmh = min_speed

        # Callbacks
        self.on_lap_complete = self.config.get('on_lap_complete', None)

        # Control flags
        self._running = False
        self._paused = False
        self._suspend_logging = False

    def start(self):
        """Start the telemetry loop (non-blocking)"""
        self._running = True
        self._paused = False

    def stop(self):
        """Stop the telemetry loop"""
        self._running = False

    def pause(self):
        """Pause data collection (but keep running)"""
        self._paused = True
        self.session_manager.state = SessionState.PAUSED

    def resume(self):
        """Resume data collection"""
        self._paused = False
        if self.session_manager.state == SessionState.PAUSED:
            self.session_manager.state = SessionState.LOGGING

    def is_running(self) -> bool:
        """Check if loop is running"""
        return self._running

    def is_paused(self) -> bool:
        """Check if loop is paused"""
        return self._paused

    def run_once(self) -> Optional[Dict[str, Any]]:
        """
        Run one iteration of the loop

        Returns:
            Status dictionary with keys:
                - state: Current SessionState
                - process_detected: bool
                - telemetry_available: bool
                - lap: Current lap number
                - samples_buffered: Number of samples in buffer
                - lap_completed: bool (if lap just completed)
        """
        if not self._running:
            return None

        current_time = time.time()

        status = {
            'state': self.session_manager.state,
            'process_detected': False,
            'telemetry_available': False,
            'lap': self.session_manager.current_lap,
            'samples_buffered': len(self.session_manager.lap_samples),
            'lap_completed': False,
            'session_stopped': False,
            'stop_reason': None,
        }

        # Check if target process is running
        process_running = self.process_monitor.is_running()
        status['process_detected'] = process_running

        if not process_running:
            # No process -> go to IDLE
            if self.session_manager.state != SessionState.IDLE:
                self.session_manager.state = SessionState.IDLE
                self.session_manager.clear_lap_buffer()
            self._suspend_logging = False
            return status

        # Process detected
        if self.session_manager.state == SessionState.IDLE:
            self.session_manager.state = SessionState.DETECTED

        # If paused, don't collect data
        if self._paused:
            return status

        # Check if telemetry is available
        if not self.telemetry_reader.is_available():
            status['telemetry_available'] = False
            self._suspend_logging = False
            return status

        status['telemetry_available'] = True

        # Read telemetry
        try:
            telemetry = self.telemetry_reader.read()

            # Update session and check for events
            events = self.session_manager.update(telemetry, current_time)

            # Handle lap completion
            if events.get('lap_completed'):
                status['lap_completed'] = True
                self._flush_lap()

            stop_reason = events.get('session_stopped')
            if stop_reason:
                self._flush_lap(reason=stop_reason)
                status['session_stopped'] = True
                status['stop_reason'] = stop_reason
                self._suspend_logging = True
                if self.session_manager.state == SessionState.LOGGING:
                    self.session_manager.state = SessionState.DETECTED

            if self._suspend_logging:
                if self._sample_indicates_active(telemetry):
                    self._suspend_logging = False
                else:
                    status['state'] = self.session_manager.state
                    status['lap'] = self.session_manager.current_lap
                    status['samples_buffered'] = len(self.session_manager.lap_samples)
                    return status

            if self.session_manager.state == SessionState.DETECTED:
                self.session_manager.state = SessionState.LOGGING
                self.session_manager.current_session_id = self.session_manager.generate_session_id()

            # Add sample to buffer
            self.session_manager.add_sample(telemetry)

            # Update status
            status['state'] = self.session_manager.state
            status['lap'] = self.session_manager.current_lap
            status['samples_buffered'] = len(self.session_manager.lap_samples)

        except Exception as e:
            self.session_manager.state = SessionState.ERROR
            status['state'] = SessionState.ERROR
            status['error'] = str(e)

        return status

    def run(self):
        """
        Run the telemetry loop continuously (blocking)

        This is the main loop that runs until stop() is called.
        Polls telemetry at the configured interval.
        """
        self.start()

        try:
            while self._running:
                self.run_once()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            # Graceful shutdown on Ctrl+C
            self.stop()

    def _flush_lap(self, reason: Optional[str] = None) -> bool:
        """
        Flush buffered lap samples and trigger the callback.

        Returns True if lap data was emitted.
        """
        lap_data = self.session_manager.get_lap_data()
        if not lap_data:
            self.session_manager.clear_lap_buffer()
            return False

        lap_summary = self.session_manager.get_lap_summary().copy()
        if reason:
            lap_summary['stop_reason'] = reason
            lap_summary['lap_completed'] = False
        else:
            lap_summary['lap_completed'] = True

        if self.on_lap_complete:
            self.on_lap_complete(lap_data, lap_summary)

        self.session_manager.clear_lap_buffer()
        return True

    def _sample_indicates_active(self, telemetry: Dict[str, Any]) -> bool:
        """Return True if the sample shows forward progress."""
        speed = telemetry.get('speed', telemetry.get('Speed [km/h]'))
        if speed is not None:
            try:
                if float(speed) >= self._min_speed_kmh:
                    return True
            except (TypeError, ValueError):
                pass
        return False
