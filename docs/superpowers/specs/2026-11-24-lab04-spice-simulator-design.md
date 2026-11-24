# Lab 04 BJT Amplifier Simulator v1 — Design

Date: 2026-11-24

## Intent

Lab 03 already delivers a trustworthy analytical DC bias calculator with 37 passing tests. Lab 04 must add a **real ngspice-driven CE amplifier simulator** without disturbing that baseline. The web app should visibly separate analytical results from SPICE results, show real DC `.op`, AC `.ac`, and transient `.tran` output, and be honest when the engine or starter files are unavailable.

## Goals

- Preserve Lab 03 routes, inputs, outputs, and all 37 tests unchanged.
- Add one top-level `analysis` selector with:
  - `bias` — existing analytical Lab 03 calculator (default).
  - `dc` — SPICE DC operating point.
  - `ac` — SPICE AC frequency response.
  - `tran` — SPICE transient waveform.
- Use a fixed CE voltage-divider reference circuit for all SPICE modes, with editable fixture values: VCC, R1, R2, RC, RE, RL, Cin, Cout, source amplitude, source frequency.
- Call a real `ngspice_con`/`ngspice` executable with an argument list, timeout, and no `shell=True`.
- Parse real output files produced by ngspice `.control` + `wrdata`; never hard-code result numbers or plots.
- Render server-side SVG charts from parsed samples; no chart-library dependency.
- Show provenance: engine executable, version, BJT model name/source, fixture inputs, analysis type, raw row counts, and run status.
- Record browser acceptance B1–B8 honestly in `docs/validation.md`, naming the actual browser tooling used.

## Non-goals / anti-goals

- No rewrite of `dc_bias.py` or the Lab 03 form contract.
- No JavaScript-side engineering calculation.
- No fabricated values, fake Success badge, or stale results after an error.
- No claim that the BJT model came from an instructor Starter Kit.
- No `git commit` by the assistant; the user commits and pushes with GitHub Desktop.

## Constraints and current state

- `AGENTS.md`: engineering equations stay in `dc_bias.py`; `app.py` owns parsing, unit conversion, validation, and HTTP status; templates only display.
- `requirements.txt` currently contains only `Flask>=3.0`; no new dependency is required for SVG plots.
- Lab 03 baseline commit: `8dc92475dd4d2c0ddf9e3eb8aa75499466da3c7e`; working tree was clean before Lab 04 work.
- Python 3.14.2, Flask 3.1.3, `python -m unittest discover -s tests -v` reports 37 tests OK.
- `node`, `npx`, and Playwright MCP are unavailable. OpenCode Browser is the accepted fallback and must be reported as such.
- No instructor Starter Kit, netlist, or BJT model was found in Downloads. ngspice was not on `PATH` and `winget --source winget` has no ngspice package.

## Spike findings

- Downloaded official ngspice 47 Windows 64-bit archive from SourceForge to a temp folder (outside the repo).
- `Spice64\bin\ngspice_con.exe -v` reports `ngspice-47`; the GUI `ngspice.exe` blocks on stdin and must not be used.
- Batch mode works with `.control` + `wrdata`. Each requested trace is written as an `(x, y)` pair, e.g. `wrdata ac.csv vm(out) vp(out)` gives columns `[freq, vm, freq, vp]`; `wrdata tran.csv v(out)` gives `[time, vout]`.
- Device currents are available directly from ngspice with `@q1[ic]`, `@q1[ib]`, `@q1[ie]`, so the engine does not need to re-derive DC bias currents.
- `ngspice_con` writes `wrdata` files relative to the process working directory, so each run gets its own temp directory.
- A documented teaching NPN model with `Is/Bf/Vaf/Cje/Cjc/Tf` is sufficient for all three analyses.

## Approaches considered

1. **Add a simulator mode to the existing page (chosen).** Minimal change to `app.py`, one new engine module, one template, and SVG plots from real data. Keeps Lab 03 untouched and avoids new dependencies.
2. **Separate `/simulator` route and page.** Cleaner visual boundary but adds navigation and duplicated form/validation work.
3. **Full UI rewrite with tabs and a JS chart library.** Best-looking but adds dependencies and creates avoidable regression risk to the accepted Lab 03 behaviour.

The user chose approach 1.

## Decisions

