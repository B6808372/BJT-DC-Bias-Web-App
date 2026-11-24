# Lab 04 BJT Amplifier Simulator v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real ngspice DC, AC, and transient simulation to the existing Flask app without changing Lab 03 analytical behaviour or its 37 tests.

**Architecture:** Keep `app.py` as the HTTP/form/unit layer and `dc_bias.py` untouched as the analytical reference. Add `spice_engine.py` as the only SPICE adapter: it builds a netlist, runs `ngspice_con`/`ngspice` with a timeout in an isolated temp directory, parses `wrdata` CSV pairs, and returns typed results or typed errors. Extend the existing Jinja page with an `analysis` selector and server-rendered SVG charts from those parsed samples.

**Tech Stack:** Python 3.14, Flask 3.1, standard library (`subprocess`, `tempfile`, `csv`, `shutil`, `unittest`), ngspice 47 console binary, inline SVG, no new pip dependencies.

**Spec:** `docs/superpowers/specs/2026-11-24-lab04-spice-simulator-design.md`

## Global Constraints

- Preserve `dc_bias.py`, `POST /calculate` Lab 03 dispatch, and all 37 existing tests unchanged.
- Engineering equations stay in `dc_bias.py`; templates and JavaScript must not compute engineering values.
- `app.py` owns form parsing, unit conversion, validation, and HTTP status: valid input → 200, invalid input → 400.
- Engine failure, timeout, missing binary, empty output, or parse failure → HTTP 200 with `UNAVAILABLE`/`ERROR` status and **no** stale results.
- `subprocess.run` must receive an argument list, set `timeout`, and never use `shell=True`.
- No fabricated values, hard-coded plots, fake Success badge, or committed ngspice binary.
- `requirements.txt` stays `Flask>=3.0` because SVG needs no dependency.
- The assistant must not run `git commit`; the user commits and pushes via GitHub Desktop.
- Browser validation must be reported as **OpenCode Browser**, not Playwright MCP, because `node`/`npx` are unavailable.

## Review Focus

- **ngspice missing or not on PATH** → expect a clear `UNAVAILABLE` status, no spinner stuck and no results; pinned in Task 1 (`find_engine` returns None) and Task 5 (web renders no SPICE result).
- **RE = 0 or invalid unit** → expect HTTP 400 with a per-field error and no results; pinned in Task 5.
- **Empty/truncated `wrdata` output** → expect `EngineOutputError`, never an empty Success result; pinned in Tasks 2, 3, and 4.
- **Requested frequency outside the `.ac` sweep** → expect the chart plus `not determined in sweep range`, not an invented marker; pinned in Task 3.
- **Engine error after a previous successful run** → expect old result blocks to disappear; pinned in Task 5.

---

## File Structure

- Create `models/bjt_teaching.lib` — documented project-defined teaching NPN model `QT_NPN`.
- Create `spice_engine.py` — netlist building, executable discovery, subprocess execution, `wrdata` parsing, typed errors, result DTOs.
- Create `tests/test_spice_engine.py` — unit tests with fake `subprocess.run` output.
- Create `tests/test_web_lab04.py` — Flask tests for SPICE GET/POST paths and error policy.
- Modify `app.py` — add `analysis` constants, SPICE form parsing, engine dispatch, render context, SVG coordinate helpers.
- Modify `templates/index.html` — analysis selector, SPICE inputs, SPICE result cards, provenance, SVG charts.
- Modify `static/style.css` — badges, status panel, chart and responsive rules.
- Modify `README.md` — ngspice install/PATH/`NGSPICE_CMD`, new modes, limits.
- Modify `docs/validation.md` — B1–B8 table, ngspice/model version evidence, honest statuses.
- Modify `docs/reflection.md` — Lab 04 learning reflection.

---

## Task 1: Teaching model, engine discovery, netlist and typed errors

