import networkx as nx
import numpy as np
import scipy.sparse as sp

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
