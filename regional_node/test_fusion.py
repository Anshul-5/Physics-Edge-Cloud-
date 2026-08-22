import unittest
from fusion_engine import FusionEngine

class TestFusionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = FusionEngine(temperature=1.5)

    def test_temperature_calibration(self):
        # 0.5 should map to 0.5 because logit(0.5) = 0
        prob = self.engine.apply_temperature_calibration(0.5)
        self.assertAlmostEqual(prob, 0.5, places=4)

        # High confidence should be softened by T > 1
        raw_prob = 0.99
        calibrated = self.engine.apply_temperature_calibration(raw_prob)
        self.assertLess(calibrated, raw_prob)

        # Low confidence should be softened by T > 1
        raw_prob = 0.01
        calibrated = self.engine.apply_temperature_calibration(raw_prob)
        self.assertGreater(calibrated, raw_prob)

    def test_fuse_log_odds(self):
        # Two highly suspicious signals should result in extremely high fused score
        fused = self.engine.fuse_log_odds(0.9, 0.9)
        self.assertGreater(fused, 0.95)

        # Two very un-suspicious signals should result in extremely low fused score
        fused = self.engine.fuse_log_odds(0.1, 0.1)
        self.assertLess(fused, 0.05)

        # Conflicting signals (one thinks yes, one thinks no with equal strength)
        # Should cancel out to 0.5
        fused = self.engine.fuse_log_odds(0.9, 0.1)
        self.assertAlmostEqual(fused, 0.5, places=4)

    def test_temperature_validation(self):
        # Temperature <= 0 or non-finite or non-numeric must raise
        with self.assertRaises(ValueError):
            FusionEngine(temperature=0)
        with self.assertRaises(ValueError):
            FusionEngine(temperature=-1.5)
        with self.assertRaises(ValueError):
            FusionEngine(temperature=float('nan'))
        with self.assertRaises(ValueError):
            FusionEngine(temperature=float('inf'))
        with self.assertRaises(TypeError):
            FusionEngine(temperature="1.5")
        with self.assertRaises(TypeError):
            FusionEngine(temperature=True)

    def test_nan_fusion_does_not_suppress_alerts(self):
        # NaN must be dropped and not drag the fused result to near-zero
        fused_with_nan = self.engine.fuse_log_odds_multi([float('nan'), 0.9, 0.9])
        fused_baseline = self.engine.fuse_log_odds_multi([0.9, 0.9])
        self.assertAlmostEqual(fused_with_nan, fused_baseline, places=4)
        self.assertGreater(fused_with_nan, 0.95)

    def test_empty_and_all_nan_fusion(self):
        self.assertEqual(self.engine.fuse_log_odds_multi([]), 0.5)
        self.assertEqual(self.engine.fuse_log_odds_multi([float('nan'), None]), 0.5)

    def test_calibration_nan_guard(self):
        with self.assertRaises(ValueError):
            self.engine.apply_temperature_calibration(float('nan'))
        with self.assertRaises(TypeError):
            self.engine.apply_temperature_calibration("high")

if __name__ == '__main__':
    unittest.main()
