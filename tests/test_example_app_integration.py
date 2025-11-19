"""Integration tests for example app lap filtering"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os


class TestLapFiltering:
    """Test that the application correctly filters incomplete laps"""

    def test_complete_lap_should_be_saved(self, tmp_path):
        """Complete laps (lap_completed=True) should be saved to disk"""
        # Import here to avoid issues with signal handlers
        from example_app import TelemetryApp

        # Create app with temp directory
        with patch('example_app.signal.signal'):  # Mock signal handlers
            app = TelemetryApp()
            app.config['output_dir'] = str(tmp_path)
            app.file_manager = Mock()
            app.file_manager.save_lap = Mock(return_value=str(tmp_path / 'test.csv'))

            # Simulate complete lap
            lap_data = [
                {'LapDistance [m]': 100.0, 'LapTime [s]': 10.0, 'Speed [km/h]': 150.0},
                {'LapDistance [m]': 200.0, 'LapTime [s]': 20.0, 'Speed [km/h]': 160.0},
            ]
            lap_summary = {
                'lap': 1,
                'lap_time': 75.5,
                'samples_count': 2,
                'lap_completed': True  # Complete lap
            }

            # Call the callback
            app.on_lap_complete(lap_data, lap_summary)

            # Verify file manager was called (lap was saved)
            app.file_manager.save_lap.assert_called_once()

    def test_incomplete_lap_should_not_be_saved(self, tmp_path):
        """Incomplete laps (lap_completed=False) should NOT be saved to disk"""
        from example_app import TelemetryApp

        with patch('example_app.signal.signal'):
            app = TelemetryApp()
            app.config['output_dir'] = str(tmp_path)
            app.file_manager = Mock()
            app.file_manager.save_lap = Mock(return_value=str(tmp_path / 'test.csv'))

            # Simulate incomplete lap (e.g., driver went to pits mid-lap)
            lap_data = [
                {'LapDistance [m]': 100.0, 'LapTime [s]': 10.0, 'Speed [km/h]': 150.0},
            ]
            lap_summary = {
                'lap': 1,
                'lap_time': 10.0,
                'samples_count': 1,
                'lap_completed': False,  # Incomplete lap
                'stop_reason': 'idle_timeout'
            }

            # Call the callback
            app.on_lap_complete(lap_data, lap_summary)

            # Verify file manager was NOT called (lap was discarded)
            app.file_manager.save_lap.assert_not_called()

    def test_incomplete_lap_with_lap_distance_reset(self, tmp_path):
        """Incomplete laps due to teleport should not be saved"""
        from example_app import TelemetryApp

        with patch('example_app.signal.signal'):
            app = TelemetryApp()
            app.config['output_dir'] = str(tmp_path)
            app.file_manager = Mock()
            app.file_manager.save_lap = Mock()

            lap_data = [
                {'LapDistance [m]': 500.0, 'LapTime [s]': 50.0, 'Speed [km/h]': 180.0},
            ]
            lap_summary = {
                'lap': 1,
                'lap_time': 50.0,
                'samples_count': 1,
                'lap_completed': False,
                'stop_reason': 'lap_distance_reset'
            }

            app.on_lap_complete(lap_data, lap_summary)

            # Should not save
            app.file_manager.save_lap.assert_not_called()

    def test_lap_counter_only_increments_for_complete_laps(self, tmp_path):
        """Lap counter should only increment for complete laps"""
        from example_app import TelemetryApp

        with patch('example_app.signal.signal'):
            app = TelemetryApp()
            app.config['output_dir'] = str(tmp_path)
            app.file_manager = Mock()
            app.file_manager.save_lap = Mock(return_value=str(tmp_path / 'test.csv'))

            assert app.laps_saved == 0

            # Incomplete lap
            incomplete_summary = {
                'lap': 1,
                'lap_time': 10.0,
                'samples_count': 5,
                'lap_completed': False,
                'stop_reason': 'idle_timeout'
            }
            app.on_lap_complete([{}] * 5, incomplete_summary)
            assert app.laps_saved == 0  # Counter should NOT increment

            # Complete lap
            complete_summary = {
                'lap': 2,
                'lap_time': 75.5,
                'samples_count': 100,
                'lap_completed': True
            }
            app.on_lap_complete([{}] * 100, complete_summary)
            assert app.laps_saved == 1  # Counter should increment
