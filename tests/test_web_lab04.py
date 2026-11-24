import unittest
from unittest.mock import patch

from werkzeug.datastructures import MultiDict

from app import app, parse_spice_form
from spice_engine import (
    EngineOutputError,
    EngineRunError,
    EngineUnavailable,
    MODEL_NAME,
    build_netlist,
    parse_tran,
)


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

    def test_invalid_spice_unit_returns_400_without_results(self):
        res = self.client.post("/calculate", data=self._spice_payload(freq_unit="ghz"))
        html = res.get_data(as_text=True)
        self.assertEqual(res.status_code, 400)
        self.assertIn("หน่วยไม่ถูกต้อง", html)
        self.assertNotIn('class="results spice-results"', html)

    def test_engine_unavailable_is_200_with_no_stale_result(self):
        with patch("app.run_analysis", side_effect=EngineUnavailable("ngspice not found")):
            res = self.client.post("/calculate", data=self._spice_payload())
        self.assertEqual(res.status_code, 200)
        self.assertIn("UNAVAILABLE", res.get_data(as_text=True))
        self.assertNotIn('class="results spice-results"', res.get_data(as_text=True))

    def test_successful_dc_shows_spice_badge_and_provenance(self):
        fake = {
            "status": "OK", "analysis": "dc", "op": {"ic_a": 1.38e-3},
            "provenance": {"engine": "ngspice-47", "model": MODEL_NAME},
            "rows": 1,
        }
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
            "ac": {
                "points": [
                    {"freq_hz": 1000.0, "gain_db": 4.6, "phase_deg": -180.0},
                    {"freq_hz": 10000.0, "gain_db": 8.0, "phase_deg": -175.0},
                ],
                "marker": {
                    "freq_hz": 1000.0, "gain_db": 4.6, "phase_deg": -180.0,
                },
                "marker_note": "",
            },
            "provenance": {"engine": "ngspice-47", "model": MODEL_NAME}, "rows": 2,
        }
        with patch("app.run_analysis", return_value=result):
            res = self.client.post("/calculate", data=self._spice_payload(analysis="ac"))
        html = res.get_data(as_text=True)
        self.assertIn("<svg", html)
        self.assertIn("Frequency (Hz)", html)
        self.assertIn("Gain (dB)", html)
        self.assertIn("source node IN", html)

    def test_ac_out_of_sweep_shows_chart_note_and_no_marker(self):
        result = {
            "status": "OK", "analysis": "ac",
            "ac": {
                "points": [
                    {"freq_hz": 10.0, "gain_db": 1.0, "phase_deg": -10.0},
                    {"freq_hz": 100.0, "gain_db": 2.0, "phase_deg": -20.0},
                ],
                "marker": None,
                "marker_note": "not determined in sweep range",
            },
            "provenance": {"engine": "ngspice-47", "model": MODEL_NAME}, "rows": 2,
        }
        with patch("app.run_analysis", return_value=result):
            res = self.client.post("/calculate", data=self._spice_payload(analysis="ac"))
        html = res.get_data(as_text=True)
        self.assertIn("<svg", html)
        self.assertIn("not determined in sweep range", html)
        self.assertNotIn('class="chart-marker"', html)

    def test_short_window_transient_does_not_claim_last_cycle(self):
        result = {
            "status": "OK", "analysis": "tran",
            "tran": {
                "points": [
                    {"time_s": 0.0, "vin_v": 0.01, "vout_v": -0.01},
                    {"time_s": 0.0005, "vin_v": 0.0, "vout_v": 0.0},
                ],
                "vout_pp_v": 0.01,
                "vout_peak_v": 0.005,
                "phase_note": "inverted",
                "measurement_note": (
                    "less than one period simulated; peak-to-peak over available window"
                ),
            },
            "provenance": {"engine": "ngspice-47", "model": MODEL_NAME}, "rows": 2,
        }
        with patch("app.run_analysis", return_value=result):
            res = self.client.post("/calculate", data=self._spice_payload(analysis="tran"))
        html = res.get_data(as_text=True)
        self.assertIn("Vout peak (available window)", html)
        self.assertIn("less than one period simulated", html)
        self.assertNotIn("Vout peak (last cycle)", html)

    def test_dc_page_explains_ngspice_emitter_current_sign(self):
        result = {
            "status": "OK", "analysis": "dc",
            "op": {"vb_v": 2.048, "ie_a": -1.386e-3},
            "provenance": {"engine": "ngspice-47", "model": MODEL_NAME},
        }
        with patch("app.run_analysis", return_value=result):
            res = self.client.post("/calculate", data=self._spice_payload())
        self.assertIn("ngspice terminal-current sign convention",
                      res.get_data(as_text=True))

    def test_error_page_has_no_svg_and_no_success_badge(self):
        with patch("app.run_analysis", side_effect=EngineRunError("boom")):
            res = self.client.post("/calculate", data=self._spice_payload())
        html = res.get_data(as_text=True)
        self.assertNotIn("Success", html)
        self.assertNotIn("<svg", html)
        self.assertIn("ERROR", html)


class TestAppEngineBoundary(unittest.TestCase):
    def test_parse_tran_rejects_empty_csv(self):
        with self.assertRaises(EngineOutputError):
            parse_tran("", 1000.0)

    def test_parsed_spice_form_drives_real_netlist(self):
        values_si, errors = parse_spice_form(MultiDict({
            "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
            "rl": "10", "cin": "10", "cout": "10",
            "source_amp": "10", "source_freq": "1",
            "r1_unit": "kohm", "r2_unit": "kohm", "rc_unit": "kohm",
            "re_unit": "kohm", "rl_unit": "kohm",
            "cin_unit": "uf", "cout_unit": "uf",
            "amp_unit": "mv", "freq_unit": "khz",
        }))
        self.assertEqual(errors, {})
        netlist = build_netlist("dc", values_si)
        self.assertIn("SIN(0 10m 1k 0 0)", netlist)