**Files:**
- Create: `models/bjt_teaching.lib`
- Create: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Consumes: SI values dict from `app.py` (`vcc`, `r1`, `r2`, `rc`, `re`, `rl`, `cin`, `cout`, `source_amp_v`, `source_freq_hz`).
- Produces:
  - `find_engine() -> str | None`
  - `format_spice_value(value: float) -> str`
  - `build_netlist(analysis: str, values_si: dict[str, float]) -> str` for `analysis in {"dc", "ac", "tran"}`
  - `SpiceError`, `EngineUnavailable`, `EngineRunError`, `EngineTimeout`, `EngineOutputError`
  - `MODEL_NAME = "QT_NPN teaching model"`, `MODEL_PATH: Path`

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from unittest.mock import Mock, patch
from spice_engine import (
    EngineUnavailable,
    build_netlist,
    find_engine,
    format_spice_value,
)

VALUES = {
    "vcc": 12.0, "r1": 100e3, "r2": 22e3, "rc": 2.2e3, "re": 1e3,
    "rl": 10e3, "cin": 10e-6, "cout": 10e-6,
    "source_amp_v": 10e-3, "source_freq_hz": 1e3,
}

class TestEngineBasics(unittest.TestCase):
    def test_format_spice_value_uses_engineering_suffixes(self):
        self.assertEqual(format_spice_value(100e3), "100k")
        self.assertEqual(format_spice_value(10e-6), "10u")
        self.assertEqual(format_spice_value(1e6), "1meg")

    def test_find_engine_uses_env_first(self):
        with patch.dict("os.environ", {"NGSPICE_CMD": r"C:\tools\ngspice_con.exe"}):
            self.assertEqual(find_engine(), r"C:\tools\ngspice_con.exe")

    def test_find_engine_returns_none_when_absent(self):
        with patch.dict("os.environ", {}, clear=True), patch("shutil.which", return_value=None):
            self.assertIsNone(find_engine())

    def test_engine_unavailable_is_typed(self):
        self.assertTrue(issubclass(EngineUnavailable, Exception))

    def test_dc_netlist_has_model_include_and_op_traces(self):
        net = build_netlist("dc", VALUES)
        self.assertIn(".include", net)
        self.assertIn("QT_NPN", net)
        self.assertIn("wrdata op.csv v(b) v(e) v(c) v(c,e) @q1[ic] @q1[ib] @q1[ie]", net)
        self.assertNotIn("shell", net)

    def test_ac_netlist_has_dec_sweep_and_gain_reference(self):
        net = build_netlist("ac", VALUES)
        self.assertIn("ac dec 10 10 10meg", net)
        self.assertIn("wrdata ac.csv vm(in) vp(in) vm(out) vp(out)", net)

    def test_tran_netlist_has_five_cycles_at_fixture_frequency(self):
        net = build_netlist("tran", VALUES)
        self.assertIn("tran 2.5u 5m", net)
        self.assertIn("wrdata tran.csv v(in) v(out)", net)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_spice_engine -v`
Expected: FAIL with module/function not found.

- [ ] **Step 3: Create the teaching model**

Write `models/bjt_teaching.lib` with a comment block stating: project-defined teaching model, not from an instructor Starter Kit, used for reproducible SPICE runs only. Define `.model QT_NPN NPN(...)` with `Is`, `Bf`, `Vaf`, `Cje`, `Cjc`, `Tf`, `Rb`, `Rc` parameters. Use the same model name constant in `spice_engine.py`.

- [ ] **Step 4: Implement Task 1 interfaces in `spice_engine.py`**

Use `os.environ.get("NGSPICE_CMD")`, then `shutil.which("ngspice_con")`, then `shutil.which("ngspice")`. Build a common CE voltage-divider netlist with nodes `VCC, IN, B, C, E, OUT`, source `VIN IN 0 DC 0 AC {amp} SIN(0 {amp} {freq} 0 0)`, and `QT_NPN`. Convert -c `/` in the model path so Windows `.include` works. Format suffixes in `p/n/u/k/meg` order. Compute transient `stop = min(max(5/freq, 1e-3), 20e-3)` and `max_step = stop/2000`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m unittest tests.test_spice_engine -v`
Expected: PASS (7 tests).

- [ ] **Step 6: User commit checkpoint**

Ask the user to commit via GitHub Desktop: `feat: add ngspice adapter and teaching BJT model`. Do not run `git commit`.

---

## Task 2: DC `.op` run and parser

**Files:**
- Modify: `spice_engine.py`
- Modify: `tests/test_spice_engine.py`

