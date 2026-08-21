import time
import numpy as np
import torch
import pytest
import networkx as nx

from crop import CROP, WelfordVarianceTracker, EMAVarianceTracker
from conformal import AdaptiveConformalPredictor
from graph_engine import SpatialGraphEngine
from orchestrator import LagrangianComputeRouter, RoutingAction


def test_welford_variance_tracker():
    tracker = WelfordVarianceTracker()
    samples = [1.2, 1.5, 1.8, 2.2, 1.1, 0.9, 1.7]
    for s in samples:
        tracker.update(s)
        
    expected_mean = np.mean(samples)
    expected_var = np.var(samples, ddof=1)
    
    assert np.isclose(tracker.mean, expected_mean)
    assert np.isclose(tracker.variance, expected_var)

def test_ema_variance_tracker():
    tracker = EMAVarianceTracker(decay=0.9)
    samples = [1.0, 2.0, 3.0]
    for s in samples:
        tracker.update(s)
        
    # Manually calculate EMA mean and variance:
    # Initial: mean = 1.0, var = 1.0
    # Step 1: d = 2.0 - 1.0 = 1.0. mean = 1.0 + 0.1 * 1.0 = 1.1. var = 0.9 * (1.0 + 0.1 * 1.0) = 0.99
    # Step 2: d = 3.0 - 1.1 = 1.9. mean = 1.1 + 0.1 * 1.9 = 1.29. var = 0.9 * (0.99 + 0.1 * 3.61) = 0.9 * 1.351 = 1.2159
    assert np.isclose(tracker.mean, 1.29)
    assert np.isclose(tracker.variance, 1.2159)

def test_crop_pooling_and_latency():
    sources = ["source_a", "source_b"]
    crop = CROP(sources, tracker_type="welford")
    
    # Initialize trackers with some variance history
    # Source A has low variance (high precision)
    for _ in range(10):
        crop.update_variance("source_a", 0.5 + np.random.normal(0, 0.05))
    # Source B has high variance (low precision)
    for _ in range(10):
        crop.update_variance("source_b", 0.5 + np.random.normal(0, 0.3))
        
    # Get variances
    var_a = crop.trackers["source_a"].variance
    var_b = crop.trackers["source_b"].variance
    assert var_a < var_b
    
    # Pool risks
    scores = {"source_a": 0.8, "source_b": 0.2}
    
    t_start = time.perf_counter()
    pooled_risk = crop.pool_risks(scores)
    t_elapsed = (time.perf_counter() - t_start) * 1000  # ms
    
    # Assert execution latency is <= 2 ms
    assert t_elapsed <= 2.0, f"CROP latency exceeded: {t_elapsed:.3f} ms"
    
    # Since source_a is much more precise, the pooled risk should be biased towards source_a's score (0.8)
    assert pooled_risk > 0.5
    assert pooled_risk <= 0.8

def test_conformal_predictor_coverage():
    # Targets
    alpha = 0.05
    target_coverage = 1 - alpha  # 95%
    
    predictor = AdaptiveConformalPredictor(alpha=alpha, gamma=0.01)
    
    # Run a simulation loop to test empirical coverage
    # Generate 1500 points where we simulate a model predicting pooled risk and getting true label
    np.random.seed(42)
    
    coverage_status = []
    
    for i in range(1500):
        # Model predictions
        pred = np.random.uniform(0.1, 0.9)
        # Ground truth is close to pred + some noise
        error = np.random.normal(0, 0.15)
        true_label = np.clip(pred + error, 0.0, 1.0)
        
        # Calculate current quantile threshold
        q_threshold = predictor.get_quantile()
        
        # Check boundary
        t_start = time.perf_counter()
        _ = predictor.check_boundary(pred, q_threshold)
        t_elapsed = (time.perf_counter() - t_start) * 1000
        
        # Latency check (Acceptance Criteria is <= 1 ms)
        if i == 0:
            assert t_elapsed <= 1.0, f"Boundary check latency exceeded: {t_elapsed:.3f} ms"
            
        # Update predictor
        predictor.update(pred, true_label)
        
        # After burn-in period of 500 steps, record coverage
        if i >= 500:
            # Did the actual true label fall within the conformal prediction interval?
            # i.e., is the residual <= current quantile threshold?
            residual = abs(true_label - pred)
            covered = residual <= q_threshold
            coverage_status.append(1.0 if covered else 0.0)
            
    empirical_coverage = np.mean(coverage_status)
    print(f"Empirical Coverage: {empirical_coverage:.4f} (Target: {target_coverage:.2f})")
    
    # Acceptance criteria: empirical coverage matches target 1 - alpha within 2%
    assert abs(empirical_coverage - target_coverage) <= 0.02, \
        f"Coverage deviation too high: empirical={empirical_coverage:.4f}, target={target_coverage:.2f}"

