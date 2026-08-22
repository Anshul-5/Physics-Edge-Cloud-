import math

class BackpressureManager:
    def __init__(self, max_queue_size=50, abstain_threshold=0.8):
        """
        Manages the processing load of the L2 Server.
        
        Args:
            max_queue_size (int): The threshold at which the server enters Abstain Mode.
            abstain_threshold (float): The minimum edge_suspicion required to process 
                                       a frame when in Abstain Mode.
        """
        if not isinstance(max_queue_size, int) or isinstance(max_queue_size, bool) or max_queue_size <= 0:
            raise ValueError(f"max_queue_size must be a positive integer, got {max_queue_size!r}")
        if not isinstance(abstain_threshold, (int, float)) or isinstance(abstain_threshold, bool) or not math.isfinite(abstain_threshold) or not (0.0 <= abstain_threshold <= 1.0):
            raise ValueError(f"abstain_threshold must be a finite float in [0.0, 1.0], got {abstain_threshold!r}")

        self.max_queue_size = int(max_queue_size)
        self.abstain_threshold = float(abstain_threshold)

    def should_abstain(self, current_queue_size, edge_suspicion):
        """
        Determines if the server should abstain from processing an incoming frame
        based on the current queue load and the edge kinematic suspicion.
        
        Args:
            current_queue_size (int): Number of items currently in the PriorityQueue.
            edge_suspicion (float): Kinematic suspicion probability from the L1 Gate.
            
        Returns:
            bool: True if the frame should be dropped/abstained, False otherwise.
        """
        if current_queue_size >= self.max_queue_size:
            # Server is under heavy load. Fail closed on invalid/NaN suspicion
            if not isinstance(edge_suspicion, (int, float)) or isinstance(edge_suspicion, bool) or not math.isfinite(edge_suspicion):
                return True
            if edge_suspicion < self.abstain_threshold:
                return True
        return False