**Interfaces:**
- Consumes: `build_netlist`, typed errors, and `find_engine` from Task 1.
- Produces:
  - `parse_wrdata(text: str, series_count: int) -> list[list[tuple[float, float]]]`
  - `parse_op(csv_text: str) -> dict[str, float]` returning `vb_v, ve_v, vc_v, vce_v, ic_a, ib_a, ie_a`
  - `engine_version(executable: str) -> str`
  - `run_analysis(analysis: str, values_si: dict[str, float]) -> dict`

- [ ] **Step 1: Write the failing tests**

```python
OP_CSV = (
    " 1.20000000e+01  2.04760600e+00 "
    " 1.20000000e+01  1.38589024e+00 "
    " 1.20000000e+01  8.96523352e+00 "
    " 1.20000000e+01  7.57934329e+00 "
    " 1.20000000e+01  1.37985457e-03 "
    " 1.20000000e+01  6.45287992e-06 "
    " 1.20000000e+01  1.40000000e-02 \n"
)

class TestDcAnalysis(unittest.TestCase):
    def test_parse_wrdata_groups_even_odd_columns(self):
        series = parse_wrdata(OP_CSV, 7)
        self.assertEqual(len(series), 7)
        self.assertAlmostEqual(series[1][0][1], 1.38589024, places=8)

    def test_parse_op_reads_device_currents_not_derived_values(self):
        op = parse_op(OP_CSV)
        self.assertAlmostEqual(op["vb_v"], 2.047606, places=6)
        self.assertAlmostEqual(op["ic_a"], 1.37985457e-3, places=9)
        self.assertAlmostEqual(op["ib_a"], 6.45287992e-6, places=9)

    def test_parse_op_rejects_empty_csv(self):
        with self.assertRaises(EngineOutputError):
            parse_op("")

    def test_run_dc_calls_binary_without_shell_and_parses_real_csv(self):
        fake = Mock(
            return_value=Mock(returncode=0, stdout="ok", stderr="")
        )
        with patch("spice_engine.find_engine", return_value="ngspice_con"), \
             patch("spice_engine.subprocess.run", fake), \
             patch("spice_engine.Path.read_text", return_value=OP_CSV):
            result = run_analysis("dc", VALUES)
        self.assertEqual(result["status"], "OK")
        self.assertAlmostEqual(result["op"]["ic_a"], 1.37985457e-3, places=9)
        self.assertIsNone(fake.call_args.kwargs.get("shell"))

    def test_engine_version_parses_banner(self):
        with patch("spice_engine.subprocess.run", return_value=Mock(
            stdout="** ngspice-47 : Circuit level simulation program", stderr=""
        )):
            self.assertEqual(engine_version("ngspice_con"), "ngspice-47")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_spice_engine -v`
Expected: FAIL with `parse_wrdata` / `parse_op` / `run_analysis` not defined.

- [ ] **Step 3: Implement the parser and DC runner**

`parse_wrdata` pairs tokens `0-1, 2-3, ...` per row and returns one `(x, y)` series per requested vector; raise `EngineOutputError` on empty text, non-numeric tokens, or wrong column count. `run_analysis` uses `tempfile.TemporaryDirectory()`, writes `case.cir`, calls `[engine, "-b", "case.cir"]` with `cwd=run_dir`, `capture_output=True`, `text=True`, `timeout=20`, then reads the expected CSV. Raise `EngineRunError` for nonzero return or missing file, `EngineTimeout` for timeout, `EngineUnavailable` when `find_engine()` is None. Include `provenance` with engine path, version, model name/path, analysis, fixture values, and row count.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_spice_engine -v`
Expected: PASS (12 tests).

- [ ] **Step 5: User commit checkpoint**

Ask the user to commit via GitHub Desktop: `feat: run and parse ngspice DC operating point`.

---

## Task 3: AC sweep run and gain/phase metrics

**Files:**
- Modify: `spice_engine.py`
- Modify: `tests/test_spice_engine.py`

**Interfaces:**
- Consumes: `run_analysis`, `parse_wrdata`, `EngineOutputError` from Task 2.
- Produces:
  - `parse_ac(csv_text: str, frequency_hz: float) -> dict` with `points`, `marker`, `marker_note`
  - `run_analysis("ac", values_si)` extends the result with `result["ac"]`

- [ ] **Step 1: Write the failing tests**

```python
AC_CSV = (
    " 1.00000000e+03  1.00000000e-02  0.00000000e+00 "
    " 1.00000000e+03  1.70000000e-02  1.80000000e+02 \n"
    " 1.25892541e+03  1.00000000e-02  0.00000000e+00 "
    " 1.25892541e+03  1.60000000e-02  1.79000000e+02 \n"
)

