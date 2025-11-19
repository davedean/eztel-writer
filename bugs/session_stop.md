# Telemetry loop keeps writing after driver leaves the track

**Status:** Open  
**Reported by:** Internal dev (Codex relay)  
**Date:** 2025-01-17

## Summary
When the driver exits to garage or otherwise leaves the racing surface, the logger continues to append telemetry rows to the current CSV until another lap-complete event occurs later. Because no new lap boundary is detected, samples accumulate indefinitely and produce a single, extremely long lap with meaningless timing data.

## Reproduction
1. Start the logger and begin a driving session (LMU mock or real sim).  
2. Drive at least one lap so logging begins.  
3. Exit to pits/garage or pause the sim so the car no longer advances along the lap.  
4. Observe that the logger keeps writing repeated samples (lap distance stagnates, lap time keeps increasing) until a later lap-complete event is triggered.

## Expected
- Logging should stop (flush + finalize lap) when we leave the session, teleport to pits, pause the sim, or otherwise stop receiving forward progress.
- CSV files should contain only valid laps; idle/paused time should not be merged into the previous lap.

## Actual
- `SessionManager` only closes a lap when `lap` increments. If the sim returns to pit lane without incrementing the lap counter, the buffer never flushes.
- `TelemetryLoop` keeps calling `session_manager.add_sample()` with stale telemetry, so the CSV grows indefinitely until another `lap_completed` event occurs.

## Suggested Detection Signals
We should treat the following events as "stop logging / flush current lap" conditions:
- **Session change:** `session_type`, `event_id`, or sim-specific session UUID changes (race → practice, etc.).
- **Vehicle inactive:** Speed and engine RPM drop below thresholds for N seconds (e.g., speed < 1 km/h AND throttle ≈ 0).
- **Pit/garage teleport:** Telemetry flag indicating pit location, or large instantaneous jump in world coordinates to known pit position.
- **Sim pause / menu:** Process still running but telemetry `is_available()` flips false, or sample timestamps stop advancing.
- **Manual stop:** Monitor when the target process closes (already handled, but ensure buffers flush immediately).

Implementation ideas:
1. Extend `SessionManager.update()` to emit `session_stopped` events when any of the above heuristics trigger, then flush/write the buffered lap.
2. Add configurable thresholds/timeouts in config (e.g., `idle_timeout_seconds`, `min_speed_to_log`).
3. Consider writing a partial lap with a special metadata flag (e.g., `LapComplete=false`) so downstream tools can ignore it.

Without these stop conditions, CSV outputs remain unreliable whenever the driver returns to pits or pauses mid-session.

