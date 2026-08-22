import asyncio
import logging
import time
import queue
import threading
import math
import os
import hashlib
import itertools
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

import grpc

try:
    import edge_uplink_pb2
    import edge_uplink_pb2_grpc
except ImportError:
    edge_uplink_pb2 = None
    edge_uplink_pb2_grpc = None

from fusion_engine import FusionEngine
from backpressure import BackpressureManager

try:
    from pose_engine import PoseEngine
except ImportError:
    PoseEngine = None

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("L2-Telemetry-Receiver")

MAX_FRAME_BYTES = 512 * 1024  # 512 KB per frame
MAX_FRAME_DIM = 4096
MIN_FRAME_DIM = 2
DEFAULT_MAX_QUEUE_CAPACITY = 200

class PriorityStreamQueue:
    def __init__(self, fusion_engine, pose_engine, backpressure_manager, model, max_capacity=DEFAULT_MAX_QUEUE_CAPACITY):
        self.pq = queue.PriorityQueue(maxsize=max_capacity)
        self.fusion_engine = fusion_engine
        self.pose_engine = pose_engine
        self.backpressure_manager = backpressure_manager
        self.model = model
        self.max_capacity = max_capacity
        self._counter = itertools.count()
        self._running = True
        self.processed_count = 0
        self.failed_count = 0
        self.last_processed_time = 0.0

    def put_payload(self, device_id, suspicion, frame_bytes):
        # 1. Validate and clamp suspicion probability
        if not isinstance(suspicion, (int, float)) or isinstance(suspicion, bool) or not math.isfinite(suspicion):
            logger.warning(f"Dropping frame from {device_id}: invalid suspicion value {suspicion!r}")
            return False
        suspicion = min(max(float(suspicion), 0.0), 1.0)

        # 2. Validate frame bytes size to prevent decompression bomb / DoS
        if not frame_bytes or not isinstance(frame_bytes, (bytes, bytearray)):
            logger.warning(f"Dropping frame from {device_id}: invalid or empty frame bytes")
            return False
        if len(frame_bytes) > MAX_FRAME_BYTES:
            logger.warning(f"Dropping frame from {device_id}: frame size ({len(frame_bytes)} bytes) exceeds limit {MAX_FRAME_BYTES}")
            return False

        # 3. Backpressure Admission Check
        if self.backpressure_manager.should_abstain(self.pq.qsize(), suspicion):
            logger.warning(f"ABSTAIN: Dropping low-suspicion ({suspicion:.2f}) frame from {device_id} due to heavy queue load ({self.pq.qsize()}).")
            return False

        # 4. Accept and Queue with deterministic tie-breaker (seq counter)
        # Negative suspicion because PriorityQueue retrieves lowest first
        priority = -suspicion
        item = (priority, time.time(), next(self._counter), device_id, suspicion, frame_bytes)
        try:
            self.pq.put_nowait(item)
            return True
        except queue.Full:
            logger.warning(f"Queue full ({self.pq.qsize()}), shedding frame from {device_id}")
            return False
        
    def process_loop(self):
        while self._running:
            try:
                item = self.pq.get(timeout=1.0)
            except queue.Empty:
                continue

            try:
                priority, timestamp, seq, device_id, edge_suspicion, frame_bytes = item
                
                # 1. Decode JPEG bytes into OpenCV image
                if cv2 is None:
                    logger.error("OpenCV (cv2) is not installed; cannot decode frame.")
                    continue

                nparr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is None:
                    logger.error(f"Failed to decode frame from {device_id}")
                    continue

                # Bounds check decoded dimensions
                if (frame.shape[0] < MIN_FRAME_DIM or frame.shape[1] < MIN_FRAME_DIM or
                    frame.shape[0] > MAX_FRAME_DIM or frame.shape[1] > MAX_FRAME_DIM):
                    logger.error(f"Invalid frame dimensions {frame.shape} from {device_id}")
                    continue

                # 2. Run YOLOv8 Inference
                max_person_conf = 0.0
                person_detected = False
                if self.model is not None:
                    results = self.model(frame, verbose=False)
                    if results and len(results) > 0 and hasattr(results[0], 'boxes') and results[0].boxes is not None:
                        for box in results[0].boxes:
                            if int(box.cls[0]) == 0:  # Person class
                                person_detected = True
                                conf = float(box.conf[0])
                                if conf > max_person_conf:
                                    max_person_conf = conf
                            
                # 3. Temperature Calibration (YOLO)
                calibrated_l2_prob = self.fusion_engine.apply_temperature_calibration(max_person_conf)
                
                # 4. Run BlazePose if a person is detected
                pose_suspicion = 0.5
                if person_detected and self.pose_engine is not None:
                    pose_suspicion = self.pose_engine.analyze_pose(frame)
                
                # 5. Recursive Log-Odds Fusion (3-way)
                fused_prob = self.fusion_engine.fuse_log_odds_multi([edge_suspicion, calibrated_l2_prob, pose_suspicion])
                
                self.last_processed_time = time.time()
                self.processed_count += 1
                logger.info(f"[{device_id}] Edge: {edge_suspicion:.4f} | YOLO: {calibrated_l2_prob:.4f} | Pose: {pose_suspicion:.4f} | FUSED: {fused_prob:.4f}")
            except Exception as e:
                self.failed_count += 1
                logger.exception(f"Unexpected error in worker loop for device {device_id}: {e}")
            finally:
                self.pq.task_done()

