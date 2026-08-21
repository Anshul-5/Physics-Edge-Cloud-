import time
from enum import Enum

class RoutingAction(Enum):
    SKIP = "skip"                           # Skip cloud analysis (lowest cost, highest risk)
    PARTIAL = "partial"                     # Execute light-weight processing (medium cost, medium risk)
    FULL = "full"                           # Execute full heavy analysis (highest cost, lowest risk)
    REGIONAL_FALLBACK = "regional_fallback" # Outage fallback routed to local regional nodes


class LagrangianComputeRouter:
    def __init__(self, delta=0.05, eta=0.01, initial_lambda=1.0, 
                 cost_skip=0.05, cost_partial=0.3, cost_full=1.0,
                 miss_factor_skip=1.0, miss_factor_partial=0.15, miss_factor_full=0.01):
        """
        Cost-Risk Lagrangian Compute Router.
        Minimizes expected compute cost subject to a missed-detection risk budget delta:
        min E[Cost] + lambda * (E[Miss Risk] - delta)
        
        Args:
            delta (float): Risk budget (maximum allowed expected miss risk).
            eta (float): Learning rate for updating the Lagrangian multiplier lambda.
            initial_lambda (float): Initial value for the Lagrangian multiplier lambda.
            cost_skip (float): Compute cost for SKIP action.
            cost_partial (float): Compute cost for PARTIAL action.
            cost_full (float): Compute cost for FULL action.
            miss_factor_skip (float): Fraction of risk missed under SKIP action.
            miss_factor_partial (float): Fraction of risk missed under PARTIAL action.
            miss_factor_full (float): Fraction of risk missed under FULL action.
        """
        self.delta = delta
        self.eta = eta
        self.lambda_val = initial_lambda
        
        # Action costs
        self.costs = {
            RoutingAction.SKIP: cost_skip,
            RoutingAction.PARTIAL: cost_partial,
            RoutingAction.FULL: cost_full
        }
        
        # Action miss risk factors (expected miss risk = factor * raw_risk)
        self.miss_factors = {
            RoutingAction.SKIP: miss_factor_skip,
            RoutingAction.PARTIAL: miss_factor_partial,
            RoutingAction.FULL: miss_factor_full
        }
        
        # Outage fallback tracking
        self.connection_timeout_threshold = 1500.0  # ms
        self.recent_latencies = []
        self.max_latency_history = 5
        self.consecutive_timeouts = 0
        
    def record_latency(self, latency_ms):
        """
        Record communication telemetry latency to check for outages.
        """
        self.recent_latencies.append(latency_ms)
        if len(self.recent_latencies) > self.max_latency_history:
            self.recent_latencies.pop(0)
            
        if latency_ms > self.connection_timeout_threshold:
            self.consecutive_timeouts += 1
        else:
            self.consecutive_timeouts = 0
            
    def decide_route(self, raw_risk):
        """
        Selects the optimal routing target based on the incoming raw risk probability.
        If connection telemetry indicates an outage, routes to REGIONAL_FALLBACK.
        """
        t_start = time.perf_counter()
        
        # Check outage fallback: if last recorded latency exceeds 1500ms
        # or we have consecutive timeouts
        if self.recent_latencies and self.recent_latencies[-1] > self.connection_timeout_threshold:
            return RoutingAction.REGIONAL_FALLBACK
            
        if self.consecutive_timeouts >= 2:
            return RoutingAction.REGIONAL_FALLBACK
            
        # Optimization: min_a (Cost_a + lambda * (MissRisk_a(P) - delta))
        # Since lambda * -delta is a constant across all actions, we minimize:
        # Cost_a + lambda * MissRisk_a(P)
        best_action = None
        min_objective = float('inf')
        
        for action in [RoutingAction.SKIP, RoutingAction.PARTIAL, RoutingAction.FULL]:
            cost = self.costs[action]
            miss_risk = self.miss_factors[action] * raw_risk
            
            objective = cost + self.lambda_val * miss_risk
            if objective < min_objective:
                min_objective = objective
                best_action = action
                
        t_elapsed = (time.perf_counter() - t_start) * 1000  # ms
        
        return best_action
        
    def update_lambda(self, chosen_action, raw_risk, was_missed=None):
        """
        Updates the Lagrangian multiplier lambda using gradient ascent on the dual problem.
        
        Args:
            chosen_action (RoutingAction): The action that was executed.
            raw_risk (float): The raw risk score of the event.
            was_missed (bool, optional): Whether a threat was actually missed in practice.
                If provided, we use the actual realized miss status (1.0 or 0.0) for the update.
                Otherwise, we use the expected miss risk (miss_factor * raw_risk).
        """
        if chosen_action == RoutingAction.REGIONAL_FALLBACK:
            return  # Do not update lambda during outage fallback
            
        # Expected or actual miss risk
        if was_missed is not None:
            actual_miss_risk = 1.0 if was_missed else 0.0
        else:
            actual_miss_risk = self.miss_factors[chosen_action] * raw_risk
            
        # Update rule: lambda_{t+1} = max(0, lambda_t + eta * (ActualMissRisk - delta))
        self.lambda_val += self.eta * (actual_miss_risk - self.delta)
        self.lambda_val = max(0.0, self.lambda_val)
