# iRacing Telemetry Support – Feasibility Analysis

**Author:** Codex agent  
**Date:** 2025-01-17  
**Scope:** Evaluate the engineering effort, risks, and architectural deltas required to extend the existing LMU telemetry writer to ingest telemetry from iRacing while continuing to emit the LMUTelemetry v2 CSV format.

---

## 1. Context Snapshot

- The current stack (`src/telemetry_writer`) targets Le Mans Ultimate on Windows, using the rFactor 2 shared-memory plugin through `pyRfactor2SharedMemory` and a mock reader for macOS development. Telemetry is ingested via `TelemetryReaderInterface` (`src/telemetry/telemetry_interface.py`) and normalized by `SampleNormalizer` in `src/mvp_format.py` before CSV emission.
- Process lifecycle is tied to a single executable name (`LMU.exe`) through `ProcessMonitor` (`src/process_monitor.py`), and `TelemetryLoop` (`src/telemetry_loop.py`) assumes one active sim/source per run.
- CSV format + metadata are shared across sims, so as long as we can provide the canonical 12 telemetry channels and minimal metadata, downstream tooling stays unchanged.
- Goal for iRacing: reuse the same polling loop, session management, and formatting/persistence layers; only swap the telemetry acquisition, process detection, and per-sim metadata adapters.

---

## 2. Proposed Integration Approach

### 2.1 Telemetry Acquisition Layer