def test_graph_spectral_instability():
    engine = SpatialGraphEngine()
    
    # Build a stable grid-like graph
    # 4 Nodes in a square
    engine.add_camera_node("A", (0, 0))
    engine.add_camera_node("B", (0, 10))
    engine.add_camera_node("C", (10, 0))
    engine.add_camera_node("D", (10, 10))
    
    engine.add_physical_adjacency("A", "B", distance_weight=1.0)
    engine.add_physical_adjacency("B", "D", distance_weight=1.0)
    engine.add_physical_adjacency("A", "C", distance_weight=1.0)
    engine.add_physical_adjacency("C", "D", distance_weight=1.0)
    
    # Initial calculation to establish baseline
    fiedler_init, is_unstable_init = engine.calculate_spectral_instability(threshold=0.15)
    assert not is_unstable_init
    
    # Disconnect C and D from the rest of the network (removing links to A and B)
    # This represents sudden group dispersal or clustering changes (network partition)
    engine.graph.remove_edge("A", "C")
    engine.graph.remove_edge("B", "D")
    
    fiedler_new, is_unstable_new = engine.calculate_spectral_instability(threshold=0.15)
    
    # Disconnected graph has second smallest eigenvalue = 0
    assert np.isclose(fiedler_new, 0.0)
    # Delta should be fiedler_init - fiedler_new
    # Since fiedler_init of a connected 4-cycle is around 0.5 (or >= 0.2), it should trigger instability
    assert is_unstable_new, f"Failed to detect spectral instability. Init: {fiedler_init}, New: {fiedler_new}"

def test_lagrangian_router_routing_decisions():
    # delta = 0.05, lambda = 10.0
    router = LagrangianComputeRouter(delta=0.05, initial_lambda=10.0)
    
    # 1. Test routing of very low risk events -> should route to SKIP
    action_low = router.decide_route(0.01)
    assert action_low == RoutingAction.SKIP
    
    # 2. Test routing of very high risk events -> should route to FULL
    action_high = router.decide_route(0.95)
    assert action_high == RoutingAction.FULL
    
    # 3. Test intermediate risk events -> should route to PARTIAL or FULL depending on lambda
    action_mid = router.decide_route(0.4)
    assert action_mid in [RoutingAction.SKIP, RoutingAction.PARTIAL, RoutingAction.FULL]

def test_lagrangian_router_lambda_update():
    router = LagrangianComputeRouter(delta=0.05, eta=0.1, initial_lambda=1.0)
    
    # Check initial lambda
    init_lambda = router.lambda_val
    
    # If chosen action is SKIP (miss factor = 1.0) and raw risk is high (e.g. 0.8),
    # then expected miss risk is 0.8. Since 0.8 > delta (0.05), lambda should increase.
    router.update_lambda(RoutingAction.SKIP, raw_risk=0.8)
    assert router.lambda_val > init_lambda
    
    # If chosen action is FULL (miss factor = 0.01) and raw risk is low (e.g. 0.1),
    # then expected miss risk is 0.001. Since 0.001 < delta (0.05), lambda should decrease.
    prev_lambda = router.lambda_val
    router.update_lambda(RoutingAction.FULL, raw_risk=0.1)
    assert router.lambda_val < prev_lambda
    
def test_lagrangian_router_outage_fallback():
    router = LagrangianComputeRouter()
    
    # Under normal latencies (e.g., 50ms)
    router.record_latency(50.0)
    assert router.decide_route(0.5) != RoutingAction.REGIONAL_FALLBACK
    
    # With a high latency spike above 1500ms (e.g., 1600ms)
    router.record_latency(1600.0)
    assert router.decide_route(0.5) == RoutingAction.REGIONAL_FALLBACK

