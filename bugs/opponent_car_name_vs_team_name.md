# Bug: Opponent Car Name Shows Team Name Instead of Car Make/Model

**Status**: DEBUG LOGGING ADDED - AWAITING TEST RESULTS
**Priority**: Medium (affects file organization and searchability)
**Discovered**: 2025-11-20 (v0.2.1 testing)
**Affects**: Opponent lap filename generation

**Debug Logging**: Added to `src/telemetry/telemetry_real.py:305-318`

---

## Description

The opponent lap CSV filenames currently show the **team name** (e.g., "Proton Competition #16") instead of the **car make/model** (e.g., "Oreca 07 LMP2" or "BMW M4 GT3").

This makes it difficult to find comparison laps because users want to compare laps for the same car model, not the same team.

## User Feedback

> "Much better, but just noticed that the 'car name' in the filename is actually the 'team name'? I want to know the car make/model, so that I can find comparison laps easily. Team name is not important, but we should have it in the metadata just in case anyway."

## Current Behavior

**Filename example**:
```
2025-11-20_15-23_spa_proton-competition-#16_igor-pikachu_lap2_t95s.csv
                       ^^^^^^^^^^^^^^^^^^^^^^^^
                       Team name + number (not helpful for finding car model)
```

**Console output**:
```
*** Opponent lap completed: Igor Pikachu
    Lap 2: 95.234s
    Position: P20
    Car: Project 1 - AO #56:LM    ← Team name, not car model
    Samples: 9523
    Fastest: True
```

## Desired Behavior

**Filename should show car make/model**:
```
2025-11-20_15-23_spa_oreca-07-lmp2_igor-pikachu_lap2_t95s.csv
                       ^^^^^^^^^^^^^^
                       Car make/model (easy to find all Oreca 07 laps)
```

**Team name should be in CSV metadata**:
```csv
Format,LMUTelemetry
Version,3
Player,Igor Pikachu
TrackName,Spa-Francorchamps
CarName,Oreca 07 LMP2           ← Car make/model
TeamName,Proton Competition #16  ← NEW: Team name in metadata
SessionUTC,2025-11-20T15:23:45
LapTime [s],95.234
TrackLen [m],7004.0
```

## Available Fields in rF2 Shared Memory

From `src/pyRfactor2SharedMemory/rF2data.py`:

### rF2VehicleScoring (Scoring Data)
```python
class rF2VehicleScoring(ctypes.Structure):
    _fields_ = [
        ('mID', ctypes.c_int),
        ('mDriverName', ctypes.c_ubyte*32),         # Driver name
        ('mVehicleName', ctypes.c_ubyte*64),        # ← Currently used for car_name
        ('mVehicleClass', ctypes.c_ubyte*32),       # Class (e.g., "LMP2", "GT3")
        ('mPitGroup', ctypes.c_ubyte*24),           # Team name (documented as "same as team name unless pit is shared")
        # ... other fields ...
    ]
```

### rF2VehicleTelemetry (Telemetry Data)
```python
class rF2VehicleTelemetry(ctypes.Structure):
    _fields_ = [
        ('mID', ctypes.c_int),
        ('mVehicleName', ctypes.c_ubyte*64),        # ← Also has vehicle name
        ('mTrackName', ctypes.c_ubyte*64),
        # ... other fields ...
    ]
```

## Current Implementation

**File**: `src/telemetry/telemetry_real.py:302-303`

```python
car_name = self.Cbytestring2Python(vehicle_tele.mVehicleName) or \
           self.Cbytestring2Python(vehicle_scor.mVehicleName)
```

We try telemetry `mVehicleName` first, then scoring `mVehicleName`.

**Observations**:
- `mVehicleName` appears to contain the team entry name (e.g., "Proton Competition #16")
- `mVehicleClass` contains the class (e.g., "HYPERCAR", "LMP2", "GT3") but NOT the car model
- `mPitGroup` is documented as "team name unless pit is shared"

