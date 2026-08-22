import networkx as nx
import numpy as np
import scipy.sparse as sp
from typing import Tuple, List

class SpatialGraphEngine:
    def __init__(self):
        """
        Manages the Spatio-Temporal Graph of all L1/L2 cameras on the site.
        """
        self.graph = nx.Graph()

    def add_camera_node(self, node_id, position):
        """
        Add a camera to the site graph.
        
        Args:
            node_id (str): Unique identifier for the camera.
            position (tuple): (x, y) coordinates of the camera.
        """
        self.graph.add_node(node_id, pos=position, suspicion=0.0)

    def add_physical_adjacency(self, node1, node2, distance_weight=1.0):
        """
        Connect two cameras that are physically adjacent or have line-of-sight.
        """
        self.graph.add_edge(node1, node2, weight=distance_weight)

    def update_node_suspicion(self, node_id, raw_suspicion):
        """
        Update the base suspicion for a specific node.
        """
        if self.graph.has_node(node_id):
            self.graph.nodes[node_id]['suspicion'] = raw_suspicion

    def propagate_suspicion(self, diffusion_factor=0.2):
        """
        Uses the Graph Laplacian to diffuse suspicion to structurally adjacent nodes.
        If Camera A sees a threat, Camera B's baseline suspicion is raised.
        
        S_new = S_old + diffusion_factor * (A * S_old)
        Where A is the adjacency matrix.
        
        Returns:
            dict: The newly propagated suspicion scores for all nodes.
        """
        if len(self.graph.nodes) == 0:
            return {}

        nodes = list(self.graph.nodes())
        
        # Get adjacency matrix
        A = nx.adjacency_matrix(self.graph, nodelist=nodes, weight='weight')
        
        # Extract current suspicion scores
        s_old = np.array([self.graph.nodes[n]['suspicion'] for n in nodes])
        
        # Diffuse
        # We use a simple diffusion model using the Adjacency matrix
        s_diffused = A.dot(s_old)
        s_new = s_old + diffusion_factor * s_diffused
        
        # Clamp to [0, 1]
        s_new = np.clip(s_new, 0.0, 1.0)
        
        # Update graph and return results
        results = {}
        for idx, n in enumerate(nodes):
            self.graph.nodes[n]['suspicion'] = s_new[idx]
            results[n] = s_new[idx]
            
        return results

    def calculate_spectral_instability(self, threshold=0.1):
        """
        Calculates the Normalized Laplacian and its Fiedler eigenvalue (second smallest eigenvalue).
        Flags instability if the difference between the previous and current Fiedler eigenvalue
        exceeds the threshold.
        
        Returns:
            tuple: (fiedler_val, is_unstable)
        """
        if len(self.graph.nodes) < 2:
            return 0.0, False
            
        try:
            # 1. Compute the Normalized Laplacian matrix
            L = nx.normalized_laplacian_matrix(self.graph)
            
            # Convert to dense or use sparse solver
            n_nodes = len(self.graph.nodes)
            if n_nodes <= 10:
                # For small graphs, dense solver is more stable
                eigenvalues = np.linalg.eigvalsh(L.toarray())
            else:
                # For larger graphs, sparse solver eigsh with k=2 SM (Smallest Magnitude)
                eigenvalues, _ = sp.linalg.eigsh(L, k=2, which='SM')
                
            # Eigenvalues are sorted in ascending order
            # The smallest eigenvalue of normalized Laplacian is always 0.
            # The second smallest is the Fiedler eigenvalue.
            fiedler_val = eigenvalues[1] if len(eigenvalues) > 1 else 0.0
        except Exception:
            # Fallback to dense eigenvalue calculation in case of solver issues
            try:
                L = nx.normalized_laplacian_matrix(self.graph).toarray()
                eigenvalues = np.linalg.eigvalsh(L)
                fiedler_val = eigenvalues[1] if len(eigenvalues) > 1 else 0.0
            except Exception:
                fiedler_val = 0.0
                
        # Compare with previous Fiedler eigenvalue
        prev_fiedler = getattr(self, '_prev_fiedler', None)
        self._prev_fiedler = fiedler_val
        
        if prev_fiedler is None:
            return fiedler_val, False
            
        # Delta lambda_2 = lambda_2(prev) - lambda_2(curr)
        # Instability when Fiedler eigenvalue decreases significantly (representing clustering/splitting)
        delta_lambda = prev_fiedler - fiedler_val
        is_unstable = delta_lambda > threshold
        return fiedler_val, is_unstable


