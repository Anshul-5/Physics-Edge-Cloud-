import unittest
from backpressure import BackpressureManager

class TestBackpressureManager(unittest.TestCase):
    def setUp(self):
        self.manager = BackpressureManager(max_queue_size=10, abstain_threshold=0.8)

    def test_normal_load_accepts_all(self):
        # Under max_queue_size, it should accept even low suspicion frames
        self.assertFalse(self.manager.should_abstain(5, 0.1))
        self.assertFalse(self.manager.should_abstain(9, 0.9))

    def test_heavy_load_abstains_low_suspicion(self):
        # Over max_queue_size, it should reject low suspicion frames
        self.assertTrue(self.manager.should_abstain(11, 0.5))
        self.assertTrue(self.manager.should_abstain(15, 0.79))

    def test_heavy_load_accepts_high_suspicion(self):
        # Over max_queue_size, it should still accept highly suspicious frames
        self.assertFalse(self.manager.should_abstain(11, 0.81))
        self.assertFalse(self.manager.should_abstain(50, 0.99))

if __name__ == '__main__':
    unittest.main()
