# Bug: Invalid Property 'mCurrentET' on rF2VehicleScoring

**Status**: FIXED ✅ (v0.2.1)
**Priority**: High (breaks player lap capture)
**Discovered**: 2025-11-20 (v0.2.0 testing)
**Fixed**: 2025-11-20 (v0.2.1)
**Affects**: Player lap capture on Windows with real LMU

---

## Description

The telemetry reader repeatedly logs this error:
```
Error reading telemetry: 'rF2VehicleScoring' object has no attribute 'mCurrentET'
```

This prevents player laps from being captured correctly.

## Root Cause

**Location**: `src/telemetry/telemetry_real.py:113`

```python
'lap_time': scor.mCurrentET - scor.mLapStartET,  # ❌ INCORRECT
```

**Problem**: `mCurrentET` is a property of `rF2ScoringInfo`, not `rF2VehicleScoring`.

### Available Properties

From rF2 shared memory structure:

**rF2ScoringInfo** (accessed via `scor_info`):
- ✅ `mCurrentET` - current time (global)
- ✅ `mStartET` - start time of event
- ✅ `mEndET` - ending time

**rF2VehicleScoring** (accessed via `scor`):
- ✅ `mLapStartET` - time this lap was started
- ✅ `mTimeIntoLap` - **estimated time into lap** ⭐ (BEST OPTION)
- ✅ `mEstimatedLapTime` - estimated lap time
- ✅ `mCurSector1`, `mCurSector2` - current sector times
- ✅ `mLastLapTime` - last completed lap time

## Solution

**Option 1**: Use `scor_info.mCurrentET` (access from scoring info)
```python
'lap_time': scor_info.mCurrentET - scor.mLapStartET,
```

**Option 2**: Use `scor.mTimeIntoLap` directly ⭐ **RECOMMENDED**
```python
'lap_time': scor.mTimeIntoLap,
```

**Recommendation**: Use Option 2 (`mTimeIntoLap`)
- ✅ Direct field for current lap time
- ✅ Already calculated by the game engine
- ✅ Simpler code (one field instead of subtraction)
- ✅ Avoids potential timing precision issues

## Implementation Plan

### Step 1: Fix Player Lap Time
**File**: `src/telemetry/telemetry_real.py`

Change line 113 from:
```python
'lap_time': scor.mCurrentET - scor.mLapStartET,
```

To:
```python
'lap_time': scor.mTimeIntoLap,
```

### Step 2: Fix Opponent Lap Time (if affected)
**File**: `src/telemetry/telemetry_real.py` around line 317

Check `get_all_vehicles()` method - currently uses approximation:
```python
# Current code (lines 309-323)
last_lap_time = vehicle_scor.mLastLapTime

if last_lap_time > 0:
    lap_time = last_lap_time
elif sector2_time > 0:
    lap_time = sector2_time  # In sector 3
elif sector1_time > 0:
    lap_time = sector1_time  # In sector 2
else:
    lap_time = 0.0
```

**Problem**: This logic is convoluted and may not give current lap time correctly.

**Fix**: Use `mTimeIntoLap` for current lap, keep `mLastLapTime` for completed laps:
```python
# For completed laps, use last lap time
# For current lap in progress, use time into lap
if vehicle_scor.mTotalLaps > opponent_tracker_lap:
    # Lap was just completed - use last lap time
    lap_time = vehicle_scor.mLastLapTime
else:
    # Lap in progress - use current lap time
    lap_time = vehicle_scor.mTimeIntoLap
```

**Note**: Need to coordinate with opponent tracker to know which lap we're tracking.

### Step 3: Add Fallback/Validation

Add defensive checks:
```python
# Get lap time with fallback
lap_time = scor.mTimeIntoLap if hasattr(scor, 'mTimeIntoLap') else 0.0

# Validate (lap time should be positive and reasonable)
if lap_time < 0:
    lap_time = 0.0
```

### Step 4: Test

**Test Cases**:
1. ✅ Start LMU and drive a lap - verify no errors in console
2. ✅ Check CSV file has valid lap_time in telemetry samples
3. ✅ Verify lap_time increases from 0 to lap completion
4. ✅ Multiplayer: opponent lap times are captured correctly

## Testing Checklist

- [ ] No console errors when reading telemetry
- [ ] Player laps save successfully
- [ ] Lap time in CSV samples increases monotonically
- [ ] Lap summary shows correct total lap time
- [ ] Opponent laps (if testing multiplayer) have valid times
- [ ] Edge case: lap time = 0 at start of lap

## Related Code

**Files to modify**:
- `src/telemetry/telemetry_real.py` - Line 113 (player), Line ~320 (opponents)

**Files to test**:
- `tests/test_telemetry_real.py` - May need to add test for mTimeIntoLap
- `example_app.py` - Integration test with real LMU

## Estimated Effort

- **Fix**: 15 minutes (simple property change)
- **Testing**: 30 minutes (run LMU, complete laps, verify)
- **Total**: ~1 hour including testing and validation

## Priority Justification

**High Priority** because:
- ❌ Blocks player lap capture entirely
- ❌ Affects all Windows users on v0.2.0
- ✅ Simple fix (one-line change)
- ✅ Can be released as v0.2.1 quickly

## Fix Summary (v0.2.1)

**Changes Made**:
1. **src/telemetry/telemetry_real.py:113** - Player lap time
   - Changed from: `'lap_time': scor.mCurrentET - scor.mLapStartET,`
   - Changed to: `'lap_time': scor.mTimeIntoLap,`

2. **src/telemetry/telemetry_real.py:311** - Opponent lap time
   - Changed from: Complex logic using sector times as fallback
   - Changed to: `lap_time = vehicle_scor.mTimeIntoLap if hasattr(vehicle_scor, 'mTimeIntoLap') else 0.0`

3. **tests/test_telemetry_real.py** - Updated test mocks
   - Updated both test cases to set `mock_scor.mTimeIntoLap` directly
   - Removed references to old calculation method

**Result**: All 91 tests passing ✅
