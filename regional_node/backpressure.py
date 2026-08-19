class BackpressureManager:
    def __init__(self, max_queue_size=50, abstain_threshold=0.8):
        """
        Manages the processing load of the L2 Server.
        
        Args:
            max_queue_size (int): The threshold at which the server enters Abstain Mode.
            abstain_threshold (float): The minimum edge_suspicion required to process 
                                       a frame when in Abstain Mode.
        """
        self.max_queue_size = max_queue_size
        self.abstain_threshold = abstain_threshold

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
        if current_queue_size > self.max_queue_size:
            # Server is under heavy load. Only accept highly suspicious frames.
            if edge_suspicion < self.abstain_threshold:
                return True
        return False
