import asyncio
import logging
import time
import queue
import threading
import cv2
import numpy as np

import grpc
import edge_uplink_pb2
import edge_uplink_pb2_grpc

from fusion_engine import FusionEngine
from pose_engine import PoseEngine
from backpressure import BackpressureManager
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("L2-Telemetry-Receiver")

class PriorityStreamQueue:
    def __init__(self, fusion_engine, pose_engine, backpressure_manager, model):
        self.pq = queue.PriorityQueue()
        self.fusion_engine = fusion_engine
        self.pose_engine = pose_engine
        self.backpressure_manager = backpressure_manager
        self.model = model

    def put_payload(self, device_id, suspicion, frame_bytes):
        # 1. Backpressure Check
        if self.backpressure_manager.should_abstain(self.pq.qsize(), suspicion):
            logger.warning(f"ABSTAIN: Dropping low-suspicion frame from {device_id} due to heavy queue load.")
            return

        # 2. Accept and Queue
        # Negative suspicion because PriorityQueue retrieves lowest first
        priority = -suspicion
        self.pq.put((priority, time.time(), device_id, suspicion, frame_bytes))
        
    def process_loop(self):
        while True:
            try:
                priority, timestamp, device_id, edge_suspicion, frame_bytes = self.pq.get(timeout=1.0)
                
                # 1. Decode JPEG bytes into OpenCV image
                nparr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is None:
                    logger.error(f"Failed to decode frame from {device_id}")
                    self.pq.task_done()
                    continue

                # 2. Run YOLOv8 Inference
                results = self.model(frame, verbose=False)
                
                # Extract the highest confidence of any detected person (class 0)
                max_person_conf = 0.0
                person_detected = False
                for box in results[0].boxes:
                    if int(box.cls[0]) == 0: # Person class
                        person_detected = True
                        conf = float(box.conf[0])
                        if conf > max_person_conf:
                            max_person_conf = conf
                            
                # 3. Temperature Calibration (YOLO)
                calibrated_l2_prob = self.fusion_engine.apply_temperature_calibration(max_person_conf)
                
                # 4. Run BlazePose if a person is detected
                pose_suspicion = 0.5
                if person_detected:
                    pose_suspicion = self.pose_engine.analyze_pose(frame)
                
                # 5. Recursive Log-Odds Fusion (3-way)
                fused_prob = self.fusion_engine.fuse_log_odds_multi([edge_suspicion, calibrated_l2_prob, pose_suspicion])
                
                logger.info(f"[{device_id}] Edge: {edge_suspicion:.4f} | YOLO: {calibrated_l2_prob:.4f} | Pose: {pose_suspicion:.4f} | FUSED: {fused_prob:.4f}")
                
                self.pq.task_done()
            except queue.Empty:
                continue

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

def run_worker_thread(pq):
    pq.process_loop()

async def serve():
    logger.info("Initializing YOLOv8n, PoseEngine, BackpressureManager, and Fusion Engine...")
    fusion_engine = FusionEngine(temperature=1.5)
    pose_engine = PoseEngine()
    backpressure_manager = BackpressureManager(max_queue_size=50, abstain_threshold=0.8)
    model = YOLO("yolov8n.pt")
    
    pq = PriorityStreamQueue(fusion_engine, pose_engine, backpressure_manager, model)
    
    worker = threading.Thread(target=run_worker_thread, args=(pq,), daemon=True)
    worker.start()
    
    server = grpc.aio.server()
    edge_uplink_pb2_grpc.add_EdgeUplinkServicer_to_server(EdgeUplinkServicerImpl(pq), server)
    server.add_insecure_port('[::]:50051')
    
    logger.info("L2 Regional Node Server started on port 50051.")
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Server shut down.")
