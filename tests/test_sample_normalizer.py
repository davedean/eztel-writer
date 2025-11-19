"""Unit tests for the SampleNormalizer."""

import pytest

from src.mvp_format import SampleNormalizer, detect_sector_boundaries


class TestSampleNormalizer:
    def test_scales_fractional_inputs(self):
        normalizer = SampleNormalizer()
        sample = normalizer.normalize({'lap_distance': 10.0, 'lap_time': 0.5, 'throttle': 0.65, 'brake': 1.2})

        assert sample['ThrottlePercentage [%]'] == pytest.approx(65.0)
        # Brake fractional should clamp at 100
        assert sample['BrakePercentage [%]'] == 100.0

    def test_converts_steering_ratio_to_percent(self):
        normalizer = SampleNormalizer()
        sample = normalizer.normalize({'lap_distance': 0.0, 'lap_time': 0.0, 'steering': -1.25})

        assert sample['Steer [%]'] == pytest.approx(-100.0)

    def test_preserves_explicit_percentages(self):
        normalizer = SampleNormalizer()
        sample = normalizer.normalize({'lap_distance': 0.0, 'lap_time': 0.0, 'throttle': 75.5, 'brake': 3.2})

        assert sample['ThrottlePercentage [%]'] == pytest.approx(75.5)
        assert sample['BrakePercentage [%]'] == pytest.approx(3.2)

    def test_handles_missing_coordinates(self):
        normalizer = SampleNormalizer()
        sample = normalizer.normalize({'lap_distance': 0.0, 'position_x': 5.0})

        assert sample['X [m]'] == 5.0
        assert sample['Z [m]'] is None
        # Y [m] removed in v3 (elevation not needed for planar track view)

    def test_sector_estimation_uses_track_length(self):
        normalizer = SampleNormalizer()
        sample = normalizer.normalize({'lap_distance': 300.0, 'lap_time': 0.0, 'track_length': 900.0})

        assert sample['Sector [int]'] == 1

    def test_sector_uses_boundaries_when_available(self):
        """Test that sector calculation uses actual boundaries instead of equal division"""
        normalizer = SampleNormalizer()
        # Track with 3 sectors: 0-1800m, 1800-3600m, 3600-5400m
        sector_boundaries = [1800.0, 3600.0, 5400.0]

        # Test various positions
        sample1 = normalizer.normalize({
            'lap_distance': 1000.0,
            'lap_time': 0.0,
            'track_length': 5400.0,
            'sector_boundaries': sector_boundaries
        })
        assert sample1['Sector [int]'] == 0  # Before first boundary

        sample2 = normalizer.normalize({
            'lap_distance': 2500.0,
            'lap_time': 0.0,
            'track_length': 5400.0,
            'sector_boundaries': sector_boundaries
        })
        assert sample2['Sector [int]'] == 1  # Between first and second boundary

        sample3 = normalizer.normalize({
            'lap_distance': 4000.0,
            'lap_time': 0.0,
            'track_length': 5400.0,
            'sector_boundaries': sector_boundaries
        })
        assert sample3['Sector [int]'] == 2  # After second boundary

    def test_sector_supports_variable_number_of_sectors(self):
        """Test tracks with 2 or 4 sectors"""
        normalizer = SampleNormalizer()

        # Track with 2 sectors: 0-2700m, 2700-5400m
        sample = normalizer.normalize({
            'lap_distance': 3000.0,
            'lap_time': 0.0,
            'track_length': 5400.0,
            'sector_boundaries': [2700.0, 5400.0]
        })
        assert sample['Sector [int]'] == 1

        # Track with 4 sectors
        sample2 = normalizer.normalize({
            'lap_distance': 500.0,
            'lap_time': 0.0,
            'track_length': 4000.0,
            'sector_boundaries': [1000.0, 2000.0, 3000.0, 4000.0]
        })
        assert sample2['Sector [int]'] == 0


class TestSectorBoundaryDetection:
    def test_detects_three_sector_boundaries(self):
        """Test detection of sector boundaries from telemetry samples"""
        # Simulate telemetry samples through a lap with 3 sectors
        samples = [
            {'lap_distance': 100.0, 'sector1_time': 0.0, 'sector2_time': 0.0},
            {'lap_distance': 500.0, 'sector1_time': 0.0, 'sector2_time': 0.0},
            {'lap_distance': 1800.0, 'sector1_time': 0.0, 'sector2_time': 0.0},  # End of sector 1
            {'lap_distance': 1850.0, 'sector1_time': 35.2, 'sector2_time': 0.0},  # Sector 1 complete
            {'lap_distance': 2500.0, 'sector1_time': 35.2, 'sector2_time': 0.0},
            {'lap_distance': 3600.0, 'sector1_time': 35.2, 'sector2_time': 0.0},  # End of sector 2
            {'lap_distance': 3650.0, 'sector1_time': 35.2, 'sector2_time': 68.5},  # Sector 2 complete
            {'lap_distance': 5000.0, 'sector1_time': 35.2, 'sector2_time': 68.5},
            {'lap_distance': 5400.0, 'sector1_time': 35.2, 'sector2_time': 68.5},  # End of sector 3
        ]

        boundaries, num_sectors = detect_sector_boundaries(samples, track_length=5400.0)

        assert num_sectors == 3
        assert len(boundaries) == 3
        assert boundaries[0] == pytest.approx(1850.0, abs=100)  # Approximate boundary
        assert boundaries[1] == pytest.approx(3650.0, abs=100)
        assert boundaries[2] == pytest.approx(5400.0, abs=50)

    def test_handles_missing_sector_data(self):
        """Test that detection handles samples without sector data"""
        samples = [
            {'lap_distance': 100.0},
            {'lap_distance': 2700.0},
            {'lap_distance': 5400.0},
        ]

        boundaries, num_sectors = detect_sector_boundaries(samples, track_length=5400.0)

        # Should fall back to equal division (3 sectors)
        assert num_sectors == 3
        assert boundaries == [1800.0, 3600.0, 5400.0]

    def test_detects_two_sector_track(self):
        """Test detection of 2-sector track"""
        samples = [
            {'lap_distance': 100.0, 'sector1_time': 0.0},
            {'lap_distance': 2700.0, 'sector1_time': 0.0},
            {'lap_distance': 2750.0, 'sector1_time': 52.3},  # Sector 1 complete
            {'lap_distance': 5000.0, 'sector1_time': 52.3},
            {'lap_distance': 5400.0, 'sector1_time': 52.3},
        ]

        boundaries, num_sectors = detect_sector_boundaries(samples, track_length=5400.0)

        assert num_sectors == 2
        assert len(boundaries) == 2
        assert boundaries[0] == pytest.approx(2750.0, abs=100)
        assert boundaries[1] == pytest.approx(5400.0, abs=50)
