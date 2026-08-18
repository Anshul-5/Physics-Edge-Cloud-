import asyncio
import logging
import time
import queue
import threading

# We will generate these using grpc_tools later
# import edge_uplink_pb2
# import edge_uplink_pb2_grpc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("L2-Telemetry-Receiver")

class PriorityStreamQueue:
    def __init__(self):
        # Python's queue.PriorityQueue is thread-safe
        self.pq = queue.PriorityQueue()

    def put_payload(self, device_id, suspicion, frame_bytes):
        # Negative suspicion because PriorityQueue retrieves lowest first
        priority = -suspicion
        self.pq.put((priority, time.time(), device_id, frame_bytes))
        
    def process_loop(self):
        while True:
            try:
                priority, timestamp, device_id, frame_bytes = self.pq.get(timeout=1.0)
                # Processing simulation
                logger.info(f"Processing frame from {device_id} | Priority: {-priority:.4f} | Size: {len(frame_bytes)} bytes")
                # Wait 5ms to simulate YOLO preparation
                time.sleep(0.005)
                self.pq.task_done()
            except queue.Empty:
                continue

# Mock Servicer (until protobufs are generated)
class EdgeUplinkServicerMock:
    def __init__(self, processing_queue):
        self.processing_queue = processing_queue

    async def StreamTelemetry(self, request_iterator, context):
        async for payload in request_iterator:
            # Simulate 2ms deserialization latency
            await asyncio.sleep(0.002)
            self.processing_queue.put_payload(
                device_id=payload.device_id,
                suspicion=payload.suspicion_probability,
                frame_bytes=payload.frame_jpg
            )
        return

def run_worker_thread(pq):
    pq.process_loop()

async def serve():
    pq = PriorityStreamQueue()
    
    # Start the background processing thread
    worker = threading.Thread(target=run_worker_thread, args=(pq,), daemon=True)
    worker.start()
    
    logger.info("L2 Regional Node Server (Mock) started on port 50051.")
    logger.info("Ready to receive EdgeTriggerPayload streams.")
    
    # Keep the asyncio loop running for tests
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Server shut down.")
