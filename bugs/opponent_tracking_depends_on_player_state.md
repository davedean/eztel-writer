# Bug: Opponent Tracking Depends on Player State

**Status**: FIXED ✅ (v0.2.1)
**Priority**: High (breaks core multiplayer feature)
**Discovered**: 2025-11-20 (v0.2.1 testing)
**Fixed**: 2025-11-20 (v0.2.1)
**Affects**: Opponent lap capture in all scenarios where player is inactive

---

## Description

Opponent laps are only tracked when the local player is actively driving. This means:

1. **Opponents not detected until player drives**: If player is in garage, opponent laps are not tracked even though opponents are driving
2. **Opponent laps not saved if player doesn't complete a lap**: If player stops mid-lap or goes to pits, opponent tracking stops
3. **Opponent tracking pauses when player is inactive**: When `_suspend_logging` is True (after player stops), opponent tracking is skipped entirely

## User Impact

**Scenario 1**: Player spectating in multiplayer
- Player joins session but stays in garage to watch
- Opponents complete laps
- **Expected**: Opponent laps are captured and saved
- **Actual**: No opponent laps captured (session is DETECTED, not LOGGING)

**Scenario 2**: Player crashes/goes to pits mid-lap
- Player is driving, opponent tracking works
- Player crashes or returns to pits (incomplete lap)
- Opponent completes a lap while player is stationary
- **Expected**: Opponent lap is captured and saved
- **Actual**: No opponent lap captured (`_suspend_logging = True`, early return)

**Scenario 3**: Player completes out-lap, stays in pits
- Player does 1 out-lap (incomplete), returns to pits
- Opponents continue racing and complete laps
- **Expected**: Opponent laps captured
- **Actual**: No opponent laps captured (player inactive, early return)

## Root Cause Analysis

### Issue #1: Opponent Tracking Inside Player Session Logic

**Location**: `src/telemetry_loop.py:188-202`

```python
# Read telemetry
try:
    telemetry = self.telemetry_reader.read()  # ← Player telemetry

    # Update session and check for events
    events = self.session_manager.update(telemetry, current_time)

    # ... player session logic ...

    # Poll opponents if enabled  ← PROBLEM: Inside player logic!
    if self.track_opponents and self.on_opponent_lap_complete:
        try:
            opponents = self.telemetry_reader.get_all_vehicles()
            for opponent_telemetry in opponents:
                completed_laps = self.opponent_tracker.update_opponent(
                    opponent_telemetry,
                    timestamp=current_time
                )
                # Trigger callback for each completed lap
                for opponent_lap_data in completed_laps:
                    self.on_opponent_lap_complete(opponent_lap_data)
        except Exception as e:
            # Don't fail the main loop if opponent tracking has issues
            pass
```

**Problem**: Opponent tracking is nested inside the player telemetry read/update block. If player session logic fails, pauses, or returns early, opponents are not tracked.

### Issue #2: Early Return When Player Inactive

**Location**: `src/telemetry_loop.py:172-179`

```python
if self._suspend_logging:
    if self._sample_indicates_active(telemetry):
        self._suspend_logging = False
    else:
        status['state'] = self.session_manager.state
        status['lap'] = self.session_manager.current_lap
        status['samples_buffered'] = len(self.session_manager.lap_samples)
        return status  # ← EARLY RETURN: Skips opponent tracking!
```

**Problem**: When `_suspend_logging` is True (set after player stops/crashes), the function returns early on line 179, completely skipping the opponent tracking code (lines 188-202).

**When does this happen?**
- Player completes incomplete lap (crash, pit entry, teleport)
- `_flush_lap(reason=stop_reason)` is called (line 165)
- `_suspend_logging = True` is set (line 168)
- Next iteration: early return on line 179
- Opponent tracking never runs

### Issue #3: Session State Dependency

**Location**: `src/telemetry_loop.py:181-183`

```python
if self.session_manager.state == SessionState.DETECTED:
    self.session_manager.state = SessionState.LOGGING
    self.session_manager.current_session_id = self.session_manager.generate_session_id()
```

**Problem**: Session only transitions to LOGGING when player starts driving. If player stays in garage:
- Session state: DETECTED (not LOGGING)
- Player telemetry available but player not moving
- Opponent tracking code runs, but session is not considered "active"

**Chain of events**:
1. Player in garage → `_sample_indicates_active()` returns False
2. `_suspend_logging` stays False initially
3. But session never transitions to LOGGING
4. Opponent tracking happens but feels incomplete/inconsistent

