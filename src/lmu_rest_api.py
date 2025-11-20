"""
LMU REST API client for fetching vehicle metadata

The LMU REST API provides detailed vehicle information that is NOT
available in shared memory, including:
- Car make/model (e.g., "Cadillac V-Series.R", "Ferrari 488 GTE EVO")
- Manufacturer
- Team name
- Vehicle class

This module fetches vehicle data once per session and caches it for
fast lookups during telemetry processing.
"""

import json
from typing import Dict, Any, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import socket


class LMURestAPI:
    """
    Client for LMU REST API

    Fetches vehicle metadata from the LMU REST API running on localhost:6397.
    This data is used to supplement shared memory telemetry with car make/model
    information that is not available through shared memory alone.
    """

    def __init__(self, base_url: str = "http://localhost:6397"):
        """
        Initialize REST API client

        Args:
            base_url: Base URL for LMU REST API (default: http://localhost:6397)
        """
        self.base_url = base_url
        self.vehicle_cache: Optional[Dict[str, Dict[str, Any]]] = None

    def is_available(self) -> bool:
        """
        Check if LMU REST API is available

        Returns:
            True if API is reachable, False otherwise
        """
        try:
            req = Request(f"{self.base_url}/rest/sessions")
            with urlopen(req, timeout=1) as response:
                return response.status == 200
        except (URLError, HTTPError, socket.timeout, ConnectionRefusedError):
            return False
        except Exception:
            return False

    def fetch_vehicle_data(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Fetch vehicle data from /rest/sessions/getAllVehicles

        This endpoint returns all vehicles in the current session with their
        metadata including car model, manufacturer, team name, etc.

        Results are cached to avoid excessive API calls.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dictionary mapping vehicle entry name to vehicle metadata:
            {
                "Action Express Racing #311:LM 1.41": {
                    "car_model": "Cadillac V-Series.R",
                    "manufacturer": "Cadillac",
                    "team": "Action Express Racing",
                    "class": "Hypercar",
                    "full_path_tree": "WEC 2023, Hypercar, Cadillac V-Series.R"
                }
            }
        """
        # Return cached data if available
        if not force_refresh and self.vehicle_cache is not None:
            return self.vehicle_cache

        # Fetch from API
        try:
            req = Request(f"{self.base_url}/rest/sessions/getAllVehicles")
            with urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode('utf-8'))

            # Build lookup dictionary
            vehicle_lookup = {}

            for vehicle in data:
                # Use "vehicle" field as key (matches mVehicleName from shared memory)
                vehicle_name = vehicle.get('vehicle', '')
                if not vehicle_name:
                    continue

                # Extract car model from fullPathTree
                # Format: "WEC 2023, Hypercar, Cadillac V-Series.R"
                # We want: "Cadillac V-Series.R"
                full_path = vehicle.get('fullPathTree', '')
                car_model = self._extract_car_model(full_path)

                # Extract vehicle class from classes array
                # Format: ["Cadillac_V_lmdh", "Hypercar", "WEC2023"]
                # We want: "Hypercar" (the human-readable class)
                classes = vehicle.get('classes', [])
                vehicle_class = self._extract_vehicle_class(classes)

                vehicle_lookup[vehicle_name] = {
                    'car_model': car_model,
                    'manufacturer': vehicle.get('manufacturer', ''),
                    'team': vehicle.get('team', ''),
                    'class': vehicle_class,
                    'full_path_tree': full_path,
                }

            # Cache the results
            self.vehicle_cache = vehicle_lookup
            return vehicle_lookup

        except (URLError, HTTPError, socket.timeout, ConnectionRefusedError):
            # API not available - return empty dict
            return {}
        except Exception as e:
            # Unexpected error - log and return empty
            print(f"[WARNING] Error fetching vehicle data from REST API: {e}")
            return {}

    def _extract_car_model(self, full_path_tree: str) -> str:
        """
        Extract car model from fullPathTree

        Examples:
            "WEC 2023, Hypercar, Cadillac V-Series.R" -> "Cadillac V-Series.R"
            "ELMS 2025, GT3, Ferrari 296 LMGT3" -> "Ferrari 296 LMGT3"

        Args:
            full_path_tree: Full path tree string

        Returns:
            Car model string (last component of path)
        """
        if not full_path_tree:
            return ''

        # Split by comma and take last component
        parts = [p.strip() for p in full_path_tree.split(',')]
        if len(parts) >= 3:
            return parts[-1]  # Last component is usually the car model
        return full_path_tree

    def _extract_vehicle_class(self, classes: list) -> str:
        """
        Extract human-readable vehicle class from classes array

        The classes array contains multiple entries:
        - Technical class name (e.g., "Cadillac_V_lmdh")
        - Human-readable class (e.g., "Hypercar")
        - Series/year (e.g., "WEC2023")

        We want the human-readable class.

        Args:
            classes: List of class strings

        Returns:
            Vehicle class string (e.g., "Hypercar", "GTE", "LMP2", "GT3")
        """
        if not classes:
            return ''

        # Known human-readable classes
        readable_classes = ['Hypercar', 'LMP2', 'LMP3', 'GTE', 'GT3', 'LMGT3']

        for cls in classes:
            if cls in readable_classes:
                return cls

        # Fallback: return second element if it exists and looks like a class
        if len(classes) >= 2:
            return classes[1]

        return classes[0] if classes else ''

    def lookup_vehicle(self, vehicle_name: str) -> Optional[Dict[str, Any]]:
        """
        Look up vehicle metadata by name

        Args:
            vehicle_name: Vehicle entry name (from mVehicleName in shared memory)

        Returns:
            Vehicle metadata dict or None if not found
        """
        if self.vehicle_cache is None:
            # Cache not loaded yet
            self.fetch_vehicle_data()

        return self.vehicle_cache.get(vehicle_name) if self.vehicle_cache else None

    def clear_cache(self):
        """Clear cached vehicle data"""
        self.vehicle_cache = None
