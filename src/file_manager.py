"""File management for saving telemetry CSV files"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class FileManager:
    """
    Manages file operations for telemetry CSV files

    Responsibilities:
    - Generate unique filenames
    - Save CSV data to disk
    - Manage output directory structure
    - Handle file naming conventions
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize file manager

        Args:
            config: Configuration dictionary with optional keys:
                - output_dir: Base directory for output files (default: "./telemetry_output")
                - filename_format: Format string for filenames (default: "{date}_{time}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv")
        """
        self.config = config or {}
        self.output_dir = Path(self.config.get('output_dir', './telemetry_output'))
        self.filename_format = self.config.get(
            'filename_format',
            '{date}_{time}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv'
        )

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_lap(
        self,
        csv_content: str,
        lap_summary: Dict[str, Any],
        session_info: Dict[str, Any]
    ) -> str:
        """
        Save lap data to CSV file

        Args:
            csv_content: Complete CSV content as string
            lap_summary: Lap summary data (contains lap number)
            session_info: Session metadata (contains session_id)

        Returns:
            Path to saved file as string
        """
        filename = self._generate_filename(lap_summary, session_info)
        filepath = self.output_dir / filename

        # Write CSV content to file
        with open(filepath, 'w') as f:
            f.write(csv_content)

        return str(filepath)

    def _generate_filename(
        self,
        lap_summary: Dict[str, Any],
        session_info: Dict[str, Any]
    ) -> str:
        """
        Generate filename for lap data

        Uses field-aware sanitization:
        - Hyphens (-) within field values (replacing spaces)
        - Underscores (_) between fields
        - Lowercase for consistency

        Args:
            lap_summary: Lap summary (contains lap number)
            session_info: Session info (contains session_id, car, track, etc.)

        Returns:
            Filename string
        """
        lap = lap_summary.get('lap', 0)
        session_id = session_info.get('session_id', self._generate_fallback_session_id())

        # Get raw field values
        # Prefer car_model (e.g., "Cadillac V-Series.R") over car_name (team entry)
        car = session_info.get('car_model') or session_info.get('car_name') or 'unknown-car'
        car_class = session_info.get('car_class') or ''
        track = session_info.get('track_name') or 'unknown-track'
        driver = (
            session_info.get('player_name')
            or session_info.get('driver_name')
            or session_info.get('driver')
            or 'unknown-driver'
        )

        # Sanitize fields individually (lowercase, spaces to hyphens)
        car = self._sanitize_field(car)
        car_class = self._sanitize_field(car_class)
        track = self._sanitize_field(track)
        driver = self._sanitize_field(driver)

        timestamp = self._resolve_timestamp(session_info.get('date'))
        date_str = timestamp.strftime('%Y-%m-%d')
        time_str = timestamp.strftime('%H-%M')

        lap_time_seconds = self._format_lap_time(lap_summary.get('lap_time'))

        # Format filename using format string
        # If car_class is available, prefix the car with it for better organization
        if car_class:
            car_with_class = f"{car_class}_{car}"
        else:
            car_with_class = car

        filename = self.filename_format.format(
            session_id=session_id,
            lap=lap,
            car=car_with_class,
            track=track,
            driver=driver,
            date=date_str,
            time=time_str,
            lap_time=lap_time_seconds
        )

        # Final sanitization for any remaining invalid characters
        filename = self._sanitize_filename(filename)

        return filename

    def _sanitize_field(self, field_value: str) -> str:
        """
        Sanitize an individual field value for use in filename

        Converts to lowercase and replaces spaces/invalid chars with hyphens.
        This makes field values internally consistent while field separators
        use underscores.

        Args:
            field_value: The field value to sanitize

        Returns:
            Sanitized field value
        """
        # Convert to lowercase
        sanitized = field_value.lower()

        # Replace invalid characters with hyphens
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', '_']
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '-')

        # Replace spaces with hyphens
        sanitized = sanitized.replace(' ', '-')

        # Remove any duplicate hyphens
        while '--' in sanitized:
            sanitized = sanitized.replace('--', '-')

        # Strip leading/trailing hyphens
        sanitized = sanitized.strip('-')

        return sanitized

    def _sanitize_filename(self, filename: str) -> str:
        """
        Final sanitization pass for complete filename

        Removes any remaining invalid filesystem characters.
        By this point, fields should already be sanitized.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Replace any remaining invalid characters with underscores
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        return filename

    def _generate_fallback_session_id(self) -> str:
        """Generate a fallback session ID if none provided"""
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def _resolve_timestamp(self, value: Optional[Any]) -> datetime:
        """Resolve a timestamp from session info for filename formatting."""
        if isinstance(value, datetime):
            return value

        if value:
            try:
                return datetime.fromisoformat(str(value))
            except ValueError:
                pass

        return datetime.now()

    def _format_lap_time(self, lap_time: Optional[Any]) -> int:
        """Format lap time value as whole seconds for filenames."""
        try:
            seconds = float(lap_time)
        except (TypeError, ValueError):
            return 0

        return int(round(seconds))

    def get_output_directory(self) -> Path:
        """Get the output directory path"""
        return self.output_dir

    def list_saved_laps(self) -> list[str]:
        """
        List all saved lap files in output directory

        Returns:
            List of filenames
        """
        if not self.output_dir.exists():
            return []

        return [f.name for f in self.output_dir.glob('*.csv')]

    def delete_lap(self, filename: str) -> bool:
        """
        Delete a specific lap file

        Args:
            filename: Name of file to delete

        Returns:
            True if deleted, False if file not found
        """
        filepath = self.output_dir / filename

        if filepath.exists():
            filepath.unlink()
            return True

        return False

    def clear_all_laps(self) -> int:
        """
        Delete all lap files in output directory

        Returns:
            Number of files deleted
        """
        count = 0

        for filepath in self.output_dir.glob('*.csv'):
            filepath.unlink()
            count += 1

        return count

    def get_session_laps(self, filter_string: str) -> list[str]:
        """
        Get all lap files matching a filter string

        Can be used to filter by date, time, track, car, driver, or any substring
        that appears in the filename. Useful for grouping laps from the same session.

        Args:
            filter_string: String to match in filenames (e.g., '2025-11-18_13-52' for a session)

        Returns:
            List of filenames matching the filter
        """
        if not self.output_dir.exists():
            return []

        pattern = f"*{filter_string}*.csv"
        return [f.name for f in self.output_dir.glob(pattern)]
