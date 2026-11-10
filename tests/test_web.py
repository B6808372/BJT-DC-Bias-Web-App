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
        data = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
                "beta": "100", "vbe": "0.70",
                "r1_unit": "kohm", "r2_unit": "kohm",
                "rc_unit": "kohm", "re_unit": "kohm"}
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

