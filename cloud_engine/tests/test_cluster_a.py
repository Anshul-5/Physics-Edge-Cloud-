import torch
from mem_ae import MemAE
from graph_engine import SpatialGraphEngine

def test_mem_ae_forward():
    model = MemAE(input_dim=64, hidden_dim=16, mem_dim=10)
    # Dummy input batch of 5 items
    x = torch.randn(5, 64)
    x_hat, att_weight = model(x)
    
    assert x_hat.shape == (5, 64), "Reconstructed output shape mismatch"
    assert att_weight.shape == (5, 10), "Attention weight shape mismatch"

def test_mem_ae_anomaly_score():
    model = MemAE(input_dim=64, hidden_dim=16, mem_dim=10)
    x = torch.randn(5, 64)
    scores = model.compute_anomaly_score(x)
    
    assert scores.shape == (5,), "Anomaly score shape mismatch"
    assert torch.all(scores >= 0), "Anomaly scores must be non-negative"

def test_graph_laplacian_diffusion():
    engine = SpatialGraphEngine()
    
    # 3 Cameras in a line
    engine.add_camera_node("C1", (0, 0))
    engine.add_camera_node("C2", (10, 0))
    engine.add_camera_node("C3", (20, 0))
    
    engine.add_physical_adjacency("C1", "C2")
    engine.add_physical_adjacency("C2", "C3")
    
    # C1 sees an event
    engine.update_node_suspicion("C1", 0.9)
    # C2 and C3 see nothing
    engine.update_node_suspicion("C2", 0.1)
    engine.update_node_suspicion("C3", 0.1)
    
    # Propagate
    results = engine.propagate_suspicion(diffusion_factor=0.5)
    
    # C2 should increase because it's next to C1
    assert results["C2"] > 0.1, "Suspicion did not diffuse to C2"
    # C1 should increase because it diffuses to itself? Actually in adjacency it only diffuses from neighbors.
    # So C1 gets diffusion from C2.
    assert "C3" in results
