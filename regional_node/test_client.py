import grpc
import time
import cv2
import numpy as np

import edge_uplink_pb2
import edge_uplink_pb2_grpc

def run_test():
    channel = grpc.insecure_channel('localhost:50051')
    stub = edge_uplink_pb2_grpc.EdgeUplinkStub(channel)

    # Create a dummy image (e.g. 640x480 black image)
    # Draw a white rectangle to simulate something YOLO might see (not a person, but enough to not crash)
    # Actually, let's just make a random noise image
    img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    _, img_encoded = cv2.imencode('.jpg', img)
    img_bytes = img_encoded.tobytes()

    def generate_payloads():
        for i in range(3):
            print(f"Sending payload {i+1}...")
            yield edge_uplink_pb2.EdgeTriggerPayload(
                device_id="esp32_test_cam_01",
                suspicion_probability=0.85, # Highly suspicious from ESP32
                frame_jpg=img_bytes,
                timestamp_ms=int(time.time() * 1000),
                metric_frame=edge_uplink_pb2.MetricFrame(
                    timestamp_ms=int(time.time() * 1000),
                    motion_energy=12.34  # Mock calculated energy
                )
            )
            time.sleep(0.5)

    try:
        response = stub.StreamTelemetry(generate_payloads())
        print("Telemetry stream finished.")
    except grpc.RpcError as e:
        print(f"gRPC Error: {e.code()} - {e.details()}")

if __name__ == '__main__':
    run_test()