class PedestrianInteractionGraph:
    """
    Spatiotemporal Interaction Graph for individual entities (pedestrians) within a camera view (L3 Engine).
    
    Computes Gaussian proximity and cosine-motion-similarity weighted adjacency:
        A_pq = exp(-sigma_1 ||X_p - X_q||^2) * max(0, cos(theta_motion))
    with division-by-zero guards on stationary/near-stationary velocities:
        cos(theta_motion) = 0 if ||v_p|| < eps or ||v_q|| < eps
    """
    def __init__(self, sigma_1: float = 0.5, eps: float = 1e-4):
        self.sigma_1 = sigma_1
        self.eps = eps
        self.entities = {} # entity_id -> {'pos': np.ndarray, 'vel': np.ndarray}
        self.prev_fiedler = None

    def add_pedestrian(self, entity_id, position, velocity):
        """
        Add or update pedestrian state.
        
        Args:
            entity_id (str): Unique pedestrian identifier.
            position (array-like): [x, y] ground-plane coordinate (meters).
            velocity (array-like): [vx, vy] ground-plane velocity (m/s).
        """
        self.entities[entity_id] = {
            'pos': np.asarray(position, dtype=float),
            'vel': np.asarray(velocity, dtype=float)
        }

    def clear(self):
        self.entities.clear()

    def build_adjacency_matrix(self) -> Tuple[np.ndarray, List]:
        """
        Builds the symmetric/directed spatial-motion adjacency matrix A_pq.
        
        Returns:
            Tuple[np.ndarray, List]: (Adjacency Matrix, entity_ids)
        """
        entity_ids = list(self.entities.keys())
        n = len(entity_ids)
        if n == 0:
            return np.empty((0, 0)), []
        if n == 1:
            return np.zeros((1, 1)), entity_ids

        A = np.zeros((n, n), dtype=float)
        for i in range(n):
            p_i = self.entities[entity_ids[i]]['pos']
            v_i = self.entities[entity_ids[i]]['vel']
            norm_vi = np.linalg.norm(v_i)

            for j in range(i + 1, n):
                p_j = self.entities[entity_ids[j]]['pos']
                v_j = self.entities[entity_ids[j]]['vel']
                norm_vj = np.linalg.norm(v_j)

                # 1. Gaussian spatial proximity term
                dist_sq = float(np.sum((p_i - p_j) ** 2))
                spatial_weight = np.exp(-self.sigma_1 * dist_sq)

                # 2. Motion cosine similarity with division-by-zero protection
                if norm_vi < self.eps or norm_vj < self.eps:
                    cos_theta = 0.0
                else:
                    dot_prod = float(np.dot(v_i, v_j))
                    cos_theta = max(0.0, dot_prod / (norm_vi * norm_vj))

                weight = float(spatial_weight * cos_theta)
                A[i, j] = weight
                A[j, i] = weight

        return A, entity_ids

    def compute_normalized_laplacian(self, A: np.ndarray) -> np.ndarray:
        """
        Computes the Normalized Graph Laplacian:
            L = I - D^(-1/2) A D^(-1/2)
        """
        n = A.shape[0]
        if n == 0:
            return np.empty((0, 0))
        if n == 1:
            return np.zeros((1, 1))

        d = np.sum(A, axis=1)
        d_inv_sqrt = np.zeros(n, dtype=float)
        for i in range(n):
            if d[i] > self.eps:
                d_inv_sqrt[i] = 1.0 / np.sqrt(d[i])

        D_inv_sqrt = np.diag(d_inv_sqrt)
        L = np.eye(n) - D_inv_sqrt @ A @ D_inv_sqrt
        return L

    def compute_fiedler_eigenvalue(self, L: np.ndarray) -> float:
        """
        Computes lambda_2 (Fiedler eigenvalue, algebraic connectivity).
        """
        if L.shape[0] < 2:
            return 0.0
        try:
            eigenvalues = np.linalg.eigvalsh(L)
            eigenvalues.sort()
            return float(eigenvalues[1]) if len(eigenvalues) > 1 else 0.0
        except Exception:
            return 0.0

    def detect_spectral_instability(self, threshold: float = 0.1) -> Tuple[float, bool]:
        """
        Calculates the current Fiedler eigenvalue and flags instability
        if Delta lambda_2 = lambda_2(t-1) - lambda_2(t) > threshold.
        """
        A, _ = self.build_adjacency_matrix()
        L = self.compute_normalized_laplacian(A)
        fiedler = self.compute_fiedler_eigenvalue(L)

        if self.prev_fiedler is None:
            self.prev_fiedler = fiedler
            return fiedler, False

        delta_lambda = self.prev_fiedler - fiedler
        is_unstable = delta_lambda > threshold
        self.prev_fiedler = fiedler

        return fiedler, is_unstable