| Item | Recommendation | Notes |
| --- | --- | --- |
| SDK / API | Use the official iRacing shared memory via `irsdk` (https://github.com/kutu/pyirsdk or iRacing’s sample `irsdk` Python bindings). | Provides Python access to live telemetry, session strings, and driver data at ~60 Hz (physics) + event-driven updates. |
| Reader implementation | Create `IRacingTelemetryReader(TelemetryReaderInterface)` inside `src/telemetry/telemetry_iracing.py`. | Mirrors `telemetry_real.py` but backed by `irsdk.IRSDK`. Handle `self.ir.startup()` / `self.ir.shutdown()` lifecycle and field caching. |
| Availability detection | `is_available()` should check `iracing.is_initialized` and optionally verify that the sim is running (SDK exposes `is_connected`). | Allows `TelemetryLoop` to stay generic. |
| Polling cadence | iRacing publishes new physics packets every 1/60th second and events at lower frequency. Our loop already polls at 100 Hz; we can either throttle (sleep until `iracing.is_connected` and `iracing.fps`) or keep current interval and drop duplicate packets using `iracing.get_session_info_update()` timestamps. |

### 2.2 Multisim Selection

1. Introduce a new top-level config knob (env var, CLI parameter, or `config.json`) for `sim` with enumerations `LMU`, `IRACING`, `AUTO`.
2. Update `get_telemetry_reader()` to:
   - Honor explicit sim selection.
   - When `AUTO`, prefer LMU on machines with rF2 plugin detected, else probe for iRacing (check running processes and attempt SDK attach).
3. Allow `ProcessMonitor` to accept a list of process names; for iRacing we watch `iRacingSim64DX11.exe` and optionally the 32-bit executable. When multiple sims are enabled, detection order decides which telemetry adapter starts.

### 2.3 Data Normalization

- Extend `SampleNormalizer` mappings if needed, but the canonical 12 channels already align closely with iRacing telemetry names.
- Add an iRacing-specific translation layer inside the new telemetry reader so raw SDK values are emitted using the same keys the LMU pipeline expects (e.g., `lap_distance`, `speed`, `gear`).
- Compute derived values when iRacing does not provide them directly (see §3).
- Session metadata (player, car, track) can be pulled from `WeekendInfo` and `DriverInfo` strings via `irsdk` helpers.

### 2.4 File Output / Lifecycle

- No changes to `CSVFormatter`, `FileManager`, or the telemetry loop contract are required once telemetry samples conform to the normalized schema.
- Optional: annotate metadata with `SimName = iRacing` so downstream analytics can differentiate laps.

---

## 3. Data Mapping Readiness

| LMU canonical field | iRacing SDK reference | Mapping + Notes |
| --- | --- | --- |
| `LapDistance [m]` | `LapDist` (meters) | Direct meters already provided. For replays, compute via `LapDistPct * TrackLength`. |
| `LapTime [s]` | `LapCurrentLapTime` (seconds) | Falls back to integrating `Speed` if unavailable (during formation laps). |
| `Sector [int]` | `SplitTimeInfo.Sectors` / `CarIdxLapDistPct` | Use `LapDistPct` vs. `WeekendInfo.NumSectors`; convert to 0‑based. |
| `Speed [km/h]` | `Speed` (m/s) | Multiply by 3.6. |
| `EngineRevs [rpm]` | `RPM` | Already rpm. |
| `ThrottlePercentage [%]` | `Throttle` (0‑1) | Multiply by 100, clamp 0–100. |
| `BrakePercentage [%]` | `Brake` (0‑1) | Multiply by 100. |
| `Steer [%]` | `SteeringWheelAngle` (radians) | Convert to -100..100 by dividing by `SteeringWheelAngleMax` and scaling. |
| `Gear [int]` | `Gear` | Already int. |
| `X [m]`, `Y [m]`, `Z [m]` | `CarIdxTrackSurface`, `CarIdxWorldPosition` arrays | Use player car index from `DriverInfo.DriverCarIdx`. Coordinates expose North/Up/East (in meters). Map to our `X/Z` plane and treat Up as `Y`. |
| Metadata: `Player`, `CarName`, `TrackName`, `TrackLen [m]` | `DriverInfo`, `WeekendInfo`, `SessionInfo` | All available via JSON-like YAML in the SDK strings. |

**Derivative values needed**
- `sector_index`: compute from `LapDistPct * num_sectors`.
- `lap`: use `CarIdxLap` for the player car.
- `session_type`: map `SessionInfo.Sessions[..].SessionType`.

No blockers surfaced—every required column is accessible with either a direct channel or trivial math.

---

## 4. Required Code Enhancements

| Area | Description | Est. Effort |
| --- | --- | --- |
| Telemetry reader | Implement `telemetry_iracing.py` with lifecycle handling, field mapping, and metadata extraction. | 1.5–2 days (includes validation + docstrings). |
| Factory & config | Update `telemetry_interface.get_telemetry_reader()` and add configuration plumbing (e.g., `config['sim']`). Introduce simple enum + error handling. | 0.5 day. |
| Process monitoring | Allow multiple target processes + per-sim overrides (maybe `ProcessMonitor(config, process_list)` or new `SimProcessMonitor`). | 0.5 day. |
| Tests | Add mocks for `irsdk` (simulate key channels), cover reader behaviour, and exercise multi-sim factory logic. | 1 day. |
| Packaging | Include `irsdk` dependency in `requirements*.txt`, gate Windows-only install, and document setup in README/WINDOWS_SETUP. | 0.5 day. |
| Integration manual | Update `TECHNICAL_SPEC.md`, `USER_GUIDE.md`, plus a short troubleshooting section for SDK connectivity. | 0.5 day. |

**Total:** ~4–5 engineering days for an initial CLI-only release, assuming access to an iRacing Windows machine for final validation.

---

## 5. Testing Strategy

1. **Unit tests:** Mock the `irsdk.IRSDK` object to return deterministic telemetry frames; assert normalization, metadata, and failure modes (e.g., disconnected sim).
2. **Integration tests (Windows):** Spin up iRacing test session, run logger in AUTO mode, confirm lap CSV output matches spec and retains 100 Hz-ish sampling without packet drops.
3. **Regression:** Ensure LMU path remains unaffected by running the full pytest suite on macOS using the existing mock reader and verifying `sim=LMU`.
4. **Performance sampling:** Profile CPU usage when both `LMU` and `IRACING` sims are enabled in AUTO mode to ensure process scanning and telemetry switching stay light.

---

## 6. Risks & Unknowns

- **SDK licensing/EULA:** iRacing’s API is intended for members; redistributing the SDK DLLs may be disallowed. Need to confirm we can vendor the Python bindings or require users to copy `irsdk.dll` themselves.
- **Sim exclusivity:** iRacing and LMU cannot run simultaneously. AUTO-detect logic must handle race conditions where one sim closes and the other starts mid-session—consider requiring a restart when switching sims.
- **Coordinate frames:** iRacing world coordinates are North-East-Up; our viewer expects a planar X/Z around the track. Need to verify axes orientation so maps are not mirrored.
- **Sampling mismatch:** iRacing physics at 60 Hz vs. LMU target of ~100 Hz. Upsampling is unnecessary, but we should ensure we do not over-sample empty frames—`irsdk` exposes a `var_headers` timestamp to detect new data.
- **Windows-only:** iRacing does not run on macOS; developers will rely on mocks. Need recorded telemetry captures (irsdk `.ibt` replays) to drive automated tests.
- **Future channel divergence:** Optional columns (tyre temps, suspension) differ in naming units. Document expectations so later “rich” exports can branch per sim without breaking base CSV.

Mitigations involve thorough docs, platform guards, and recorded sample data for macOS testing.

---

## 7. Dependencies & Tooling

- Add `irsdk` (or `pyirsdk`) to `requirements-windows.txt`; guard installation with `sys_platform == 'win32'`.
- Require `iRacingSim64DX11.exe` presence or `Documents/iRacing/telemetry` folder as heuristics.
- Optional: vendor a thin wrapper around `irsdk` to ensure consistent error handling and to stub in tests.
- Provide a setup checklist in `WINDOWS_SETUP.md` (enable telemetry, configure `app.ini` `irsdkEnableMem=1`, ensure firewall allows local shared memory).

---

## 8. Recommendation & Next Steps

Extending the telemetry writer to iRacing is **feasible** with manageable engineering effort because:

1. The architecture already abstracts telemetry acquisition through `TelemetryReaderInterface`.
2. iRacing exposes all required data fields via the shared memory SDK with compatible units.
3. CSV formatting, session management, and storage layers remain untouched.

**Suggested next actions**

1. Decide on configuration UX (`sim` flag + AUTO detection policy).
2. Prototype `IRacingTelemetryReader` using recorded `.ibt` telemetry to validate mapping.
3. Expand process monitoring + factory selection, then wire unit tests.
4. Validate on Windows with live iRacing session, collect one end-to-end CSV for regression comparisons.
5. Update documentation + onboarding scripts to cover the iRacing pathway.

Delivering the above yields dual-sim support with minimal disruption to the existing LMU workflow.

