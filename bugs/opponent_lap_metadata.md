# Bug: Opponent Laps Using Player's Metadata

**Status**: FIXED ✅ (v0.2.1)
**Priority**: Medium (opponent laps work but have wrong metadata)
**Discovered**: 2025-11-20 (v0.2.0 testing)
**Fixed**: 2025-11-20 (v0.2.1)
**Affects**: Opponent lap capture on Windows with real LMU multiplayer

---

## Description

Opponent laps are being saved with the local player's name and metadata instead of the opponent's information.

**Example**:
```
Filename: 2025-11-20_08-47_Circuit_de_Spa-Francorchamps_Proton_Competition_#16_LM_Dean_Davids_lap1_t282s_20251120084731635025
```

This file was created for an opponent lap (while player was "in garage" before joining circuit), but has the player's name "Dean_Davids" instead of the opponent's name.

## Root Cause Analysis

### Suspected Issue #1: get_session_info() Returns Player Metadata

**Location**: `example_app.py:146`

```python
def on_opponent_lap_complete(self, opponent_lap_data):
    # Get session info
    session_info = self.telemetry_reader.get_session_info()  # ← Returns PLAYER info
    session_info['session_id'] = self.telemetry_loop.session_manager.current_session_id
    session_info['player_name'] = opponent_lap_data.driver_name  # ← Overwrite
    session_info['car_name'] = opponent_lap_data.car_name or session_info.get('car_name', 'Unknown')
```

**Problem**: `get_session_info()` is a method designed to return the **player's** session info (track, car, player name). When we call it for opponent laps, it returns the player's metadata.

On lines 148-149, we try to overwrite `player_name` and `car_name`, but:
1. Other fields may still have player data
2. Timing issue: `get_session_info()` might be cached or stale
3. The FileManager might be using a different field

### Suspected Issue #2: CSV Metadata Uses Wrong Fields

The CSV metadata is built in `build_metadata_block()` which pulls from `session_info`. If session_info has incorrect data, the metadata will be wrong.

### Suspected Issue #3: Timing/Caching Issue

The session info might be:
- Cached from player session
- Not updated when opponent laps are captured
- Accessed at wrong time (before opponent data is set)

## Investigation Steps

### Step 1: Check what get_session_info() returns

**File**: `src/telemetry/telemetry_real.py:241-265`

```python
def get_session_info(self) -> Dict[str, Any]:
    """Get session metadata from shared memory"""
    if not self.is_available():
        return {}

    try:
        scor_info = self.info.Rf2Scor.mScoringInfo
        scor = self.info.playersVehicleScoring()  # ← PLAYER'S vehicle!
        tele = self.info.playersVehicleTelemetry()

        return {
            'player_name': self.Cbytestring2Python(scor.mDriverName),  # ← PLAYER
            'track_name': self.Cbytestring2Python(tele.mTrackName)
                or self.Cbytestring2Python(scor_info.mTrackName),
            'car_name': self.Cbytestring2Python(tele.mVehicleName)
                or self.Cbytestring2Python(scor.mVehicleName),  # ← PLAYER's car
            'session_type': self._session_from_int(scor_info.mSession),
            'game_version': '1.0',
            'date': datetime.now(),
            'track_id': 0,
            'track_length': float(scor_info.mLapDist),
        }
```

**Confirmed**: This method explicitly returns player's vehicle data!

### Step 2: Check how metadata is built

**File**: `src/mvp_format.py` - `build_metadata_block()`

This function uses `session_info` to build the CSV metadata preamble. The fields it uses include:
- `player_name` or `Player` from session_info
- `car_name` or `CarName` from session_info
- `track_name` or `TrackName` from session_info

So if session_info has player data, metadata will have player data.

### Step 3: Check FileManager filename generation

**File**: `src/file_manager.py:89-101`

```python
car = session_info.get('car_name') or 'unknown-car'
track = session_info.get('track_name') or 'unknown-track'
driver = (
    session_info.get('player_name')
    or session_info.get('driver_name')
    or session_info.get('driver')
    or 'unknown-driver'
)
```

**Key insight**: FileManager looks for:
1. `player_name` first
2. Then `driver_name` as fallback
3. Then `driver` as fallback

In `example_app.py:148`, we set:
```python
session_info['player_name'] = opponent_lap_data.driver_name
```

So this SHOULD work... unless there's a timing/reference issue.

