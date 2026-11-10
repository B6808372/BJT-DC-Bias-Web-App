import unittest
from dc_bias import solve


class TestActiveRegion(unittest.TestCase):
    def test_reference_example(self):
        op = solve(vcc=12.0, r1=100_000, r2=22_000, rc=2_200,
                   re=1_000, beta=100, vbe=0.70)
        self.assertAlmostEqual(op.vb, 1.942, places=3)
        self.assertAlmostEqual(op.ve, 1.242, places=3)
        self.assertAlmostEqual(op.vc, 9.294, places=3)
        self.assertAlmostEqual(op.vce, 8.052, places=3)
        self.assertAlmostEqual(op.ic * 1000, 1.230, places=3)
        self.assertEqual(op.region, "active")
        self.assertEqual(op.warnings, ())

    def test_kcl_holds(self):
        op = solve(12, 100_000, 22_000, 2_200, 1_000, 100, 0.7)
        self.assertAlmostEqual(op.ie, op.ib + op.ic, places=12)


class TestOutsideActiveRegion(unittest.TestCase):
    def test_cutoff_when_vth_below_vbe(self):
        op = solve(12, 100_000, 5_000, 2_200, 1_000, 100, 0.7)
        self.assertEqual(op.region, "cutoff")
        self.assertAlmostEqual(op.ib, 0.0)
        self.assertAlmostEqual(op.ic, 0.0)
        self.assertAlmostEqual(op.ie, 0.0)
        self.assertAlmostEqual(op.ve, 0.0)
        self.assertAlmostEqual(op.vb, op.vth)
        self.assertAlmostEqual(op.vc, 12.0)
        self.assertTrue(any("Forward-Active" in w for w in op.warnings))

    def test_saturation_when_vce_below_sat(self):
        op = solve(12, 100_000, 22_000, 10_000, 100, 100, 0.7)
        self.assertEqual(op.region, "saturation")
        self.assertLess(op.vce, 0.2)
        self.assertTrue(any("Saturation" in w for w in op.warnings))