## Questions to Investigate

1. **Does `vehicle_tele.mVehicleName` differ from `vehicle_scor.mVehicleName`?**
   - Maybe telemetry has car model and scoring has team name?

2. **What does `mVehicleClass` actually contain?**
   - Does it have just "LMP2" or does it have "Oreca 07 LMP2"?

3. **Is there another field we're missing?**
   - Check extended data or other structures

4. **How does LMU populate these fields?**
   - .veh files define entries (team + driver)
   - Where is the car model stored?

## Investigation Plan

### Step 1: Add Debug Logging

**File**: `src/telemetry/telemetry_real.py`
**Location**: After line 303 in `get_all_vehicles()`

Add logging to print ALL vehicle-related fields:

```python
# DEBUG: Log all vehicle identification fields
if i == 0:  # Only log for first opponent to avoid spam
    print(f"\n[DEBUG] Vehicle identification fields:")
    print(f"  mVehicleName (tele): {self.Cbytestring2Python(vehicle_tele.mVehicleName)}")
    print(f"  mVehicleName (scor): {self.Cbytestring2Python(vehicle_scor.mVehicleName)}")
    print(f"  mVehicleClass:       {self.Cbytestring2Python(vehicle_scor.mVehicleClass)}")
    print(f"  mPitGroup:           {self.Cbytestring2Python(vehicle_scor.mPitGroup)}")
    print(f"  mDriverName:         {self.Cbytestring2Python(vehicle_scor.mDriverName)}")
```

### Step 2: Test in Multiplayer

- Join multiplayer session with various car classes
- Observe what each field actually contains
- Document findings

### Step 3: Implement Solution

Based on findings, implement one of:

**Option A**: Use `mVehicleClass` if it contains model
```python
car_model = telemetry.get('vehicle_class')  # e.g., "Oreca 07 LMP2"
team_name = telemetry.get('car_name')       # e.g., "Proton Competition #16"
```

**Option B**: Parse from `mVehicleName`
```python
# If mVehicleName = "Proton Competition #16" and class = "LMP2"
# Infer car model from class somehow (not ideal)
```

**Option C**: Add both fields
```python
# Add both car_model and team_name to telemetry dict
vehicle_data = {
    'car_model': ...,   # For filename
    'team_name': ...,   # For metadata
    # ...
}
```

## Expected Changes

### 1. Update telemetry dictionary

**File**: `src/telemetry/telemetry_real.py:319-340`

Add separate fields for car model and team name:

```python
vehicle_data = {
    'driver_name': driver_name,
    'car_name': car_model,           # ← Car make/model (for filename)
    'team_name': team_name,          # ← NEW: Team name (for metadata)
    'car_class': car_class,          # ← Class designation (LMP2, GT3, etc.)
    'control': vehicle_scor.mControl,
    # ... rest ...
}
```

### 2. Update CSV metadata

**File**: `src/csv_formatter.py`

Add TeamName to metadata section:

```python
metadata_lines = [
    f"Format,{self.format_name}",
    f"Version,{self.format_version}",
    f"Player,{session_info.get('player_name', 'Unknown')}",
    f"TrackName,{session_info.get('track_name', 'Unknown')}",
    f"CarName,{session_info.get('car_name', 'Unknown')}",
    f"TeamName,{session_info.get('team_name', 'Unknown')}",  # ← NEW
    # ...
]
```

### 3. Update tests

All opponent tests need `team_name` field added to mock data.

## Testing Checklist

- [ ] Debug logging added to telemetry_real.py
- [ ] Tested in multiplayer to observe field values
- [ ] Documented what each field contains
- [ ] Implemented solution based on findings
- [ ] Updated CSV metadata to include TeamName
- [ ] Updated tests
- [ ] Verified filenames show car model
- [ ] Verified CSV metadata shows team name

## Related Files

**To Investigate**:
- `src/telemetry/telemetry_real.py` - Read fields from shared memory
- `src/pyRfactor2SharedMemory/rF2data.py` - Structure definitions