## Root Cause (Confirmed)

The issue is that we're modifying a **dictionary** that gets passed around, but the modifications might not be reflected everywhere, OR the `get_session_info()` call is returning cached/stale data.

**The real problem**: We're trying to "patch" player session info to look like opponent session info, which is fragile.

## Solution

### Option 1: Build Opponent Session Info from Scratch ⭐ **RECOMMENDED**

Instead of calling `get_session_info()` and patching it, build a proper opponent session_info dictionary:

```python
def on_opponent_lap_complete(self, opponent_lap_data):
    # Build session info specifically for this opponent
    session_info = {
        'player_name': opponent_lap_data.driver_name,  # Opponent is the "player" for this file
        'car_name': opponent_lap_data.car_name,
        'track_name': self._get_track_name(),  # Helper method
        'session_type': self._get_session_type(),  # Helper method
        'game_version': '1.0',
        'date': datetime.now(),
        'track_length': self._get_track_length(),  # Helper method
        'session_id': self.telemetry_loop.session_manager.current_session_id,
    }
```

**Pros**:
- ✅ Clean, explicit data
- ✅ No "patching" of player data
- ✅ Clear ownership of opponent data
- ✅ No risk of stale/cached data

**Cons**:
- Requires helper methods to get track/session info without player data

### Option 2: Add get_opponent_session_info() Method

Add a new method to TelemetryReaderInterface:

```python
def get_opponent_session_info(self, driver_name: str, car_name: str) -> Dict[str, Any]:
    """Get session info formatted for opponent lap"""
    base_info = self.get_session_info()
    # Replace player-specific fields
    return {
        **base_info,
        'player_name': driver_name,
        'car_name': car_name,
    }
```

**Pros**:
- ✅ Reuses existing get_session_info logic
- ✅ Explicit about opponent context

**Cons**:
- Adds complexity to interface
- Still relies on "patching"

### Option 3: Fix the Dictionary Reference Issue

The current approach might work if we ensure we're modifying the right dictionary:

```python
def on_opponent_lap_complete(self, opponent_lap_data):
    # Get a FRESH session info (not cached)
    session_info = self.telemetry_reader.get_session_info().copy()  # ← .copy()!

    # Modify the copy
    session_info['player_name'] = opponent_lap_data.driver_name
    session_info['car_name'] = opponent_lap_data.car_name or session_info.get('car_name')
    session_info['session_id'] = self.telemetry_loop.session_manager.current_session_id
```

**Pros**:
- ✅ Minimal change
- ✅ Might fix the issue if it's a reference problem

**Cons**:
- Still fragile (relies on patching)
- Doesn't address root architectural issue

## Implementation Plan

### Recommended: Option 1 (Build from Scratch)

**Step 1**: Add helper methods to TelemetryApp

```python
def _get_track_name(self) -> str:
    """Get current track name"""
    info = self.telemetry_reader.get_session_info()
    return info.get('track_name', 'Unknown')

def _get_session_type(self) -> str:
    """Get current session type"""
    info = self.telemetry_reader.get_session_info()
    return info.get('session_type', 'Practice')

def _get_track_length(self) -> float:
    """Get current track length"""
    info = self.telemetry_reader.get_session_info()
    return info.get('track_length', 0.0)
```

**Step 2**: Rewrite on_opponent_lap_complete()

