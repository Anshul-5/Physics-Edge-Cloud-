"""
Champion / Challenger Model Promotion Pipeline (L7 Retraining Layer)

Implements continuous learning validation loops comparing retrained challenger models
against the active production champion model using statistical hypothesis testing.

Promotion Gate Condition:
    AUPRC_challenger - AUPRC_champion >= 1.96 * SE_diff
"""

import math
import time
import numpy as np
from typing import Dict, List, Tuple, Optional, Any


def compute_auprc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """
    Computes the Area Under the Precision-Recall Curve (AUPRC / Average Precision).
    
    Args:
        y_true: Binary ground truth labels (0 or 1).
        y_score: Continuous predicted risk scores in [0, 1].
        
    Returns:
        float: AUPRC value in [0, 1].
    """
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    
    if len(y_true) != len(y_score):
        raise ValueError("y_true and y_score must have the same length.")
    if len(y_true) == 0:
        return 0.0
    if np.sum(y_true) == 0:
        return 0.0  # No positive samples
        
    # Sort scores in descending order
    desc_order = np.argsort(y_score)[::-1]
    y_true_sorted = y_true[desc_order]
    y_score_sorted = y_score[desc_order]
    
    # Identify unique score thresholds
    distinct_indices = np.where(np.diff(y_score_sorted))[0]
    threshold_indices = np.r_[distinct_indices, y_true_sorted.size - 1]
    
    # True Positives and Cumulative True Positives
    tps = np.cumsum(y_true_sorted)[threshold_indices]
    fps = (1 + threshold_indices) - tps
    
    total_positives = np.sum(y_true)
    
    recalls = tps / total_positives
    precisions = tps / (tps + fps)
    
    # Prepend recall 0, precision 1
    recalls = np.r_[0.0, recalls]
    precisions = np.r_[1.0, precisions]
    
    # Area under precision-recall curve via trapezoidal / step integration
    auprc = np.sum((recalls[1:] - recalls[:-1]) * precisions[1:])
    return float(np.clip(auprc, 0.0, 1.0))


def compute_bootstrap_se_diff(
    y_true: np.ndarray,
    y_score_champion: np.ndarray,
    y_score_challenger: np.ndarray,
    n_bootstraps: int = 500,
    seed: Optional[int] = 42
) -> Tuple[float, float, float]:
    """
    Estimates the standard error of the AUPRC difference using paired non-parametric bootstrapping.
    
    Returns:
        Tuple of (delta_auprc, se_diff, z_score)
    """
    y_true = np.asarray(y_true, dtype=int)
    y_score_champ = np.asarray(y_score_champion, dtype=float)
    y_score_chal = np.asarray(y_score_challenger, dtype=float)
    
    n_samples = len(y_true)
    if n_samples == 0:
        return 0.0, 0.0, 0.0
        
    auprc_champ = compute_auprc(y_true, y_score_champ)
    auprc_chal = compute_auprc(y_true, y_score_chal)
    delta_auprc = auprc_chal - auprc_champ
    
    rng = np.random.default_rng(seed)
    diffs = []
    
    for _ in range(n_bootstraps):
        boot_idx = rng.choice(n_samples, size=n_samples, replace=True)
        boot_y = y_true[boot_idx]
        if np.sum(boot_y) == 0:
            continue  # Skip all-negative bootstrap samples
        b_champ = compute_auprc(boot_y, y_score_champ[boot_idx])
        b_chal = compute_auprc(boot_y, y_score_chal[boot_idx])
        diffs.append(b_chal - b_champ)
        
    if len(diffs) < 2:
        se_diff = 1e-6
    else:
        se_diff = float(np.std(diffs, ddof=1))
        
    # Prevent division by zero
    se_diff = max(se_diff, 1e-6)
    z_score = delta_auprc / se_diff
    return delta_auprc, se_diff, z_score


class ModelRegistryRecord:
    def __init__(
        self,
        model_id: str,
        version: str,
        auprc: float,
        is_champion: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.model_id = model_id
        self.version = version
        self.auprc = auprc
        self.is_champion = is_champion
        self.metadata = metadata or {}
        self.created_at = time.time()


class ChampionChallengerPipeline:
    """
    Automates champion vs. challenger model comparison and promotion gating.
    """
    def __init__(
        self,
        alpha_significance: float = 0.05,
        min_auprc_gain: float = 0.0,
        n_bootstraps: int = 500
    ):
        """
        Args:
            alpha_significance: Two-tailed significance level (0.05 -> z >= 1.96).
            min_auprc_gain: Minimum absolute AUPRC gain required in addition to significance.
            n_bootstraps: Number of bootstrap iterations for standard error estimation.
        """
        self.alpha_significance = alpha_significance
        self.z_threshold = 1.96  # for alpha = 0.05
        self.min_auprc_gain = min_auprc_gain
        self.n_bootstraps = n_bootstraps
        
        self.champion: Optional[ModelRegistryRecord] = None
        self.registry: Dict[str, ModelRegistryRecord] = {}
        self.evaluation_history: List[Dict[str, Any]] = []

    def register_champion(
        self,
        model_id: str,
        version: str,
        auprc: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ModelRegistryRecord:
        """Initializes or overwrites the current baseline champion model."""
        if self.champion:
            self.champion.is_champion = False
            
        record = ModelRegistryRecord(
            model_id=model_id,
            version=version,
            auprc=auprc,
            is_champion=True,
            metadata=metadata
        )
        self.champion = record
        self.registry[version] = record
        return record

    def evaluate_challenger(
        self,
        challenger_model_id: str,
        challenger_version: str,
        y_true: np.ndarray,
        y_score_champion: np.ndarray,
        y_score_challenger: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates a challenger against the champion on a frozen validation dataset.
        
        Applies Gate:
            delta_auprc >= 1.96 * se_diff AND delta_auprc >= min_auprc_gain
        """
        if self.champion is None:
            raise RuntimeError("No active champion registered in the pipeline.")
            
        auprc_champ = compute_auprc(y_true, y_score_champion)
        auprc_chal = compute_auprc(y_true, y_score_challenger)
        
        delta_auprc, se_diff, z_score = compute_bootstrap_se_diff(
            y_true,
            y_score_champion,
            y_score_challenger,
            n_bootstraps=self.n_bootstraps
        )
        
        required_diff = self.z_threshold * se_diff
        is_statistically_significant = delta_auprc >= required_diff
        meets_min_gain = delta_auprc >= self.min_auprc_gain
        
        promoted = is_statistically_significant and meets_min_gain
        
        eval_result = {
            "challenger_model_id": challenger_model_id,
            "challenger_version": challenger_version,
            "champion_version": self.champion.version,
            "champion_auprc": float(auprc_champ),
            "challenger_auprc": float(auprc_chal),
            "delta_auprc": float(delta_auprc),
            "se_diff": float(se_diff),
            "z_score": float(z_score),
            "z_threshold": self.z_threshold,
            "required_diff": float(required_diff),
            "is_significant": bool(is_statistically_significant),
            "promoted": bool(promoted),
            "evaluated_at": time.time()
        }
        
        # If promoted, update registry and assign new champion
        if promoted:
            record = ModelRegistryRecord(
                model_id=challenger_model_id,
                version=challenger_version,
                auprc=auprc_chal,
                is_champion=True,
                metadata=metadata
            )
            self.champion.is_champion = False
            self.champion = record
            self.registry[challenger_version] = record
            eval_result["status"] = "PROMOTED"
        else:
            eval_result["status"] = "REJECTED"
            
        self.evaluation_history.append(eval_result)
        return eval_result
