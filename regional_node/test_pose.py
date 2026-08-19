import unittest
import numpy as np
from pose_engine import PoseEngine

class TestPoseEngine(unittest.TestCase):
    def setUp(self):
        self.engine = PoseEngine()

    def test_analyze_pose_no_person(self):
        # Create a black dummy image (no person)
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Should return exactly 0.5 because no landmarks are detected
        suspicion = self.engine.analyze_pose(dummy_frame)
        self.assertAlmostEqual(suspicion, 0.5)

if __name__ == '__main__':
    unittest.main()