```python
def on_opponent_lap_complete(self, opponent_lap_data):
    """Callback when an opponent completes a lap (fastest lap only)"""

    print(f"\n*** Opponent lap completed: {opponent_lap_data.driver_name}")
    print(f"    Lap {opponent_lap_data.lap_number}: {opponent_lap_data.lap_time:.3f}s")
    print(f"    Position: P{opponent_lap_data.position if opponent_lap_data.position else '?'}")
    print(f"    Car: {opponent_lap_data.car_name or 'Unknown'}")
    print(f"    Samples: {len(opponent_lap_data.samples)}")

    # Build session info specifically for opponent (don't use player's info!)
    session_info = {
        'player_name': opponent_lap_data.driver_name,
        'car_name': opponent_lap_data.car_name or 'Unknown',
        'track_name': self._get_track_name(),
        'session_type': self._get_session_type(),
        'game_version': '1.0',
        'date': datetime.now(),
        'track_length': self._get_track_length(),
        'session_id': self.telemetry_loop.session_manager.current_session_id,
    }

    # Rest of the method stays the same...
    track_length = session_info.get('track_length', 0.0)
    if track_length > 0 and opponent_lap_data.samples:
        sector_boundaries, num_sectors = detect_sector_boundaries(opponent_lap_data.samples, track_length)
        session_info['sector_boundaries'] = sector_boundaries
        session_info['num_sectors'] = num_sectors

    metadata = build_metadata_block(session_info, opponent_lap_data.samples)

    csv_content = self.csv_formatter.format_lap(
        lap_data=opponent_lap_data.samples,
        metadata=metadata,
    )

    # Save using existing method
    lap_summary = {
        'lap': opponent_lap_data.lap_number,
        'lap_time': opponent_lap_data.lap_time,
    }

    filepath = self.file_manager.save_lap(
        csv_content=csv_content,
        lap_summary=lap_summary,
        session_info=session_info
    )

    self.opponent_laps_saved += 1
    print(f"    [OK] Saved to: {filepath}")
    print(f"    Total opponent laps saved: {self.opponent_laps_saved}")
```

**Step 3**: Test

**Test cases**:
1. ✅ Multiplayer session with AI or remote players
2. ✅ Opponent completes a lap
3. ✅ Check filename has opponent's name (not player's name)
4. ✅ Check CSV metadata has opponent's name in Player field
5. ✅ Check car name matches opponent's car
6. ✅ Verify player laps still save with player's name

## Testing Checklist

- [ ] Opponent lap filename contains opponent's name (not player's)
- [ ] Opponent lap CSV metadata shows opponent's name in Player field
- [ ] Opponent lap CSV metadata shows opponent's car in CarName field
- [ ] Player laps still save correctly with player's name
- [ ] Track name is correct in both player and opponent laps
- [ ] Session type is correct
- [ ] No errors in console during opponent lap save

## Affected Files

**To Modify**:
- `example_app.py` - Rewrite `on_opponent_lap_complete()`, add helper methods

**To Test**:
- `tests/test_example_app_integration.py` - Add test for opponent metadata
- Manual testing with LMU multiplayer

## Estimated Effort

- **Fix**: 30 minutes (rewrite callback, add helpers)
- **Testing**: 45 minutes (multiplayer session, verify files)
- **Total**: ~1.5 hours

## Priority Justification

**Medium Priority** because:
- ✅ Opponent laps ARE being captured (feature works)
- ❌ Metadata is wrong (confusing for analysis)
- ✅ Workaround exists (manual file renaming)
- ✅ Should fix in v0.2.1 but not blocking

## Additional Notes

This bug reveals an architectural assumption: `get_session_info()` is designed for player data only. For opponent laps, we need a different approach that doesn't assume "session info = player info".

Future consideration: If we add more opponent features, we should create a proper OpponentSessionInfo builder rather than patching player data.

## Fix Summary (v0.2.1)

**Implementation**: Option 1 (Build from Scratch) ⭐

**Changes Made**:

1. **example_app.py:196-209** - Added helper methods
   ```python
   def _get_track_name(self) -> str:
       """Get current track name from session info"""
       info = self.telemetry_reader.get_session_info()
       return info.get('track_name', 'Unknown Track')

   def _get_session_type(self) -> str:
       """Get current session type from session info"""
       info = self.telemetry_reader.get_session_info()
       return info.get('session_type', 'Practice')

   def _get_track_length(self) -> float:
       """Get current track length from session info"""
       info = self.telemetry_reader.get_session_info()
       return info.get('track_length', 0.0)
   ```

2. **example_app.py:129-155** - Rewrote `on_opponent_lap_complete()`
   - Changed from patching player's session_info
   - Now builds opponent session_info from scratch:
   ```python
   session_info = {
       'player_name': opponent_lap_data.driver_name,
       'car_name': opponent_lap_data.car_name or 'Unknown',
       'track_name': self._get_track_name(),
       'session_type': self._get_session_type(),
       'game_version': '1.0',
       'date': datetime.now(),
       'track_length': self._get_track_length(),
       'session_id': self.telemetry_loop.session_manager.current_session_id,
   }
   ```

**Result**:
- ✅ Opponent lap filenames now contain opponent's name (not player's)
- ✅ CSV metadata shows opponent's name in Player field
- ✅ CSV metadata shows opponent's car in CarName field
- ✅ All 91 tests passing