- **Model provenance:** create `models/bjt_teaching.lib` with a clearly documented teaching model. Show `Teaching NPN (project-defined; Starter Kit unavailable)` in the UI and docs. This is a model choice, not a fabricated result.
- **Engine location:** `spice_engine.py` owns netlist generation, executable discovery, subprocess execution, `wrdata` parsing, and typed engine errors. It does not replace `dc_bias.py`.
- **Executable discovery:** check `NGSPICE_CMD` first, then `shutil.which("ngspice_con")`, then `shutil.which("ngspice")`. Missing engine yields a clear `UNAVAILABLE` status with HTTP 200 and no results.
- **Error policy:** invalid user input keeps the existing Lab 03 convention (HTTP 400 with per-field errors and no results). Engine failure, timeout, empty output, or parse failure yields HTTP 200 with `ERROR` status, an error message, and no stale result blocks.
- **Units:** SPICE inputs use explicit unit selects. `app.py` converts every value to SI before calling the engine; the engine formats SI to SPICE suffixes (`k`, `u`, `n`, `p`, `meg`).
- **Plots:** server-rendered inline SVG. AC chart uses log frequency on x and gain dB on y. Transient chart uses time on x and output volts on y. Both use at most ~1200 downsampled real points.
- **AC metric:** report gain dB, magnitude, and phase by finding the parsed sample nearest the requested source frequency; never invent an interpolated value without labelling it.
- **Transient metric:** report peak-to-peak and last-cycle peak from parsed output samples; label them as measured from the simulated waveform.
- **Validation:** use OpenCode Browser, not Playwright MCP. Record B1–B8 with expected/observed/evidence/status; use `NOT RUN` only if a check truly cannot be executed.

## Implementation contracts (answers from the builder check)

These are calls made from the handout, the spike, and the existing app structure; they are not left to the builder.

- **B1–B8 source:** the eight checks are defined in the Lab 04 handout (lines 538–545): B1 Lab 03 regression, B2 DC SPICE, B3 change RE, B4 AC Bode, B5 transient at 10 mV/1 kHz with phase inversion, B6 change source, B7 invalid/engine failure, B8 desktop/mobile UI. They will be copied into `docs/validation.md` with expected/observed/evidence/status.
- **AC contract:** ideal source (no series resistance), unbypassed RE (no `CE`), `.ac dec 10 10 10meg`. Gain reference is the source node `IN` before `Cin`: `gain_db = 20·log10(vm(out)/vm(in))` and `phase = vp(out) − vp(in)` wrapped to −180…+180°. If the requested frequency is outside the swept range, show the chart but report `not determined in sweep range` instead of inventing a marker value.
- **Transient contract:** `.tran` uses a maximum step of `stop/2000` and `stop = min(max(5/frequency, 1 ms), 20 ms)`, so 1 kHz gives 5 ms and about five cycles. Request `v(in)` and `v(out)`; report peak-to-peak from the final one-period window and half of that span as `peak (last cycle)`. Report inversion by the sign of the input/output correlation in that window. Downsample to at most 1200 points for SVG.
- **Default SPICE fixture:** VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ, RL 10 kΩ, Cin 10 µF, Cout 10 µF, amplitude 10 mV peak, frequency 1 kHz. All resistances, capacitances, amplitude, and frequency must be finite and > 0; β and VBE are not SPICE inputs because the model owns them.
- **DC parser contract:** `.control` writes `wrdata op.csv v(b) v(e) v(c) v(c,e) @q1[ic] @q1[ib] @q1[ie]`. Each vector is an `(x, y)` pair, so the parser reads the odd columns as VB, VE, VC, VCE, IC, IB, IE in volts/amperes. Missing, non-numeric, or empty CSV is an engine error, never a blank Success.
- **SPICE DC display:** show only the seven ngspice values above plus run status and provenance. Do not show an analytical table or a derived region badge in SPICE mode; the Analytical results live only in `bias` mode, and the UI states that the two use different assumptions.
- **Analytical vs SPICE agreement:** not required to match every digit. The teaching model has its own `Is`, `Bf`, `Vaf`, capacitances, and `Tf`; it is documented in `models/bjt_teaching.lib` and shown in the UI. Validation compares each source to its own contract, not to forced equality.
- **Engine availability:** binaries are not committed. README instructs adding the ngspice `bin` directory to `PATH` or setting `NGSPICE_CMD` to `ngspice_con.exe`. Local browser validation starts Flask with `NGSPICE_CMD` pointing at the extracted ngspice 47 console binary outside the repo; if that run cannot be reproduced, B2–B6 are marked `NOT RUN` honestly.
- **Analysis selection:** `analysis` is a GET selector like the existing `mode` selector (`/?analysis=dc`). In SPICE modes the Lab 03 `mode` dropdown is hidden and its value ignored; POST still uses `/calculate` with hidden `analysis`. The `bias` path and all 37 existing tests stay byte-for-byte compatible.

## What is left to the builder

- Exact field names and labels in the form, following existing snake_case conventions.
- Exact chart dimensions/colors, matching `static/style.css`.
- Test doubles for subprocess/CSV parsing so unit tests do not require ngspice on `PATH`.
- Final commit message and GitHub Desktop steps are the user's responsibility.
