import pytest
import asyncio
import time
import edge_uplink_pb2
from server import EdgeUplinkServicerImpl, PriorityStreamQueue
from unittest.mock import MagicMock

def test_stream_telemetry_with_motion_energy():
    # Mock processing queue
    mock_pq = MagicMock(spec=PriorityStreamQueue)
    
    servicer = EdgeUplinkServicerImpl(mock_pq)
    
    # Create mock payload with metric_frame containing motion_energy
    img_bytes = b"fake_jpeg_data"
    payload = edge_uplink_pb2.EdgeTriggerPayload(
        device_id="test_cam_01",
        suspicion_probability=0.5,
        frame_jpg=img_bytes,
        timestamp_ms=int(time.time() * 1000),
        metric_frame=edge_uplink_pb2.MetricFrame(
            timestamp_ms=int(time.time() * 1000),
            motion_energy=45.67
        )
    )
    
    # Asynchronous request iterator
    async def request_generator():
        yield payload
        
    # Call the gRPC servicer method
    context = MagicMock()
    
    loop = asyncio.get_event_loop()
    response = loop.run_until_complete(servicer.StreamTelemetry(request_generator(), context))
    
    # Verify processing queue was called with correct arguments
    mock_pq.put_payload.assert_called_once_with(
        device_id="test_cam_01",
        suspicion=0.5,
        frame_bytes=img_bytes
    )
    
    assert isinstance(response, edge_uplink_pb2.Empty)
