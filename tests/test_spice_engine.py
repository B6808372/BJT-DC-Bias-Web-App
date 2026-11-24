import math
import unittest
from unittest.mock import Mock, patch

from spice_engine import (
    EngineOutputError,
    build_netlist,
    engine_version,
    find_engine,
    format_spice_value,
    parse_ac,
    parse_op,
    parse_tran,
    parse_wrdata,
    run_analysis,
)

VALUES = {
    "vcc": 12.0,
    "r1": 100e3,
    "r2": 22e3,
    "rc": 2.2e3,
    "re": 1e3,
    "rl": 10e3,
    "cin": 10e-6,
    "cout": 10e-6,
    "source_amp_v": 10e-3,
    "source_freq_hz": 1e3,
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

    def test_dc_netlist_uses_control_block_instead_of_batch_print(self):
        net = build_netlist("dc", VALUES)
        self.assertIn(".control", net)
        self.assertIn(".endc", net)
        self.assertNotIn(".print", net)

    def test_dc_netlist_has_model_include_and_op_traces(self):
        net = build_netlist("dc", VALUES)
        self.assertIn(".include", net)
        self.assertIn("QT_NPN", net)
        self.assertIn("wrdata op.csv v(b) v(e) v(c) v(c,e) @q1[ic] @q1[ib] @q1[ie]", net)

    def test_netlist_quotes_include_path_that_may_contain_spaces(self):
        net = build_netlist("dc", VALUES)
        self.assertRegex(net, r'\.include "[^"\n]*bjt_teaching\.lib"')

    def test_ac_netlist_has_dec_sweep_and_gain_reference(self):
        net = build_netlist("ac", VALUES)
        self.assertIn("ac dec 10 10 10meg", net)
        self.assertIn("wrdata ac.csv vm(in) vp(in) vm(out) vp(out)", net)

    def test_tran_netlist_has_five_cycles_at_fixture_frequency(self):
        net = build_netlist("tran", VALUES)
        self.assertIn("tran 2.5u 5m", net)
        self.assertIn("wrdata tran.csv v(in) v(out)", net)


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

    def test_parse_wrdata_rejects_nan_token(self):
        with self.assertRaises(EngineOutputError):
            parse_wrdata(" 1.00000000e+00 nan \n", 1)

    def test_parse_op_rejects_infinite_device_current(self):
        with self.assertRaises(EngineOutputError):
            parse_op(OP_CSV.replace(" 1.37985457e-03 ", " inf "))

    def test_run_dc_calls_binary_without_shell_and_parses_real_csv(self):
        fake = Mock(return_value=Mock(returncode=0, stdout="ok", stderr=""))
        with patch("spice_engine.find_engine", return_value="ngspice_con"), \
             patch("spice_engine.subprocess.run", fake), \
             patch("spice_engine.Path.read_text", return_value=OP_CSV):
            result = run_analysis("dc", VALUES)
        self.assertEqual(result["status"], "OK")
        self.assertAlmostEqual(result["op"]["ic_a"], 1.37985457e-3, places=9)
        self.assertIsNone(fake.call_args.kwargs.get("shell"))

    def test_engine_version_parses_banner(self):
        banner = Mock(stdout="** ngspice-47 : Circuit level simulation program", stderr="")
        with patch("spice_engine.subprocess.run", return_value=banner):
            self.assertEqual(engine_version("ngspice_con"), "ngspice-47")


AC_CSV = (
    " 1.00000000e+03  1.00000000e-02 "
    " 1.00000000e+03  0.00000000e+00 "
    " 1.00000000e+03  1.70000000e-02 "
    " 1.00000000e+03  3.141592653589793e+00 \n"
    " 1.25892541e+03  1.00000000e-02 "
    " 1.25892541e+03  0.00000000e+00 "
    " 1.25892541e+03  1.60000000e-02 "
    " 1.25892541e+03  3.12413936e+00 \n"
)


class TestAcAnalysis(unittest.TestCase):
    def test_parse_ac_uses_source_node_as_gain_reference(self):
        ac = parse_ac(AC_CSV, 1000.0)
        self.assertAlmostEqual(ac["marker"]["gain_db"], 20 * math.log10(1.7), places=6)
        self.assertAlmostEqual(ac["marker"]["phase_deg"], -180.0, places=6)

    def test_parse_ac_converts_ngspice_radians_to_degrees(self):
        csv_text = (
            " 1.00000000e+03 1.0e-02 1.00000000e+03 0.00000000e+00 "
            " 1.00000000e+03 1.0e-02 1.00000000e+03 -1.57079633e+00 \n"
        )
        ac = parse_ac(csv_text, 1000.0)
        self.assertAlmostEqual(ac["marker"]["phase_deg"], -90.0, places=6)

    def test_parse_ac_out_of_sweep_range_has_no_marker(self):
        ac = parse_ac(AC_CSV, 100e6)
        self.assertIsNone(ac["marker"])
        self.assertEqual(ac["marker_note"], "not determined in sweep range")

    def test_parse_ac_rejects_truncated_row(self):
        with self.assertRaises(EngineOutputError):
            parse_ac(" 1.0e3 0.01 0.0 1.0e3 0.017\n", 1000.0)

    def test_parse_ac_rejects_infinite_magnitude(self):
        with self.assertRaises(EngineOutputError):
            parse_ac(AC_CSV.replace(" 1.70000000e-02 ", " inf "), 1000.0)


TRAN_CSV = "".join(
    f" {i * 1e-5:.8e}  {0.01 * math.sin(2 * math.pi * 1000 * i * 1e-5):.8e}"
    f"  {i * 1e-5:.8e}  {-0.017 * math.sin(2 * math.pi * 1000 * i * 1e-5):.8e} \n"
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
        many = "".join(f" {i * 1e-5:.8e} 0.0 {i * 1e-5:.8e} 0.0 \n" for i in range(5000))
        tran = parse_tran(many, 1000.0)
        self.assertLessEqual(len(tran["points"]), 1200)

    def test_parse_tran_flags_window_shorter_than_one_period(self):
        half_cycle = "".join(
            f" {i * 5e-6:.8e} 0.0 "
            f"{i * 5e-6:.8e} {-0.017 * math.sin(2 * math.pi * 1000 * i * 5e-6):.8e} \n"
            for i in range(100)
        )
        tran = parse_tran(half_cycle, 1000.0)
        self.assertEqual(
            tran.get("measurement_note"),
            "less than one period simulated; peak-to-peak over available window",
        )

    def test_parse_tran_flags_too_few_samples_per_period(self):
        sparse = "".join(
            f" {i * 1e-6:.8e} 0.0 {i * 1e-6:.8e} 0.0 \n" for i in range(1000)
        )
        tran = parse_tran(sparse, 10e6)
        self.assertEqual(
            tran.get("measurement_note"),
            "fewer than 10 samples per period; peak-to-peak is approximate",
        )