class TestAcAnalysis(unittest.TestCase):
    def test_parse_ac_uses_source_node_as_gain_reference(self):
        ac = parse_ac(AC_CSV, 1000.0)
        self.assertAlmostEqual(ac["marker"]["gain_db"], 20 * math.log10(1.7), places=6)
        self.assertAlmostEqual(ac["marker"]["phase_deg"], -180.0, places=6)

    def test_parse_ac_out_of_sweep_range_has_no_marker(self):
        ac = parse_ac(AC_CSV, 100e6)
        self.assertIsNone(ac["marker"])
        self.assertEqual(ac["marker_note"], "not determined in sweep range")

    def test_parse_ac_rejects_truncated_row(self):
        with self.assertRaises(EngineOutputError):
            parse_ac(" 1.0e3 0.01 0.0 1.0e3 0.017\n", 1000.0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_spice_engine -v`
Expected: FAIL with `parse_ac` not defined.

- [ ] **Step 3: Implement AC parsing**

Read four series as `vm(in), vp(in), vm(out), vp(out)`; build `points` with `freq_hz, gain_db, phase_deg, vm_in, vm_out`. Compute gain from `vm(out)/vm(in)`, not from a pre-supplied dB column. Wrap phase difference to `[-180, 180]`. Pick the point with minimum `abs(log10(freq) - log10(requested))`; if the requested frequency is outside `[min(freq), max(freq)]`, set `marker=None` and the exact note `not determined in sweep range`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_spice_engine -v`
Expected: PASS (15 tests).

- [ ] **Step 5: User commit checkpoint**

Ask the user to commit via GitHub Desktop: `feat: add AC frequency response from ngspice`.

---

## Task 4: Transient run, downsampling and waveform metrics

**Files:**
- Modify: `spice_engine.py`
- Modify: `tests/test_spice_engine.py`

**Interfaces:**
- Consumes: `run_analysis`, `parse_wrdata`, `EngineOutputError` from Task 2.
- Produces:
  - `parse_tran(csv_text: str, frequency_hz: float) -> dict` with `points`, `vout_pp_v`, `vout_peak_v`, `phase_note`
  - `run_analysis("tran", values_si)` extends the result with `result["tran"]`

- [ ] **Step 1: Write the failing tests**

```python
TRAN_CSV = "".join(
    f" {i * 1e-5:.8e}  {0.01 * math.sin(2 * math.pi * 1000 * i * 1e-5):.8e}"
    f"  {-0.017 * math.sin(2 * math.pi * 1000 * i * 1e-5):.8e} \n"
    for i in range(1000)
)

class TestTransientAnalysis(unittest.TestCase):
    def test_parse_tran_reads_vin_and_vout(self):
        tran = parse_tran(TRAN_CSV, 1000.0)
        self.assertEqual(len(tran["points"]), 1000)
        self.assertGreater(tran["points"][1]["vin_v"], 0)
        self.assertLess(tran["points"][1]["vout_v"], 0)

    def test_parse_tran_measures_last_cycle_peak_to_peak(self):
        tran = parse_tran(TRAN_CSV, 1000.0)
        self.assertAlmostEqual(tran["vout_pp_v"], 0.034, places=3)
        self.assertAlmostEqual(tran["vout_peak_v"], 0.017, places=3)

    def test_parse_tran_detects_inversion(self):
        tran = parse_tran(TRAN_CSV, 1000.0)
        self.assertEqual(tran["phase_note"], "inverted")

    def test_parse_tran_downsamples_to_1200_points(self):
        many = "".join(f" {i * 1e-5:.8e} 0.0 0.0 \n" for i in range(5000))
        tran = parse_tran(many, 1000.0)
        self.assertLessEqual(len(tran["points"]), 1200)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_spice_engine -v`
Expected: FAIL with `parse_tran` not defined.

- [ ] **Step 3: Implement transient parsing**

Read `v(in)` and `v(out)` series. Determine the final one-period window as `t >= max(time) - 1/frequency`. Compute `vout_pp_v = max(vout) - min(vout)` in that window and `vout_peak_v = vout_pp_v / 2`. Determine inversion by the sign of `sum(vin_sample * vout_sample)` over that window: negative → `inverted`, otherwise `in-phase or undetermined`. Downsample the full series uniformly to at most 1200 points, preserving first and last samples. Raise `EngineOutputError` on empty or mismatched series.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_spice_engine -v`
Expected: PASS (19 tests).

- [ ] **Step 5: User commit checkpoint**

Ask the user to commit via GitHub Desktop: `feat: add transient waveform from ngspice`.

---

## Task 5: Flask analysis dispatch, SPICE validation and error policy

**Files:**
- Modify: `app.py`
- Create: `tests/test_web_lab04.py`

**Interfaces:**
- Consumes: `run_analysis`, `SpiceError` subclasses, `MODEL_NAME` from `spice_engine.py`.
- Produces:
  - `ANALYSES = ("bias", "dc", "ac", "tran")`
  - `parse_spice_form(form) -> tuple[dict[str, float], dict[str, str]]`
  - `render_page(..., analysis="bias", spice_values=None, spice_units=None, spice_result=None, engine=None, charts=None)`
  - updated `GET /` and `POST /calculate`

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from unittest.mock import patch

from app import app
from spice_engine import EngineUnavailable, MODEL_NAME


class TestSpiceWeb(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def _spice_payload(self, **overrides):
        data = {
            "analysis": "dc", "vcc": "12", "r1": "100", "r2": "22",
            "rc": "2.2", "re": "1", "rl": "10", "cin": "10", "cout": "10",
            "source_amp": "10", "source_freq": "1",
            "r1_unit": "kohm", "r2_unit": "kohm", "rc_unit": "kohm",
            "re_unit": "kohm", "rl_unit": "kohm",
            "cin_unit": "uf", "cout_unit": "uf",
            "amp_unit": "mv", "freq_unit": "khz",
        }
        data.update(overrides)
        return data

    def test_get_analysis_selects_spice_form(self):
        res = self.client.get("/?analysis=ac")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('name="source_amp"', html)
        self.assertIn('value="ac" selected', html)
        self.assertIn("source node IN", html)

    def test_invalid_re_returns_400_without_results(self):
        res = self.client.post("/calculate", data=self._spice_payload(re="0"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("RE ต้องมากกว่า 0", res.get_data(as_text=True))
        self.assertNotIn('class="results spice-results"', res.get_data(as_text=True))

    def test_engine_unavailable_is_200_with_no_stale_result(self):
        with patch("app.run_analysis", side_effect=EngineUnavailable("ngspice not found")):
            res = self.client.post("/calculate", data=self._spice_payload())
        self.assertEqual(res.status_code, 200)
        self.assertIn("UNAVAILABLE", res.get_data(as_text=True))
        self.assertNotIn('class="results spice-results"', res.get_data(as_text=True))

    def test_successful_dc_shows_spice_badge_and_provenance(self):
        fake = {"status": "OK", "analysis": "dc", "op": {"ic_a": 1.38e-3},
                "provenance": {"engine": "ngspice-47", "model": MODEL_NAME},
                "rows": 1}
        with patch("app.run_analysis", return_value=fake):
            res = self.client.post("/calculate", data=self._spice_payload())
        html = res.get_data(as_text=True)
        self.assertIn("ngspice", html)
        self.assertIn("QT_NPN", html)
        self.assertIn('class="results spice-results"', html)

    def test_bias_route_still_uses_lab03_solver(self):
        res = self.client.post("/calculate", data={
            "analysis": "bias", "mode": "divider", "vcc": "12", "r1": "100",
            "r2": "22", "rc": "2.2", "re": "1", "beta": "100", "vbe": "0.70",
            "r1_unit": "kohm", "r2_unit": "kohm", "rc_unit": "kohm", "re_unit": "kohm",
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn("9.294", res.get_data(as_text=True))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_web_lab04 -v`
Expected: FAIL because `analysis`, `parse_spice_form`, or SPICE sections do not exist.

- [ ] **Step 3: Implement the Flask layer**

Add SPICE constants and unit maps: resistance `Ω/kΩ/MΩ`, capacitance `pF/nF/µF` (keys `pf`, `nf`, `uf`), amplitude `mV/V` (`mv`, `v`), frequency `Hz/kHz/MHz` (`hz`, `khz`, `mhz`). Validate finite and > 0 for every SPICE numeric field. Extend `render_page` with new keyword-only defaults so existing calls remain valid. For `analysis != "bias"`, hide the Lab 03 `mode` selector, ignore `mode`, parse SPICE form, call `run_analysis`, catch `SpiceError` into `engine` status (`UNAVAILABLE` for `EngineUnavailable`, `ERROR` otherwise) and set `spice_result=None`. Never pass stale results into the template on error.

- [ ] **Step 4: Run all tests to verify no regression**

Run: `python -m unittest discover -s tests -v`
Expected: PASS (61 tests = 37 existing + 19 engine + 5 web).

- [ ] **Step 5: User commit checkpoint**

Ask the user to commit via GitHub Desktop: `feat: dispatch DC/AC/transient analysis in Flask`.

---

## Task 6: Template, SVG plots, status and responsive styling

**Files:**
- Modify: `templates/index.html`
- Modify: `static/style.css`
- Modify: `app.py` (chart coordinate helpers only)

**Interfaces:**
- Consumes: `analysis`, `spice_values`, `spice_units`, `spice_result`, `engine`, `charts` from Task 5.
- Produces:
  - `build_charts(spice_result: dict | None) -> dict[str, dict]`
  - template variables `ac_points`, `tran_points`, `op_display`, `spice_display`, `provenance_rows`

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from unittest.mock import patch

from app import app
from spice_engine import EngineRunError, MODEL_NAME


class TestPresentation(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def _spice_payload(self, **overrides):
        data = {
            "analysis": "dc", "vcc": "12", "r1": "100", "r2": "22",
            "rc": "2.2", "re": "1", "rl": "10", "cin": "10", "cout": "10",
            "source_amp": "10", "source_freq": "1",
            "r1_unit": "kohm", "r2_unit": "kohm", "rc_unit": "kohm",
            "re_unit": "kohm", "rl_unit": "kohm",
            "cin_unit": "uf", "cout_unit": "uf",
            "amp_unit": "mv", "freq_unit": "khz",
        }
        data.update(overrides)
        return data

    def test_ac_page_has_svg_with_axis_labels_when_result_present(self):
        result = {
            "status": "OK", "analysis": "ac",
            "ac": {"points": [{"freq_hz": 1000.0, "gain_db": 4.6, "phase_deg": -180.0}],
                   "marker": {"freq_hz": 1000.0, "gain_db": 4.6, "phase_deg": -180.0},
                   "marker_note": ""},
            "provenance": {"engine": "ngspice-47", "model": MODEL_NAME}, "rows": 1,
        }
        with patch("app.run_analysis", return_value=result):
            res = self.client.post("/calculate", data={
                "analysis": "ac", "vcc": "12", "r1": "100", "r2": "22",
                "rc": "2.2", "re": "1", "rl": "10", "cin": "10", "cout": "10",
                "source_amp": "10", "source_freq": "1", "r1_unit": "kohm",
                "r2_unit": "kohm", "rc_unit": "kohm", "re_unit": "kohm",
                "rl_unit": "kohm", "cin_unit": "uf", "cout_unit": "uf",
                "amp_unit": "mv", "freq_unit": "khz",
            })
        html = res.get_data(as_text=True)
        self.assertIn("<svg", html)
        self.assertIn("Frequency (Hz)", html)
        self.assertIn("Gain (dB)", html)
        self.assertIn("source node IN", html)

    def test_error_page_has_no_svg_and_no_success_badge(self):
        with patch("app.run_analysis", side_effect=EngineRunError("boom")):
            res = self.client.post("/calculate", data=self._spice_payload())
        html = res.get_data(as_text=True)
        self.assertNotIn("Success", html)
        self.assertNotIn("<svg", html)
        self.assertIn("ERROR", html)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_web_lab04 -v`
Expected: FAIL because SVG/chart context is absent.

- [ ] **Step 3: Implement presentation**

Add `build_charts()` in `app.py` to map parsed samples to `width=680 height=260` SVG coordinates and return `ac_points`/`tran_points` strings plus axis labels; no engineering calculation in Jinja. In the template, keep the existing Lab 03 results block unchanged for `analysis == "bias"`; add SPICE-only cards for DC (table), AC (gain/phase table + SVG + marker note), and transient (Vin/Vout SVG + measured peak note). Show the status badge as `Success` for `OK`, `Unavailable` for `UNAVAILABLE`, and `Error` for `ERROR`; with a synchronous POST, `Running` is the browser's brief loading state, not a persisted page state. Add a provenance table with engine/version, model, analysis, fixture, and row count. Add CSS for `.status-ok`, `.status-error`, `.chart`, `.provenance`, and `@media (max-width: 640px)`.

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m unittest discover -s tests -v`
Expected: PASS (63 tests = 37 existing + 19 engine + 7 web).

- [ ] **Step 5: User commit checkpoint**

Ask the user to commit via GitHub Desktop: `feat: render ngspice plots and provenance`.

---

## Task 7: Docs and honest browser acceptance B1–B8

**Files:**
- Modify: `README.md`
- Modify: `docs/validation.md`
- Modify: `docs/reflection.md`

**Interfaces:**
- Consumes: all tasks above.
- Produces: reproducible setup instructions, B1–B8 evidence table, final reflection.

- [ ] **Step 1: Update `README.md`**

Document: ngspice 47 Windows console binary (`ngspice_con.exe`) install, add its `bin` folder to `PATH` or set `NGSPICE_CMD`, `python -m unittest discover -s tests -v`, `python -m flask --app app run --debug`, the four `analysis` values, SPICE fixture defaults, model provenance note, and that plotting uses inline SVG with no new dependency.

- [ ] **Step 2: Update `docs/validation.md`**

Add a Lab 04 section with the exact ngspice banner, model file/parameters, `NGSPICE_CMD` used, and a B1–B8 table with columns `Case | Expected | Observed | Evidence | Method | Status`. Copy B1–B8 from the handout. State `OpenCode Browser` as the method. Use `NOT RUN` if any check could not be executed; never mark a check PASS from source inspection alone.

- [ ] **Step 3: Run the full suite**

Run: `python -m unittest discover -s tests -v`
Expected: `Ran 63 tests ... OK`.

- [ ] **Step 4: Browser acceptance**

Start Flask with `NGSPICE_CMD` pointing at the extracted ngspice 47 console binary. Using OpenCode Browser, execute B1–B8 against `http://127.0.0.1:5000/`: switch Lab 03 modes, run DC, change RE, run AC, run transient at 10 mV/1 kHz, change source, force RE=0 and engine-unavailable, then check desktop/mobile viewports and capture both screenshots for B8. Record observed values and evidence exactly as seen. For B4/B5/B6, confirm chart data changes with the run inputs by comparing parsed sample arrays in the page/provenance, not by screenshots alone.

- [ ] **Step 5: Update reflection and final status**

Add a short Lab 04 reflection covering external-process integration, why `.ac` and `.tran` differ, provenance, and what Impeccable/Playwright could not do in this environment. Ensure `docs/validation.md` statuses match what was actually run.

- [ ] **Step 6: User commit and push checkpoint**

Ask the user to commit and push via GitHub Desktop: `feat: add Lab 04 BJT CE amplifier simulator`. Do not run `git commit` or `git push`.

---

## Self-Review Notes

- **Spec coverage:** model provenance, real `.op/.ac/.tran`, engineering units, status/provenance, analytical/SPICE separation, error policy, B1–B8, README/reflection are all assigned to tasks.
- **Step scan:** each step is one test, one implementation, one verification, or one user commit checkpoint.
- **Type consistency:** `run_analysis(analysis, values_si)`, `SpiceError` subclasses, `result["op"|"ac"|"tran"|"provenance"]`, and `render_page(..., analysis=...)` are used with the same names in every task.
- **Review Focus:** each of the five risks has an explicit failing test in its owning task.
- **Proportion:** the plan pins contracts and test assertions without transcribing implementation bodies.
