"""Tests for session manager"""

import pytest
from src.session_manager import SessionManager, SessionState


class TestSessionManager:
    """Test suite for SessionManager"""

    def test_initial_state_is_idle(self):
        """Session should start in IDLE state"""
        manager = SessionManager()
        assert manager.state == SessionState.IDLE

    def test_detects_lap_change(self):
        """Should detect when lap number changes"""
        manager = SessionManager()

        # First sample - lap 1
        telemetry1 = {'lap': 1, 'speed': 200.0}
        events1 = manager.update(telemetry1)
        assert 'lap_completed' not in events1  # No lap change yet

        # Second sample - still lap 1
        telemetry2 = {'lap': 1, 'speed': 210.0}
        events2 = manager.update(telemetry2)
        assert 'lap_completed' not in events2

        # Third sample - lap 2
        telemetry3 = {'lap': 2, 'speed': 150.0}
        events3 = manager.update(telemetry3)
        assert events3.get('lap_completed') is True

    def test_session_id_generation(self):
        """Should generate unique session IDs"""
        import time
        manager = SessionManager()
        id1 = manager.generate_session_id()
        time.sleep(0.001)  # Sleep 1ms to ensure different timestamp
        id2 = manager.generate_session_id()

        assert id1 != id2
        assert len(id1) > 0
        assert len(id2) > 0
        # Verify format: YYYYMMDDHHMMSS + microseconds (20 chars)
        assert len(id1) == 20
        assert id1.isdigit()

    def test_lap_buffer_management(self):
        """Should buffer telemetry samples correctly"""
        manager = SessionManager()

        sample1 = {'lap': 1, 'lap_distance': 100.0, 'lap_time': 1.0}
        sample2 = {'lap': 1, 'lap_distance': 150.0, 'lap_time': 1.5}
        sample3 = {'lap': 1, 'lap_distance': 200.0, 'lap_time': 2.0}

        manager.add_sample(sample1)
        manager.add_sample(sample2)
        manager.add_sample(sample3)

        lap_data = manager.get_lap_data()
        assert len(lap_data) == 3
        assert lap_data[0]['LapDistance [m]'] == pytest.approx(100.0)
        assert lap_data[2]['LapDistance [m]'] == pytest.approx(200.0)

    def test_clear_lap_buffer(self):
        """Should clear buffer correctly"""
        manager = SessionManager()

        manager.add_sample({'lap': 1, 'lap_distance': 50.0, 'lap_time': 0.5})
        manager.add_sample({'lap': 1, 'lap_distance': 90.0, 'lap_time': 0.9})

        assert len(manager.get_lap_data()) == 2

        manager.clear_lap_buffer()

        assert len(manager.get_lap_data()) == 0

    def test_state_transitions(self):
        """Should transition states correctly"""
        manager = SessionManager()

        assert manager.state == SessionState.IDLE

        manager.state = SessionState.DETECTED
        assert manager.state == SessionState.DETECTED

        manager.state = SessionState.LOGGING
        assert manager.state == SessionState.LOGGING

    def test_tracks_current_lap(self):
        """Should track current lap number"""
        manager = SessionManager()

        telemetry = {'lap': 5, 'lap_distance': 10.0}
        manager.update(telemetry)

        assert manager.current_lap == 5

    def test_lap_summary_uses_normalized_values(self):
        manager = SessionManager()

        manager.current_lap = 3
        manager.add_sample({'lap': 3, 'lap_distance': 10.0, 'lap_time': 1.0})
        manager.add_sample({'lap': 3, 'lap_distance': 300.0, 'lap_time': 75.4321})

        summary = manager.get_lap_summary()

        assert summary['lap'] == 3
        assert summary['lap_time'] == pytest.approx(75.4321)
        assert summary['lap_distance'] == pytest.approx(300.0)
        assert summary['samples_count'] == 2

    def test_session_stop_on_idle_timeout(self):
        manager = SessionManager(idle_timeout=0.5, min_speed_kmh=1.0)

        manager.update({'lap': 1, 'lap_distance': 10.0, 'speed': 50.0}, timestamp=0.0)
        events = manager.update(
            {'lap': 1, 'lap_distance': 10.0, 'speed': 0.0},
            timestamp=0.6,
        )

        assert events.get('session_stopped') == 'idle_timeout'

    def test_session_stop_on_lap_distance_reset(self):
        manager = SessionManager(lap_reset_tolerance=1.0)

        manager.update({'lap': 1, 'lap_distance': 100.0}, timestamp=0.0)
        events = manager.update({'lap': 1, 'lap_distance': 0.0}, timestamp=0.1)

        assert events.get('session_stopped') == 'lap_distance_reset'