if edge_uplink_pb2_grpc is not None:
    class EdgeUplinkServicerImpl(edge_uplink_pb2_grpc.EdgeUplinkServicer):
        def __init__(self, processing_queue):
            self.processing_queue = processing_queue

        async def StreamTelemetry(self, request_iterator, context):
            async for payload in request_iterator:
                energy_log = ""
                if payload.HasField("metric_frame"):
                    energy_log = f" | Motion Energy: {payload.metric_frame.motion_energy:.2f}"
                logger.info(f"Received telemetry stream from {payload.device_id}{energy_log}")
                self.processing_queue.put_payload(
                    device_id=payload.device_id,
                    suspicion=payload.suspicion_probability,
                    frame_bytes=payload.frame_jpg
                )
            return edge_uplink_pb2.Empty()
else:
    class EdgeUplinkServicerImpl:
        def __init__(self, processing_queue):
            self.processing_queue = processing_queue

def run_worker_thread(pq):
    pq.process_loop()

def load_yolo_model(model_path=None, model_sha256=None):
    if YOLO is None:
        logger.warning("ultralytics YOLO module not installed.")
        return None

    path = model_path or os.environ.get("YOLO_MODEL_PATH", "yolov8n.pt")
    if not os.path.exists(path) and os.environ.get("STRICT_MODEL_CHECK", "0") == "1":
        raise RuntimeError(f"YOLO model weights not found at {path}")
    
    if model_sha256 and os.path.exists(path):
        with open(path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        if digest != model_sha256:
            raise ValueError(f"YOLO model digest mismatch: expected {model_sha256}, got {digest}")

    return YOLO(path)

def create_grpc_server(servicer, server_port="50051", cert_path=None, key_path=None, ca_path=None):
    server_options = [
        ('grpc.max_receive_message_length', MAX_FRAME_BYTES + 64 * 1024),
        ('grpc.max_send_message_length', 4 * 1024 * 1024),
    ]
    server = grpc.aio.server(options=server_options)
    
    if edge_uplink_pb2_grpc is not None:
        edge_uplink_pb2_grpc.add_EdgeUplinkServicer_to_server(servicer, server)

    cert_path = cert_path or os.environ.get("GRPC_SERVER_CERT")
    key_path = key_path or os.environ.get("GRPC_SERVER_KEY")
    ca_path = ca_path or os.environ.get("GRPC_CA_CERT")

    if cert_path and key_path and os.path.exists(cert_path) and os.path.exists(key_path):
        with open(key_path, 'rb') as f:
            private_key = f.read()
        with open(cert_path, 'rb') as f:
            certificate_chain = f.read()
        
        root_certificates = None
        require_client_auth = False
        if ca_path and os.path.exists(ca_path):
            with open(ca_path, 'rb') as f:
                root_certificates = f.read()
            require_client_auth = True

        credentials = grpc.ssl_server_credentials(
            [(private_key, certificate_chain)],
            root_certificates=root_certificates,
            require_client_auth=require_client_auth,
        )
        server.add_secure_port(f'[::]:{server_port}', credentials)
        logger.info(f"L2 Regional Node Server configured with mTLS on port {server_port}")
    else:
        allow_insecure = os.environ.get("ALLOW_INSECURE_GRPC", "1")
        if allow_insecure == "1":
            logger.warning(
                "SECURITY WARNING: Running gRPC server on insecure plaintext port! "
                "Provide GRPC_SERVER_CERT, GRPC_SERVER_KEY, and GRPC_CA_CERT for production mTLS."
            )
            server.add_insecure_port(f'[::]:{server_port}')
        else:
            raise RuntimeError("Secure mTLS credentials required but not configured.")

    return server

async def serve():
    logger.info("Initializing YOLOv8n, PoseEngine, BackpressureManager, and Fusion Engine...")
    fusion_engine = FusionEngine(temperature=1.5)
    pose_engine = PoseEngine() if PoseEngine is not None else None
    backpressure_manager = BackpressureManager(max_queue_size=50, abstain_threshold=0.8)
    model = load_yolo_model()
    
    pq = PriorityStreamQueue(fusion_engine, pose_engine, backpressure_manager, model)
    
    worker = threading.Thread(target=run_worker_thread, args=(pq,), daemon=True)
    worker.start()
    
    servicer = EdgeUplinkServicerImpl(pq)
    server = create_grpc_server(servicer, server_port="50051")
    
    logger.info("L2 Regional Node Server started on port 50051.")
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Server shut down.")