**To Modify** (after investigation):
- `src/telemetry/telemetry_real.py` - Add team_name field
- `src/csv_formatter.py` - Add TeamName to metadata
- `tests/test_opponent_tracker.py` - Update mocks
- `tests/test_telemetry_loop.py` - Update mocks

## Notes

In LMU/rF2:
- .veh files define **entries** (team + driver + car assignment)
- The car model is defined in the vehicle class files
- Shared memory exposes the entry name as `mVehicleName`
- Need to find where the actual car model name is exposed

This is different from games like iRacing where car model is clearly separated from team/livery.

## Priority Justification

**Medium Priority** because:
- ✅ Feature works (laps are saved correctly)
- ❌ Poor file organization (hard to find comparison laps)
- ✅ Relatively easy fix once we know the right fields
- 🔧 Requires testing in live multiplayer to determine correct solution

---

## Current Status (2025-11-20)

### ✅ INVESTIGATION COMPLETE

**Debug output received**:
```
[DEBUG] Vehicle identification fields for 'J P':
  mVehicleName (tele): 'Iron Dames #85:LM'
  mVehicleName (scor): 'Iron Dames #85:LM'
  mVehicleClass:       'GTE'
  mPitGroup:           'Group32'
  car_name (used):     'Iron Dames #85:LM'
```

### Findings

**BAD NEWS**: LMU/rF2 shared memory **does NOT expose the car make/model separately**.

Available fields:
- ❌ `mVehicleName`: Contains team entry name (e.g., "Iron Dames #85:LM") - NOT car model
- ❌ `mVehicleClass`: Contains class only (e.g., "GTE") - too generic, doesn't distinguish Porsche vs Ferrari
- ❌ `mPitGroup`: Contains generic group (e.g., "Group32") - not useful

**CONCLUSION**: The car make/model (e.g., "Porsche 911 RSR", "Ferrari 488 GTE") is NOT available in shared memory. It's defined in the vehicle files (.veh) but not exposed to telemetry plugins.

### Proposed Solution

Since we can't get the actual car model, we have two options:

**Option A: Keep current behavior, improve metadata**
- ✅ Filename continues to use team entry name (e.g., "iron-dames-#85-lm")
- ✅ Add vehicle class to filename for better organization (e.g., "gte_iron-dames-#85-lm")
- ✅ Add vehicle class to CSV metadata
- ✅ Document limitation clearly

**Option B: Manual car model mapping (future enhancement)**
- Create a mapping file: team entry → car model
- Users could edit this file to map entries to car models
- More complex, requires maintenance

**RECOMMENDATION**: Go with Option A for now.

### Implementation Plan (Option A)

1. **Add vehicle class to telemetry dict**
   ```python
   vehicle_data = {
       'car_name': car_name,           # Team entry (e.g., "Iron Dames #85:LM")
       'car_class': vehicle_class,     # NEW: Class (e.g., "GTE")
       # ...
   }
   ```

2. **Update filename format to include class**
   ```
   Before: 2025-11-20_15-23_spa_iron-dames-#85-lm_jp_lap2_t95s.csv
   After:  2025-11-20_15-23_spa_gte_iron-dames-#85-lm_jp_lap2_t95s.csv
                                      ^^^^
                                      Class helps group by car type
   ```

3. **Add CarClass to CSV metadata**
   ```csv
   Format,LMUTelemetry
   Version,3
   Player,J P
   TrackName,Spa-Francorchamps
   CarName,Iron Dames #85:LM
   CarClass,GTE                  ← NEW: Helps identify car category
   SessionUTC,2025-11-20T15:23:45
   LapTime [s],95.234
   TrackLen [m],7004.0
   ```

4. **Update documentation**
   - Explain that CarName is the team entry, not car model
   - Explain that CarClass helps categorize (HYPERCAR, LMP2, GTE, GT3)
   - Suggest manual organization if users need car-specific grouping
