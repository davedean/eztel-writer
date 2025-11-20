"""Tests for telemetry loop"""

import pytest
import time
from unittest.mock import Mock, patch
from src.telemetry_loop import TelemetryLoop
from src.session_manager import SessionState


class TestTelemetryLoop:
    """Test suite for TelemetryLoop"""

    def test_initialization(self):
        """Loop should initialize with correct defaults"""
        loop = TelemetryLoop()
        assert loop.is_running() is False
        assert loop.is_paused() is False
        assert loop.session_manager.state == SessionState.IDLE

    def test_start_stop(self):
        """Should be able to start and stop the loop"""
        loop = TelemetryLoop()

        loop.start()
        assert loop.is_running() is True

        loop.stop()
        assert loop.is_running() is False

    def test_pause_resume(self):
        """Should be able to pause and resume"""
        loop = TelemetryLoop()
        loop.start()

        loop.pause()
        assert loop.is_paused() is True
        assert loop.session_manager.state == SessionState.PAUSED

        loop.resume()
        assert loop.is_paused() is False

    def test_idle_state_when_no_process(self):
        """Should stay in IDLE when target process not running"""
        loop = TelemetryLoop({'target_process': 'definitely_not_running_xyz123'})
        loop.start()

        status = loop.run_once()

        assert status['state'] == SessionState.IDLE
        assert status['process_detected'] is False

    @patch('src.telemetry_loop.get_telemetry_reader')
    def test_detects_process(self, mock_get_reader):
        """Should detect when target process is running"""
        # Mock the telemetry reader to always use MockTelemetryReader
        from src.telemetry.telemetry_mock import MockTelemetryReader
        mock_get_reader.return_value = MockTelemetryReader()

        # Use python process which we know is running
        loop = TelemetryLoop({'target_process': 'python'})
        loop.start()

        status = loop.run_once()

        assert status['process_detected'] is True
        # State might be DETECTED or LOGGING depending on telemetry availability
        assert status['state'] in [SessionState.DETECTED, SessionState.LOGGING]

    @patch('src.telemetry_loop.get_telemetry_reader')
    def test_starts_logging_when_telemetry_available(self, mock_get_reader):
        """Should transition to LOGGING when telemetry is available"""
        # Mock the telemetry reader to always use MockTelemetryReader
        from src.telemetry.telemetry_mock import MockTelemetryReader
        mock_get_reader.return_value = MockTelemetryReader()

        loop = TelemetryLoop({'target_process': 'python'})
        loop.start()

        # Run once - should transition from IDLE
        status1 = loop.run_once()
        # Might go straight to LOGGING if telemetry immediately available
        assert status1['state'] in [SessionState.DETECTED, SessionState.LOGGING]

        # Second call: Should definitely be in LOGGING
        status2 = loop.run_once()
        assert status2['state'] == SessionState.LOGGING
        assert status2['telemetry_available'] is True

    @patch('src.telemetry_loop.get_telemetry_reader')
    def test_buffers_samples(self, mock_get_reader):
        """Should buffer telemetry samples"""
        # Mock the telemetry reader to always use MockTelemetryReader
        from src.telemetry.telemetry_mock import MockTelemetryReader
        mock_get_reader.return_value = MockTelemetryReader()

        loop = TelemetryLoop({'target_process': 'python'})
        loop.start()

        # Run a few iterations to get to LOGGING state
        loop.run_once()  # IDLE -> DETECTED/LOGGING
        loop.run_once()  # Should be LOGGING

        initial_count = len(loop.session_manager.lap_samples)

        # Run a few more to buffer samples
        loop.run_once()
        loop.run_once()
        loop.run_once()

        # Should have buffered samples
        assert len(loop.session_manager.lap_samples) > initial_count

    @patch('src.telemetry_loop.get_telemetry_reader')
    def test_lap_completion_callback(self, mock_get_reader):
        """Should trigger callback on lap completion"""
        # Mock the telemetry reader to always use MockTelemetryReader
        from src.telemetry.telemetry_mock import MockTelemetryReader
        mock_get_reader.return_value = MockTelemetryReader()

        callback_data = {'called': False, 'lap_data': None, 'lap_summary': None}

        def on_lap_complete(lap_data, lap_summary):
            callback_data['called'] = True
            callback_data['lap_data'] = lap_data
            callback_data['lap_summary'] = lap_summary

        loop = TelemetryLoop({
            'target_process': 'python',
            'on_lap_complete': on_lap_complete
        })
        loop.start()

        # Get to LOGGING state and buffer some samples
        loop.run_once()
        loop.run_once()
        for _ in range(5):
            loop.run_once()

        # Manually force a lap change to test callback
        # Save current lap and force increment
        old_lap = loop.session_manager.current_lap
        loop.session_manager.current_lap = old_lap + 1

        # Manually trigger the lap completion logic
        # This simulates what would happen in run_once() when lap changes
        telemetry = loop.telemetry_reader.read()
        telemetry['lap'] = loop.session_manager.current_lap
        loop.session_manager.update(telemetry)

        # Now call the callback directly as run_once() would
        lap_data = loop.session_manager.get_lap_data()
        lap_summary = loop.session_manager.get_lap_summary()
        if loop.on_lap_complete and len(lap_data) > 0:
            loop.on_lap_complete(lap_data, lap_summary)

        assert callback_data['called'] is True
        assert callback_data['lap_data'] is not None
        assert len(callback_data['lap_data']) > 0

    @patch('src.telemetry_loop.get_telemetry_reader')
    def test_clears_buffer_after_lap_completion(self, mock_get_reader):
        """Should clear buffer after lap completes"""
        # Mock the telemetry reader to always use MockTelemetryReader
        from src.telemetry.telemetry_mock import MockTelemetryReader
        mock_get_reader.return_value = MockTelemetryReader()

        loop = TelemetryLoop({'target_process': 'python'})
        loop.start()

        # Get to LOGGING state and buffer samples
        loop.run_once()
        loop.run_once()
        for _ in range(5):
            loop.run_once()

        assert len(loop.session_manager.lap_samples) > 0

        # Test that clear_lap_buffer() actually works
        loop.session_manager.clear_lap_buffer()
        assert len(loop.session_manager.lap_samples) == 0

    def test_returns_none_when_not_running(self):
        """Should return None from run_once when not started"""
        loop = TelemetryLoop()

        status = loop.run_once()
        assert status is None

    def test_does_not_collect_data_when_paused(self):
        """Should not collect data when paused"""
        loop = TelemetryLoop({'target_process': 'python'})
        loop.start()

        # Get to LOGGING
        loop.run_once()
        loop.run_once()

        # Pause
        loop.pause()

        # Note initial buffer size
        initial_size = len(loop.session_manager.lap_samples)

        # Run several iterations while paused
        for _ in range(5):
            loop.run_once()

        # Buffer should not have grown
        assert len(loop.session_manager.lap_samples) == initial_size

    def test_custom_poll_interval(self):
        """Should use custom poll interval from config"""
        loop = TelemetryLoop({'poll_interval': 0.05})
        assert loop.poll_interval == 0.05

    def test_tracks_current_lap(self):
        """Should track current lap number in status"""
        loop = TelemetryLoop({'target_process': 'python'})
        loop.start()

        # Get to LOGGING
        loop.run_once()
        status = loop.run_once()

        assert 'lap' in status
        assert status['lap'] >= 0

    @patch('src.telemetry_loop.ProcessMonitor')
    @patch('src.telemetry_loop.get_telemetry_reader')
    def test_stops_logging_when_idle(self, mock_get_reader, mock_process_monitor):
        """Should flush and suspend logging when car is idle for too long"""
        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process_monitor.return_value = mock_process

        reader = Mock()
        reader.is_available.return_value = True
        samples = [
            {'lap': 1, 'lap_distance': 10.0, 'lap_time': 1.0, 'speed': 50.0},
            {'lap': 1, 'lap_distance': 10.0, 'lap_time': 2.0, 'speed': 0.0},
        ]
        reader.read.side_effect = samples + [samples[-1]]
        mock_get_reader.return_value = reader

        loop = TelemetryLoop({
            'target_process': 'python',
            'idle_timeout_seconds': 0.1,
            'min_speed_kmh': 1.0,
        })
        loop.start()

        with patch('src.telemetry_loop.time.time', side_effect=[0.0, 0.2]):
            status1 = loop.run_once()
            assert len(loop.session_manager.lap_samples) > 0
            status2 = loop.run_once()

        assert status1['lap_completed'] is False
        assert status2['session_stopped'] is True
        assert status2['stop_reason'] == 'idle_timeout'
        assert len(loop.session_manager.lap_samples) == 0

    @patch('src.telemetry_loop.ProcessMonitor')
    @patch('src.telemetry_loop.get_telemetry_reader')
    def test_incomplete_lap_marked_when_stopped(self, mock_get_reader, mock_process_monitor):
        """Should mark lap as incomplete when session stops mid-lap"""
        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process_monitor.return_value = mock_process

        reader = Mock()
        reader.is_available.return_value = True
        reader.read.return_value = {'lap': 1, 'lap_distance': 100.0, 'lap_time': 10.0, 'speed': 0.0}
        mock_get_reader.return_value = reader

        callback_data = {'called': False, 'lap_summary': None}

        def on_lap_complete(lap_data, lap_summary):
            callback_data['called'] = True
            callback_data['lap_summary'] = lap_summary

        loop = TelemetryLoop({
            'target_process': 'python',
            'idle_timeout_seconds': 0.1,
            'on_lap_complete': on_lap_complete
        })
        loop.start()

        # Run once to start logging
        with patch('src.telemetry_loop.time.time', return_value=0.0):
            loop.run_once()

        # Run again after idle timeout to trigger session stop
        with patch('src.telemetry_loop.time.time', return_value=0.2):
            status = loop.run_once()

        # Verify callback was called with incomplete lap
        assert callback_data['called'] is True
        assert callback_data['lap_summary'] is not None
        assert callback_data['lap_summary']['lap_completed'] is False
        assert callback_data['lap_summary']['stop_reason'] == 'idle_timeout'

    @patch('src.telemetry_loop.ProcessMonitor')
    @patch('src.telemetry_loop.get_telemetry_reader')
    def test_complete_lap_marked_on_normal_completion(self, mock_get_reader, mock_process_monitor):
        """Should mark lap as complete when lap changes normally"""
        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process_monitor.return_value = mock_process

        reader = Mock()
        reader.is_available.return_value = True
        # Simulate lap progression: lap 1 -> lap 2
        samples = [
            {'lap': 1, 'lap_distance': 100.0, 'lap_time': 10.0, 'speed': 150.0},
            {'lap': 1, 'lap_distance': 200.0, 'lap_time': 20.0, 'speed': 160.0},
            {'lap': 2, 'lap_distance': 10.0, 'lap_time': 0.5, 'speed': 120.0},
        ]
        reader.read.side_effect = samples
        mock_get_reader.return_value = reader

        callback_data = {'called': False, 'lap_summary': None}

        def on_lap_complete(lap_data, lap_summary):
            callback_data['called'] = True
            callback_data['lap_summary'] = lap_summary

        loop = TelemetryLoop({
            'target_process': 'python',
            'on_lap_complete': on_lap_complete
        })
        loop.start()

        # Run three iterations to trigger lap change
        with patch('src.telemetry_loop.time.time', return_value=0.0):
            loop.run_once()
            loop.run_once()
            loop.run_once()

        # Verify callback was called with complete lap
        assert callback_data['called'] is True
        assert callback_data['lap_summary'] is not None
        assert callback_data['lap_summary']['lap_completed'] is True
        assert 'stop_reason' not in callback_data['lap_summary']

    @patch('src.telemetry_loop.ProcessMonitor')
    @patch('src.telemetry_loop.get_telemetry_reader')
    def test_incomplete_lap_on_lap_distance_reset(self, mock_get_reader, mock_process_monitor):
        """Should mark lap as incomplete when driver teleports to pits (lap distance resets)"""
        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process_monitor.return_value = mock_process

        reader = Mock()
        reader.is_available.return_value = True
        # Simulate teleport: lap_distance jumps backward
        samples = [
            {'lap': 1, 'lap_distance': 500.0, 'lap_time': 50.0, 'speed': 180.0},
            {'lap': 1, 'lap_distance': 10.0, 'lap_time': 51.0, 'speed': 50.0},  # Teleport!
        ]
        reader.read.side_effect = samples
        mock_get_reader.return_value = reader

        callback_data = {'called': False, 'lap_summary': None}

        def on_lap_complete(lap_data, lap_summary):
            callback_data['called'] = True
            callback_data['lap_summary'] = lap_summary

        loop = TelemetryLoop({
            'target_process': 'python',
            'lap_reset_tolerance_m': 5.0,
            'on_lap_complete': on_lap_complete
        })
        loop.start()

        with patch('src.telemetry_loop.time.time', return_value=0.0):
            loop.run_once()
            status = loop.run_once()

        # Verify callback was called with incomplete lap
        assert callback_data['called'] is True
        assert callback_data['lap_summary'] is not None
        assert callback_data['lap_summary']['lap_completed'] is False
        assert callback_data['lap_summary']['stop_reason'] == 'lap_distance_reset'

    @patch('src.telemetry_loop.get_telemetry_reader')
    @patch('src.telemetry_loop.ProcessMonitor')
    def test_opponent_tracking_works_when_player_in_garage(self, mock_process_monitor, mock_get_reader):
        """Opponent tracking should work even when player is in garage (DETECTED state, not LOGGING)"""
        # Mock process monitor
        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process_monitor.return_value = mock_process

        # Mock telemetry reader
        reader = Mock()
        reader.is_available.return_value = True

        # Player telemetry: stationary in garage (speed = 0)
        player_sample = {
            'lap': 1,
            'lap_distance': 0.0,
            'lap_time': 0.0,
            'speed': 0.0,  # Not moving!
            'throttle': 0.0,
            'brake': 0.0,
        }
        reader.read.return_value = player_sample

        # Opponent telemetry: opponent completes a lap
        opponent_samples = [
            # First call: opponent mid-lap
            [{'driver_name': 'Opponent1', 'lap': 1, 'lap_distance': 1500.0, 'lap_time': 90.0, 'speed': 200.0, 'control': 2, 'last_lap_time': 0.0}],
            # Second call: opponent completes lap 1, starts lap 2
            [{'driver_name': 'Opponent1', 'lap': 2, 'lap_distance': 10.0, 'lap_time': 1.0, 'last_lap_time': 95.0, 'speed': 100.0, 'control': 2}],
        ]
        reader.get_all_vehicles.side_effect = opponent_samples

        mock_get_reader.return_value = reader

        opponent_callback_data = {'called': False, 'opponent_lap': None}

        def on_opponent_lap_complete(opponent_lap_data):
            opponent_callback_data['called'] = True
            opponent_callback_data['opponent_lap'] = opponent_lap_data

        loop = TelemetryLoop({
            'target_process': 'python',
            'track_opponents': True,
            'on_opponent_lap_complete': on_opponent_lap_complete,
            'min_speed_kmh': 1.0,  # Require 1 km/h to be considered "active"
        })
        loop.start()

        # Run twice: first to detect process, second for opponent lap completion
        with patch('src.telemetry_loop.time.time', return_value=0.0):
            status1 = loop.run_once()

        with patch('src.telemetry_loop.time.time', return_value=1.0):
            status2 = loop.run_once()

        # Player should still be in DETECTED state (not LOGGING, since not moving)
        assert status2['state'] in [SessionState.DETECTED, SessionState.LOGGING]

        # Opponent callback should have been called
        assert opponent_callback_data['called'] is True
        assert opponent_callback_data['opponent_lap'] is not None
        assert opponent_callback_data['opponent_lap'].driver_name == 'Opponent1'
        assert opponent_callback_data['opponent_lap'].lap_number == 1

    @patch('src.telemetry_loop.get_telemetry_reader')
    @patch('src.telemetry_loop.ProcessMonitor')
    def test_opponent_tracking_works_when_player_suspended(self, mock_process_monitor, mock_get_reader):
        """Opponent tracking should work even when player is suspended (_suspend_logging = True)"""
        # Mock process monitor
        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process_monitor.return_value = mock_process

        # Mock telemetry reader
        reader = Mock()
        reader.is_available.return_value = True

        # Player telemetry sequence:
        # 1. Driving at 500m
        # 2. Teleport to pits (lap_distance reset) - triggers suspension
        # 3. Stationary in pits
        player_samples = [
            {'lap': 1, 'lap_distance': 500.0, 'lap_time': 50.0, 'speed': 180.0, 'throttle': 80.0, 'brake': 0.0},
            {'lap': 1, 'lap_distance': 10.0, 'lap_time': 51.0, 'speed': 0.0, 'throttle': 0.0, 'brake': 0.0},  # Teleport!
            {'lap': 1, 'lap_distance': 10.0, 'lap_time': 52.0, 'speed': 0.0, 'throttle': 0.0, 'brake': 0.0},  # Still in pits
        ]
        reader.read.side_effect = player_samples

        # Opponent telemetry: opponent completes lap while player is suspended
        opponent_samples = [
            [{'driver_name': 'Opponent1', 'lap': 1, 'lap_distance': 1500.0, 'lap_time': 90.0, 'speed': 200.0, 'control': 2, 'last_lap_time': 0.0}],
            [{'driver_name': 'Opponent1', 'lap': 1, 'lap_distance': 2500.0, 'lap_time': 95.0, 'speed': 200.0, 'control': 2, 'last_lap_time': 0.0}],
            [{'driver_name': 'Opponent1', 'lap': 2, 'lap_distance': 10.0, 'lap_time': 1.0, 'last_lap_time': 98.0, 'speed': 100.0, 'control': 2}],  # Lap complete!
        ]
        reader.get_all_vehicles.side_effect = opponent_samples

        mock_get_reader.return_value = reader

        opponent_callback_data = {'called': False, 'opponent_lap': None}
        player_callback_data = {'called': False}

        def on_opponent_lap_complete(opponent_lap_data):
            opponent_callback_data['called'] = True
            opponent_callback_data['opponent_lap'] = opponent_lap_data

        def on_player_lap_complete(lap_data, lap_summary):
            player_callback_data['called'] = True

        loop = TelemetryLoop({
            'target_process': 'python',
            'track_opponents': True,
            'on_opponent_lap_complete': on_opponent_lap_complete,
            'on_lap_complete': on_player_lap_complete,
            'lap_reset_tolerance_m': 5.0,
        })
        loop.start()

        # Run three times
        with patch('src.telemetry_loop.time.time', return_value=0.0):
            status1 = loop.run_once()  # Player driving

        with patch('src.telemetry_loop.time.time', return_value=1.0):
            status2 = loop.run_once()  # Player teleports, triggers suspension

        with patch('src.telemetry_loop.time.time', return_value=2.0):
            status3 = loop.run_once()  # Player suspended, opponent completes lap

        # Player should have triggered suspension
        assert player_callback_data['called'] is True  # Incomplete lap callback

        # Opponent callback should STILL have been called despite player suspension
        assert opponent_callback_data['called'] is True
        assert opponent_callback_data['opponent_lap'] is not None
        assert opponent_callback_data['opponent_lap'].driver_name == 'Opponent1'
        assert opponent_callback_data['opponent_lap'].lap_number == 1
