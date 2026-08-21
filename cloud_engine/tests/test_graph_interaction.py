import numpy as np
import pytest
from graph_engine import PedestrianInteractionGraph

def test_pedestrian_graph_adjacency_and_division_guard():
    pig = PedestrianInteractionGraph(sigma_1=0.5, eps=1e-4)
    
    # Pedestrian 1: at (0, 0) moving in +X direction (1, 0)
    pig.add_pedestrian("p1", [0.0, 0.0], [1.0, 0.0])
    # Pedestrian 2: at (1, 0) moving in parallel +X direction (2, 0)
    pig.add_pedestrian("p2", [1.0, 0.0], [2.0, 0.0])
    # Pedestrian 3: stationary at (2, 0) with zero velocity (0, 0)
    pig.add_pedestrian("p3", [2.0, 0.0], [0.0, 0.0])
    
    A, entity_ids = pig.build_adjacency_matrix()
    
    assert A.shape == (3, 3)
    # p1 and p2 have parallel vectors (cos_theta = 1.0) and dist_sq = 1.0
    # Expected weight = exp(-0.5 * 1.0) * 1.0 = exp(-0.5) ~ 0.6065
    assert np.isclose(A[0, 1], np.exp(-0.5), atol=1e-3)
    assert np.isclose(A[1, 0], np.exp(-0.5), atol=1e-3)
    
    # p3 is stationary (||v||=0), division-by-zero safeguard must set cos_theta = 0.0 -> A_p3 = 0.0
    assert A[0, 2] == 0.0
    assert A[1, 2] == 0.0
    assert A[2, 0] == 0.0
    assert A[2, 1] == 0.0


def test_pedestrian_graph_laplacian_and_fiedler():
    pig = PedestrianInteractionGraph(sigma_1=0.5)
    
    # 4 pedestrians in a tightly coupled group moving in same direction
    pig.add_pedestrian("p1", [0.0, 0.0], [1.0, 1.0])
    pig.add_pedestrian("p2", [0.5, 0.5], [1.0, 1.0])
    pig.add_pedestrian("p3", [1.0, 0.0], [1.0, 1.0])
    pig.add_pedestrian("p4", [0.5, -0.5], [1.0, 1.0])
    
    A, _ = pig.build_adjacency_matrix()
    L = pig.compute_normalized_laplacian(A)
    fiedler = pig.compute_fiedler_eigenvalue(L)
    
    # Normalized Laplacian has eigenvalues in [0, 2], smallest is 0, Fiedler > 0 for connected graph
    assert fiedler > 0.0
    assert fiedler <= 2.0


def test_pedestrian_spectral_instability_detection():
    pig = PedestrianInteractionGraph(sigma_1=0.5)
    
    # Frame 1: Single cohesive group moving together
    pig.add_pedestrian("p1", [0.0, 0.0], [1.0, 0.0])
    pig.add_pedestrian("p2", [0.5, 0.0], [1.0, 0.0])
    pig.add_pedestrian("p3", [1.0, 0.0], [1.0, 0.0])
    fiedler1, is_unstable1 = pig.detect_spectral_instability(threshold=0.1)
    assert not is_unstable1
    
    # Frame 2: Sudden crowd panic/dispersion (opposing diverging directions and large distances)
    pig.add_pedestrian("p1", [0.0, 0.0], [-5.0, 0.0])
    pig.add_pedestrian("p2", [5.0, 0.0], [5.0, 0.0])
    pig.add_pedestrian("p3", [10.0, 0.0], [0.0, 5.0])
    fiedler2, is_unstable2 = pig.detect_spectral_instability(threshold=0.05)
    
    # The algebraic connectivity drops sharply as crowd breaks apart
    assert fiedler2 < fiedler1
    assert is_unstable2
