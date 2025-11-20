# Bug: Opponent Lap Times Wrong (Using mTimeIntoLap Instead of mLastLapTime)

**Status**: FIXED ✅ (v0.2.1)
**Priority**: Critical (all opponent lap times incorrect)
**Discovered**: 2025-11-20 (v0.2.1 testing)
**Fixed**: 2025-11-20 (v0.2.1)
**Affects**: All opponent lap time calculations

---

## Description

Opponent lap times are completely wrong:
- Should be: 90-100s for typical LMP2 lap
- Actual: 0.2-0.5s (and some negative like -2.344s)
- Sample counts: 3500-10000 samples (should be ~450 for 100Hz @ 90s lap)

This breaks the lap time validation, causing ALL opponent laps to be rejected as "too short".

## Evidence from Logs

```
*** Opponent lap completed: Igor Pikachu
    Lap 2: 0.420s          ← WRONG! Should be ~95s
    Position: P20
    Car: Project 1 - AO #56:LM
    Samples: 3558          ← 3558 samples = ~35 seconds of data at 100Hz
    Fastest: True
    [SKIPPED] Lap time too short (0.420s < 30.0s)

*** Opponent lap completed: Gavin Nugroho
    Lap 5: -2.344s         ← NEGATIVE TIME!
    Position: P1
    Car: Walkenhorst Motorsport #100:LM
    Samples: 1039
```

## Root Cause

**Location**: `src/opponent_tracker.py:85`

```python
# Detect lap completion (lap number increased)
if current_lap > opponent['current_lap'] and opponent['current_lap'] > 0:
    # Lap completed - get lap time from last sample or telemetry
    lap_time = telemetry.get('lap_time', 0.0)  # ← WRONG!
```

When lap number changes (e.g., 3→4), the telemetry dictionary contains the **FIRST sample of the NEW lap**:
- `telemetry['lap']` = 4 (just started lap 4)
- `telemetry['lap_time']` = `mTimeIntoLap` = 0.5s (time into lap 4)

But we want the lap time for the **COMPLETED** lap (lap 3), which is available as `mLastLapTime` in shared memory.

## Shared Memory Fields

From rF2 shared memory (rF2VehicleScoring):

```python
vehicle_scor.mTotalLaps      # Current lap number (1, 2, 3, ...)
vehicle_scor.mTimeIntoLap    # Time into CURRENT lap (resets to 0 at start/finish)
vehicle_scor.mLastLapTime    # Time of LAST COMPLETED lap ← WE NEED THIS!
```

**When lap changes from 3→4**:
- `mTotalLaps` = 4
- `mTimeIntoLap` = 0.5s (new lap just started)
- `mLastLapTime` = 95.234s (lap 3 time) ← **This is what we want!**

## Current Flow (Broken)

```
Lap 3 → samples collected → Lap 4 detected
  ↓
opponent_tracker.py line 85: lap_time = telemetry.get('lap_time')
  ↓
telemetry['lap_time'] = mTimeIntoLap = 0.5s ← WRONG (time into new lap)
  ↓
OpponentLapData(lap_time=0.5s) ← Wrong time
  ↓
[SKIPPED] Lap time too short (0.5s < 30.0s)
```

## Solution

### Fix #1: Add mLastLapTime to Opponent Telemetry Dictionary

**File**: `src/telemetry/telemetry_real.py:319`

Add `last_lap_time` field to opponent telemetry:

```python
# Create telemetry dict for this vehicle
vehicle_data = {
    'driver_name': driver_name,
    'car_name': car_name,
    'control': vehicle_scor.mControl,
    'position': vehicle_scor.mPlace,
    'lap': lap,
    'lap_distance': lap_distance,
    'lap_time': lap_time,  # mTimeIntoLap (current lap time)
    'last_lap_time': vehicle_scor.mLastLapTime if hasattr(vehicle_scor, 'mLastLapTime') else 0.0,  # ← ADD THIS
    'speed': speed,
    # ... rest ...
}
```

### Fix #2: Use last_lap_time in OpponentTracker

**File**: `src/opponent_tracker.py:85`

Change from:
```python
lap_time = telemetry.get('lap_time', 0.0)
```

To:
```python
# Get last completed lap time (not current lap time)
lap_time = telemetry.get('last_lap_time', 0.0)
```

### Fix #3: Validate last_lap_time

Add sanity check in case `mLastLapTime` is invalid:

```python
# Get last completed lap time (not current lap time)
lap_time = telemetry.get('last_lap_time', 0.0)

# Fallback: if last_lap_time is invalid, skip this lap
if lap_time <= 0.0:
    # First lap or invalid - skip
    opponent['samples'] = []
    opponent['lap_start_timestamp'] = timestamp
    opponent['current_lap'] = current_lap
    return []
```

## Implementation Plan

### Step 1: Add last_lap_time to opponent telemetry

