"""
Debug script to dump ALL fields from rF2 shared memory

Run this with LMU open and in a multiplayer session to see
all available vehicle identification fields.

Usage:
    python debug_dump_all_fields.py
"""

import sys
import time

# Import the shared memory library
try:
    from pyRfactor2SharedMemory.sharedMemoryAPI import SimInfoAPI, Cbytestring2Python
except ImportError:
    # Try vendored copy
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "pyRfactor2SharedMemory"))
    from sharedMemoryAPI import SimInfoAPI, Cbytestring2Python


def safe_convert(value):
    """Safely convert a value to string"""
    try:
        if isinstance(value, bytes):
            return Cbytestring2Python(value)
        elif isinstance(value, (int, float)):
            return str(value)
        elif hasattr(value, '__iter__') and not isinstance(value, str):
            # Array - show first few elements
            return f"[array of {len(value)} items]"
        else:
            return str(value)
    except Exception as e:
        return f"<error: {e}>"


def dump_structure(struct, name, indent=0):
    """Recursively dump all fields from a ctypes structure"""
    prefix = "  " * indent
    print(f"{prefix}{name}:")

    if not hasattr(struct, '_fields_'):
        print(f"{prefix}  <not a structure>")
        return

    for field_name, field_type in struct._fields_:
        try:
            value = getattr(struct, field_name)

            # Convert bytes to string if it's a string field
            if field_name.startswith('m') and isinstance(value, (bytes, bytearray)):
                converted = Cbytestring2Python(value)
                if converted:
                    print(f"{prefix}  {field_name}: '{converted}'")
                else:
                    print(f"{prefix}  {field_name}: <empty>")
            elif isinstance(value, (int, float)):
                print(f"{prefix}  {field_name}: {value}")
            elif hasattr(value, '_fields_'):
                # Nested structure - recurse
                dump_structure(value, field_name, indent + 1)
            elif hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
                # Array
                try:
                    arr_len = len(value)
                    if arr_len <= 4:
                        # Small array - show all values
                        print(f"{prefix}  {field_name}: {[safe_convert(v) for v in value]}")
                    else:
                        # Large array - show first few
                        print(f"{prefix}  {field_name}: [array of {arr_len} items]")
                except:
                    print(f"{prefix}  {field_name}: <array>")
            else:
                print(f"{prefix}  {field_name}: {safe_convert(value)}")
        except Exception as e:
            print(f"{prefix}  {field_name}: <error reading: {e}>")


def main():
    print("=" * 80)
    print("rF2 Shared Memory Field Dump")
    print("=" * 80)
    print()

    # Initialize shared memory
    try:
        info = SimInfoAPI()
    except Exception as e:
        print(f"ERROR: Could not initialize shared memory: {e}")
        print("Make sure LMU is running!")
        return

    # Check if available
    if not info.isSharedMemoryAvailable():
        print("ERROR: Shared memory not available!")
        print("Make sure LMU is running and rF2SharedMemoryMapPlugin is enabled.")
        return

    print("✓ Shared memory connected")
    print()

    # Get scoring info
    try:
        scor_info = info.Rf2Scor.mScoringInfo
        num_vehicles = scor_info.mNumVehicles
        print(f"✓ Found {num_vehicles} vehicles in session")
        print()
    except Exception as e:
        print(f"ERROR: Could not read scoring info: {e}")
        return

    if num_vehicles <= 1:
        print("WARNING: Only 1 vehicle (local player). Join a multiplayer session to see opponent data!")
        print()

    # Find first opponent (non-player vehicle)
    opponent_idx = None
    for i in range(num_vehicles):
        try:
            vehicle_scor = info.Rf2Scor.mVehicles[i]
            if not vehicle_scor.mIsPlayer and vehicle_scor.mControl != 0:
                opponent_idx = i
                break
        except:
            continue

    if opponent_idx is None:
        print("WARNING: No opponents found. Using player vehicle for demo.")
        opponent_idx = 0

    # Get the vehicle structures
    try:
        vehicle_tele = info.Rf2Tele.mVehicles[opponent_idx]
        vehicle_scor = info.Rf2Scor.mVehicles[opponent_idx]
    except Exception as e:
        print(f"ERROR: Could not read vehicle data: {e}")
        return

    # Get basic info
    driver_name = Cbytestring2Python(vehicle_scor.mDriverName)
    is_player = vehicle_scor.mIsPlayer
    control = vehicle_scor.mControl

    print("=" * 80)
    print(f"VEHICLE #{opponent_idx}: {driver_name}")
    print(f"Is Player: {bool(is_player)}")
    print(f"Control: {control} (-1=nobody, 0=local, 1=AI, 2=remote, 3=replay)")
    print("=" * 80)
    print()

    # Dump ALL fields from VehicleScoring
    print("=" * 80)
    print("rF2VehicleScoring (Scoring/Standings Data)")
    print("=" * 80)
    dump_structure(vehicle_scor, "VehicleScoring", indent=0)
    print()

    # Dump ALL fields from VehicleTelemetry
    print("=" * 80)
    print("rF2VehicleTelemetry (Telemetry Data)")
    print("=" * 80)
    dump_structure(vehicle_tele, "VehicleTelemetry", indent=0)
    print()

    # Also check Extended data if available
    try:
        print("=" * 80)
        print("rF2Extended (Extended Session Data)")
        print("=" * 80)
        print(f"  mVersion: {Cbytestring2Python(info.Rf2Ext.mVersion)}")
        print(f"  mSessionStarted: {info.Rf2Ext.mSessionStarted}")
        print()
    except Exception as e:
        print(f"Could not read extended data: {e}")
        print()

    print("=" * 80)
    print("SUMMARY: Vehicle Identification Fields")
    print("=" * 80)

    # Highlight the most relevant fields for vehicle identification
    print("\nKEY FIELDS FOR VEHICLE IDENTIFICATION:")
    print("-" * 80)

    relevant_fields = [
        ('mDriverName', vehicle_scor, 'Driver name'),
        ('mVehicleName', vehicle_scor, 'Vehicle name (scoring)'),
        ('mVehicleName', vehicle_tele, 'Vehicle name (telemetry)'),
        ('mVehicleClass', vehicle_scor, 'Vehicle class'),
        ('mPitGroup', vehicle_scor, 'Pit group / team name'),
        ('mUpgradePack', vehicle_scor, 'Upgrade pack (might contain car variant info)'),
    ]

    for field_name, struct, description in relevant_fields:
        try:
            value = getattr(struct, field_name)
            if isinstance(value, (bytes, bytearray)):
                converted = Cbytestring2Python(value)
                print(f"{field_name:20s} = '{converted}' ({description})")
            else:
                print(f"{field_name:20s} = {safe_convert(value)} ({description})")
        except Exception as e:
            print(f"{field_name:20s} = <error: {e}>")

    print()
    print("=" * 80)
    print("Dump complete!")
    print("=" * 80)
    print()
    print("Please save this output and share it for analysis.")
    print()


if __name__ == '__main__':
    main()
