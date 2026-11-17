import unittest

from app import app


class TestFormPage(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_index_returns_form(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        for field in ["vcc", "r1", "r2", "rc", "re", "beta", "vbe",
                      "r1_unit", "r2_unit", "rc_unit", "re_unit"]:
            self.assertIn(f'name="{field}"', html)
        self.assertIn("Calculate DC Bias", html)


class TestCalculate(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def _payload(self, **overrides):
        data = {"mode": "divider", "vcc": "12", "r1": "100", "r2": "22",
                "rc": "2.2", "re": "1", "beta": "100", "vbe": "0.70",
                "r1_unit": "kohm", "r2_unit": "kohm",
                "rc_unit": "kohm", "re_unit": "kohm"}
        data.update(overrides)
        return data

    def _mode_payload(self, mode="fixed", **overrides):
        data = {"mode": mode, "vcc": "12", "rc": "2.2", "rc_unit": "kohm",
                "beta": "100", "vbe": "0.70", "rb": "1", "rb_unit": "mohm",
                "re": "1", "re_unit": "kohm", "r1": "100",
                "r1_unit": "kohm", "r2": "22", "r2_unit": "kohm"}
        data.update(overrides)
        return data

    def _results_html(self, body):
        start = body.index('<section class="results"')
        end = body.index("</section>", start)
        return body[start:end]

    def test_valid_input_shows_results(self):
        res = self.client.post("/calculate", data=self._payload())
        self.assertEqual(res.status_code, 200)
        results = self._results_html(res.get_data(as_text=True))
        for expected in ["9.294", "8.052", "1.942", "1.242"]:
            self.assertIn(expected, results)
        self.assertIn("Active Region", results)
        self.assertIn("badge-active", results)

    def test_cutoff_badge_and_warning(self):
        res = self.client.post("/calculate", data=self._payload(r2="5"))
        results = self._results_html(res.get_data(as_text=True))
        self.assertIn("badge-cutoff", results)
        self.assertIn("Forward-Active", results)

    def test_saturation_badge_and_warning(self):
        res = self.client.post("/calculate", data=self._payload(rc="10", re="0.1"))
        results = self._results_html(res.get_data(as_text=True))
        self.assertIn("badge-saturation", results)
        self.assertIn("Saturation", results)

    def test_small_current_uses_microamps(self):
        res = self.client.post("/calculate", data=self._payload(re="10", re_unit="mohm"))
        results = self._results_html(res.get_data(as_text=True))
        self.assertIn("144.941 nA", results)
        self.assertNotIn("0.000 mA", results)

    def test_non_finite_values_are_rejected(self):
        cases = [("vcc", "nan"), ("vcc", "inf"), ("beta", "1e400")]
        for key, value in cases:
            with self.subTest(field=key, value=value):
                res = self.client.post("/calculate", data=self._payload(**{key: value}))
                self.assertEqual(res.status_code, 400)
                self.assertIn("กรุณากรอกตัวเลข", res.get_data(as_text=True))

    def test_vbe_must_be_below_vcc(self):
        res = self.client.post("/calculate", data=self._payload(vbe="12"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("VBE", res.get_data(as_text=True))

    def test_zero_beta_shows_error(self):
        res = self.client.post("/calculate", data=self._payload(beta="0"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("β ต้องมากกว่า 0", res.get_data(as_text=True))

    def test_invalid_unit_shows_error(self):
        res = self.client.post("/calculate", data=self._payload(r1_unit="KOHM"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("หน่วยไม่ถูกต้อง", res.get_data(as_text=True))

    def test_empty_field_shows_error(self):
        res = self.client.post("/calculate", data=self._payload(r1=""))
        self.assertEqual(res.status_code, 400)
        self.assertIn("กรุณากรอกตัวเลข: R1", res.get_data(as_text=True))

    def test_unit_conversion_matches_ohms(self):
        kohm = self.client.post("/calculate", data=self._payload())
        ohm = self.client.post("/calculate", data=self._payload(
            r1="100000", r2="22000", rc="2200", re="1000",
            r1_unit="ohm", r2_unit="ohm", rc_unit="ohm", re_unit="ohm"))
        self.assertEqual(self._results_html(kohm.get_data(as_text=True)),
                         self._results_html(ohm.get_data(as_text=True)))

    def test_zero_resistance_shows_error(self):
        res = self.client.post("/calculate", data=self._payload(r1="0"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("มากกว่า 0", res.get_data(as_text=True))

    def test_non_numeric_keeps_typed_value(self):
        res = self.client.post("/calculate", data=self._payload(r1="abc"))
        self.assertEqual(res.status_code, 400)
        html = res.get_data(as_text=True)
        self.assertIn("กรุณากรอกตัวเลข", html)
        self.assertIn('value="abc"', html)

    def test_fixed_dispatch(self):
        res = self.client.post("/calculate", data=self._mode_payload())
        self.assertEqual(res.status_code, 200)
        self.assertIn("Fixed Bias", res.get_data(as_text=True))
        self.assertIn("1.130 mA", res.get_data(as_text=True))

    def test_emitter_dispatch(self):
        res = self.client.post("/calculate", data=self._mode_payload(
            "emitter", re="1"))
        self.assertEqual(res.status_code, 200)
        self.assertIn("Emitter Bias", res.get_data(as_text=True))
        self.assertIn("1.026 mA", res.get_data(as_text=True))

    def test_divider_unchanged(self):
        res = self.client.post("/calculate", data=self._payload(mode="divider"))
        self.assertIn("9.294", self._results_html(res.get_data(as_text=True)))

    def test_rb_unit_conversion(self):
        a = self.client.post("/calculate", data=self._mode_payload(
            rb="1", rb_unit="mohm"))
        b = self.client.post("/calculate", data=self._mode_payload(
            rb="1000000", rb_unit="ohm"))
        self.assertEqual(self._results_html(a.get_data(as_text=True)),
                         self._results_html(b.get_data(as_text=True)))

    def test_unknown_mode_returns_error(self):
        res = self.client.post("/calculate", data=self._mode_payload("bogus"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("โหมดไม่ถูกต้อง", res.get_data(as_text=True))
        self.assertNotIn('<section class="results"', res.get_data(as_text=True))

    def test_get_unknown_mode_returns_error(self):
        res = self.client.get("/?mode=bogus")
        self.assertEqual(res.status_code, 400)
        self.assertIn("โหมดไม่ถูกต้อง", res.get_data(as_text=True))
        self.assertNotIn('<section class="results"', res.get_data(as_text=True))

    def test_fixed_invalid_rb_unit_shows_error(self):
        res = self.client.post("/calculate", data=self._mode_payload(
            rb_unit="BAD"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("หน่วยไม่ถูกต้อง", res.get_data(as_text=True))

    def test_fixed_ignores_unused_fields(self):
        res = self.client.post("/calculate", data=self._mode_payload(
            re="abc", r1="abc", r2="abc", re_unit="BAD"))
        self.assertEqual(res.status_code, 200)

    def test_emitter_ignores_unused_fields(self):
        res = self.client.post("/calculate", data=self._mode_payload(
            "emitter", r1="abc", r2="abc", r1_unit="BAD"))
        self.assertEqual(res.status_code, 200)

    def test_error_does_not_show_results(self):
        res = self.client.post("/calculate", data=self._mode_payload(rb="0"))
        self.assertEqual(res.status_code, 400)
        self.assertNotIn('<section class="results"', res.get_data(as_text=True))

    def test_get_mode_selects_form(self):
        res = self.client.get("/?mode=fixed")
        self.assertEqual(res.status_code, 200)
        self.assertIn('name="rb"', res.get_data(as_text=True))
        self.assertNotIn('name="r1"', res.get_data(as_text=True))

    def test_mode_selector_present(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('id="mode"', html)
        self.assertIn("เปลี่ยนวงจร", html)

    def test_fixed_form_hides_divider_fields(self):
        html = self.client.get("/?mode=fixed").get_data(as_text=True)
        self.assertIn('name="rb"', html)
        self.assertNotIn('name="r1"', html)
        self.assertNotIn('name="r2"', html)

    def test_result_shows_selected_mode(self):
        html = self.client.post("/calculate", data=self._mode_payload(
            "emitter")).get_data(as_text=True)
        self.assertIn("Emitter Bias", self._results_html(html))

