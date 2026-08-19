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

if __name__ == '__main__':
    unittest.main()