## Architecture Issue

The fundamental problem: **Opponent tracking is coupled to player session state**.

**Current design assumption**:
- Session = Player session
- Session LOGGING = Player is driving
- Opponents are "passengers" in the player's session

**Correct design**:
- Session = Multiplayer session (independent of player state)
- Player can be active or inactive
- Opponents are tracked independently of player

## Solution Options

### Option 1: Move Opponent Tracking Outside Player Session Logic ⭐ **RECOMMENDED**

Decouple opponent tracking from player session updates:

```python
def run_once(self) -> Optional[Dict[str, Any]]:
    # ... process detection, paused check, telemetry availability ...

    status['telemetry_available'] = True

    # Track opponents FIRST (independent of player state)
    if self.track_opponents and self.on_opponent_lap_complete:
        try:
            opponents = self.telemetry_reader.get_all_vehicles()
            for opponent_telemetry in opponents:
                completed_laps = self.opponent_tracker.update_opponent(
                    opponent_telemetry,
                    timestamp=current_time
                )
                for opponent_lap_data in completed_laps:
                    self.on_opponent_lap_complete(opponent_lap_data)
        except Exception as e:
            pass  # Don't block player session if opponent tracking fails

    # THEN handle player session (can return early without affecting opponents)
    try:
        telemetry = self.telemetry_reader.read()
        events = self.session_manager.update(telemetry, current_time)

        # ... rest of player session logic ...

        if self._suspend_logging:
            # Return early for player, but opponents already tracked above
            return status
```

**Pros**:
- ✅ Opponents tracked even when player inactive
- ✅ Minimal code changes
- ✅ Clear separation of concerns
- ✅ Early returns don't affect opponents

**Cons**:
- Opponents tracked even in single-player (negligible cost)

### Option 2: Separate Opponent Polling from Player Session

Create a separate method for opponent tracking:

```python
def _poll_opponents(self, current_time: float):
    """Poll and track opponents (independent of player state)"""
    if not self.track_opponents or not self.on_opponent_lap_complete:
        return

    try:
        opponents = self.telemetry_reader.get_all_vehicles()
        for opponent_telemetry in opponents:
            completed_laps = self.opponent_tracker.update_opponent(
                opponent_telemetry,
                timestamp=current_time
            )
            for opponent_lap_data in completed_laps:
                self.on_opponent_lap_complete(opponent_lap_data)
    except Exception as e:
        pass

def run_once(self) -> Optional[Dict[str, Any]]:
    # ... checks ...

    # Always poll opponents if telemetry available
    self._poll_opponents(current_time)

    # Handle player session separately
    # ... player logic ...
```

**Pros**:
- ✅ Very clear separation
- ✅ Easier to test
- ✅ Can add opponent-specific config/logic

**Cons**:
- More refactoring required

### Option 3: Dual Session Manager (Player + Multiplayer)

Create separate session managers for player and multiplayer:

```python
self.player_session = SessionManager(...)  # Player-specific
self.mp_session = MultiplayerSessionManager(...)  # Tracks overall session
```

**Pros**:
- ✅ Cleanest architecture
- ✅ Proper separation of player vs multiplayer state

**Cons**:
- ❌ Significant refactoring
- ❌ More complex
- ❌ Overkill for current requirements

## Implementation Plan (Option 1)

### Step 1: Identify the opponent tracking block

Current location: `src/telemetry_loop.py:188-202`

### Step 2: Move opponent tracking before player session update

```python
def run_once(self) -> Optional[Dict[str, Any]]:
    if not self._running:
        return None

    current_time = time.time()

    # ... status init, process detection, paused check ...

    # Check if telemetry is available
    if not self.telemetry_reader.is_available():
        status['telemetry_available'] = False
        self._suspend_logging = False
        return status

    status['telemetry_available'] = True

    # ========================================
    # OPPONENTS: Track independently of player
    # ========================================
    if self.track_opponents and self.on_opponent_lap_complete:
        try:
            opponents = self.telemetry_reader.get_all_vehicles()
            for opponent_telemetry in opponents:
                completed_laps = self.opponent_tracker.update_opponent(
                    opponent_telemetry,
                    timestamp=current_time
                )
                for opponent_lap_data in completed_laps:
                    self.on_opponent_lap_complete(opponent_lap_data)
        except Exception as e:
            pass  # Don't block player session

    # ========================================
    # PLAYER: Session management and lap tracking
    # ========================================
    try:
        telemetry = self.telemetry_reader.read()
        events = self.session_manager.update(telemetry, current_time)

        # ... rest of player logic (unchanged) ...
```