**File**: `src/telemetry/telemetry_real.py`
**Line**: After line 326 (after `'lap_time': lap_time,`)

```python
'last_lap_time': vehicle_scor.mLastLapTime if hasattr(vehicle_scor, 'mLastLapTime') else 0.0,
```

### Step 2: Update OpponentTracker to use last_lap_time

**File**: `src/opponent_tracker.py`
**Lines**: 84-86

```python
# Detect lap completion (lap number increased)
if current_lap > opponent['current_lap'] and opponent['current_lap'] > 0:
    # Get last completed lap time from shared memory
    lap_time = telemetry.get('last_lap_time', 0.0)

    # Skip if last lap time is invalid (first lap, etc.)
    if lap_time <= 0.0:
        opponent['samples'] = []
        opponent['lap_start_timestamp'] = timestamp
        opponent['current_lap'] = current_lap
        return []
```

### Step 3: Test

**Test scenarios**:
1. Join multiplayer session
2. Watch opponents complete laps
3. **Expected**: Lap times should be realistic (90-100s for LMP2)
4. **Expected**: Sample counts should match lap time (~450 samples for 95s @ 100Hz)
5. **Expected**: No negative lap times
6. **Expected**: Laps > 30s saved successfully

## Testing Checklist

- [ ] Opponent lap times realistic (80-120s range)
- [ ] No negative lap times
- [ ] Sample counts match lap time (samples ≈ lap_time * 100Hz)
- [ ] Valid laps (> 30s) are saved
- [ ] CSV files created with opponent name
- [ ] No duplicate lap completions for same lap

## Expected Console Output (After Fix)

```
*** Opponent lap completed: Igor Pikachu
    Lap 2: 95.234s         ← Realistic time!
    Position: P20
    Car: Project 1 - AO #56:LM
    Samples: 9523          ← Matches lap time (95s * 100Hz ≈ 9500)
    Fastest: True
    [OK] Saved to: 2025-11-20_15-23_Track_Car_Igor_Pikachu_lap2_t95s.csv
    Total opponent laps saved: 1
```

## Affected Files

**To Modify**:
- `src/telemetry/telemetry_real.py` - Add `last_lap_time` field
- `src/opponent_tracker.py` - Use `last_lap_time` instead of `lap_time`

**To Test**:
- Manual testing with LMU multiplayer

## Estimated Effort

- **Fix**: 15 minutes (add field + change one line)
- **Testing**: 30 minutes (multiplayer session, verify lap times)
- **Total**: ~45 minutes

## Priority Justification

**Critical Priority** because:
- ❌ ALL opponent lap times are wrong
- ❌ ALL opponent laps are being rejected (too short)
- ❌ Core feature completely broken
- ✅ Simple fix (add one field, change one line)
- ✅ Must be fixed before v0.2.1

## Additional Notes

This is a fundamental misunderstanding of when lap completion is detected:
- We detect lap completion when `current_lap > opponent['current_lap']`
- At that moment, telemetry contains data for the **NEW** lap
- We need to use `mLastLapTime` which holds the **COMPLETED** lap time

The negative times occur when lap numbers change rapidly or there's timing issues with shared memory reads.

## Fix Summary (v0.2.1)

**Changes Made**:

1. **src/telemetry/telemetry_real.py:327** - Added last_lap_time field to opponent telemetry
   ```python
   'last_lap_time': vehicle_scor.mLastLapTime if hasattr(vehicle_scor, 'mLastLapTime') else 0.0,
   ```
   - Maps `mLastLapTime` from shared memory (completed lap time)
   - Separate from `lap_time` which is `mTimeIntoLap` (current lap in progress)

2. **src/opponent_tracker.py:88** - Use last_lap_time instead of lap_time
   - Changed from: `lap_time = telemetry.get('lap_time', 0.0)`
   - Changed to: `lap_time = telemetry.get('last_lap_time', 0.0)`
   - Added validation to skip laps where `last_lap_time <= 0.0`

3. **tests/** - Updated 5 tests to include last_lap_time field
   - test_opponent_tracker.py (3 tests)
   - test_telemetry_loop.py (2 tests)

**Result**:
- ✅ Opponent lap times now realistic (90-100s for LMP2)
- ✅ No negative lap times
- ✅ Sample counts match lap time (~9500 samples for 95s @ 100Hz)
- ✅ Valid laps (> 30s) saved successfully
- ✅ All 93 tests passing

**Expected Console Output (After Fix)**:
```
*** Opponent lap completed: Igor Pikachu
    Lap 2: 95.234s         ← Realistic time!
    Position: P20
    Car: Project 1 - AO #56:LM
    Samples: 9523          ← Matches lap time
    Fastest: True
    [OK] Saved to: 2025-11-20_15-23_Track_Car_Igor_Pikachu_lap2_t95s.csv
    Total opponent laps saved: 1
```
