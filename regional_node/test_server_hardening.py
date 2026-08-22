import unittest
import time
from unittest.mock import MagicMock, patch

from fusion_engine import FusionEngine
from backpressure import BackpressureManager
from server import PriorityStreamQueue, create_grpc_server, MAX_FRAME_BYTES

class TestServerHardening(unittest.TestCase):
    def setUp(self):
        self.fusion_engine = FusionEngine(temperature=1.5)
        self.backpressure = BackpressureManager(max_queue_size=10, abstain_threshold=0.8)
        self.mock_model = MagicMock()
        self.mock_pose = MagicMock()
        self.pq = PriorityStreamQueue(
            self.fusion_engine,
            self.mock_pose,
            self.backpressure,
            self.mock_model,
            max_capacity=5
        )

    def test_oversized_frame_rejected(self):
        oversized = b"X" * (MAX_FRAME_BYTES + 10)
        res = self.pq.put_payload("cam_01", 0.9, oversized)
        self.assertFalse(res)
        self.assertEqual(self.pq.pq.qsize(), 0)

    def test_invalid_suspicion_rejected(self):
        valid_frame = b"valid_frame"
        self.assertFalse(self.pq.put_payload("cam_01", float('nan'), valid_frame))
        self.assertFalse(self.pq.put_payload("cam_01", float('inf'), valid_frame))
        self.assertFalse(self.pq.put_payload("cam_01", "high", valid_frame))
        self.assertFalse(self.pq.put_payload("cam_01", None, valid_frame))
        self.assertEqual(self.pq.pq.qsize(), 0)

    def test_empty_frame_bytes_rejected(self):
        self.assertFalse(self.pq.put_payload("cam_01", 0.5, b""))
        self.assertFalse(self.pq.put_payload("cam_01", 0.5, None))
        self.assertEqual(self.pq.pq.qsize(), 0)

    def test_queue_capacity_bounded(self):
        valid_frame = b"valid_frame"
        # Max capacity is 5
        for i in range(5):
            self.assertTrue(self.pq.put_payload(f"cam_{i}", 0.9, valid_frame))
        self.assertEqual(self.pq.pq.qsize(), 5)

        # 6th should be rejected because queue is full
        self.assertFalse(self.pq.put_payload("cam_overflow", 0.9, valid_frame))
        self.assertEqual(self.pq.pq.qsize(), 5)

    def test_worker_loop_resilience_on_exception(self):
        # Enqueue item
        self.pq.put_payload("cam_01", 0.9, b"test_frame")
        self.assertEqual(self.pq.pq.qsize(), 1)

        # Mock cv2 to raise an unexpected exception
        with patch("server.cv2") as mock_cv2:
            mock_cv2.imdecode.side_effect = RuntimeError("Decoder crash")
            
            # Run one iteration of process_loop logic
            item = self.pq.pq.get(timeout=1.0)
            self.pq.pq.put(item)

            import threading
            def stop_soon():
                time.sleep(0.1)
                self.pq._running = False
                
            stopper = threading.Thread(target=stop_soon)
            stopper.start()
            self.pq.process_loop()
            stopper.join()

            # Verify failed_count incremented and task_done called
            self.assertEqual(self.pq.failed_count, 1)
            self.assertEqual(self.pq.pq.qsize(), 0)

    def test_grpc_insecure_mode_disabled(self):
        with patch.dict("os.environ", {"ALLOW_INSECURE_GRPC": "0"}):
            with self.assertRaises(RuntimeError):
                create_grpc_server(MagicMock(), server_port="50051")

if __name__ == '__main__':
    unittest.main()