### Step 3: Remove opponent tracking from old location

Delete lines 188-202 (the opponent tracking block inside player logic)

### Step 4: Update tests

Tests that might need updates:
- `test_telemetry_loop.py` - Verify opponent tracking works when player inactive
- Add test: "opponent laps tracked when player in garage"
- Add test: "opponent laps tracked when player stopped mid-lap"

### Step 5: Test scenarios

**Test 1**: Player in garage
- Join multiplayer session
- Stay in garage (don't drive)
- Wait for opponent to complete lap
- **Expected**: Opponent lap saved

**Test 2**: Player crashes mid-lap
- Start driving
- Stop mid-lap (trigger `_suspend_logging`)
- Wait for opponent to complete lap
- **Expected**: Opponent lap saved

**Test 3**: Player does out-lap
- Complete incomplete lap (out-lap)
- Stay in pits
- Wait for opponent to complete lap
- **Expected**: Opponent lap saved

## Testing Checklist

- [ ] Opponent laps tracked when player in garage (DETECTED state)
- [ ] Opponent laps tracked when `_suspend_logging = True`
- [ ] Opponent laps tracked when player crashes/stops mid-lap
- [ ] Player laps still work normally
- [ ] No errors when opponent tracking fails
- [ ] Unit tests pass
- [ ] Integration test: multiplayer session on Windows

## Affected Files

**To Modify**:
- `src/telemetry_loop.py` - Move opponent tracking block (lines 188-202 → earlier)

**To Test**:
- `tests/test_telemetry_loop.py` - Add tests for opponent tracking independence

## Estimated Effort

- **Fix**: 30 minutes (move code block, test locally)
- **Testing**: 1 hour (unit tests + manual multiplayer testing)
- **Total**: ~1.5 hours

## Priority Justification

**High Priority** because:
- ❌ Breaks core opponent tracking feature
- ❌ Makes opponent tracking unreliable in normal use
- ❌ Affects all multiplayer scenarios
- ✅ Simple fix (move code block)
- ✅ Should be fixed before v0.2.1 release

## Related Bugs

This bug is separate from the v0.2.1 bugs (mCurrentET and metadata) but should be fixed in the same release since it affects the same feature (opponent tracking).

## Additional Notes

This bug reveals a fundamental architectural coupling: opponent tracking was initially implemented as a "bonus feature" within the player session loop. For robust multiplayer support, opponent tracking needs to be first-class and independent.

Future consideration: If we add more multiplayer features (e.g., session-wide statistics, leader boards), we should create a proper MultiplayerSessionManager that operates independently of the player's state.

## Fix Summary (v0.2.1)

**Implementation**: Option 1 (Move Opponent Tracking Outside Player Session Logic) ⭐

**Changes Made**:

1. **src/telemetry_loop.py:151-172** - Moved opponent tracking before player session logic
   - Opponent tracking now executes immediately after telemetry availability check
   - Placed BEFORE player session update (line 179)
   - Added clear section separators with comments

2. **src/telemetry_loop.py:214-217** - Removed duplicate opponent tracking
   - Deleted old opponent tracking block that was nested inside player logic
   - Removed duplicate `opponents_tracked` status update

3. **tests/test_telemetry_loop.py** - Added comprehensive tests
   - New test: `test_opponent_tracking_works_when_player_in_garage` (line 388)
     - Verifies opponents tracked when player is stationary (DETECTED state)
   - New test: `test_opponent_tracking_works_when_player_suspended` (line 453)
     - Verifies opponents tracked when `_suspend_logging = True` (player crashed/pits)

**Code Flow (After Fix)**:
```
run_once() {
    1. Check process running
    2. Check telemetry available
    3. → TRACK OPPONENTS (independent, always runs)
    4. → Track player session (can return early without affecting opponents)
}
```

**Result**:
- ✅ Opponents tracked when player in garage
- ✅ Opponents tracked when player suspended
- ✅ Opponents tracked when player crashes/pits
- ✅ Early returns don't skip opponent tracking
- ✅ All 93 tests passing

**Testing**:
- 2 new unit tests added specifically for this fix
- Both test scenarios that previously failed
- All existing tests still pass (no regressions)
