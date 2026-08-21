import numpy as np
import pytest
import uuid
from promotion import compute_auprc, compute_bootstrap_se_diff, ChampionChallengerPipeline
from canary import SPRTController, SPRTDecision, CanaryRolloutScheduler, CanaryState


# =====================================================================
# Tests: Champion / Challenger Promotion Pipeline (L7 Retraining)
# =====================================================================

def test_compute_auprc_perfect():
    y_true = np.array([1, 1, 1, 0, 0, 0])
    y_score = np.array([0.9, 0.8, 0.7, 0.3, 0.2, 0.1])
    auprc = compute_auprc(y_true, y_score)
    assert np.isclose(auprc, 1.0)


def test_compute_auprc_random():
    np.random.seed(42)
    y_true = np.random.choice([0, 1], size=1000, p=[0.8, 0.2])
    y_score = np.random.uniform(0, 1, size=1000)
    auprc = compute_auprc(y_true, y_score)
    # For a random classifier, AUPRC should be roughly equal to the positive prevalence (0.2)
    assert 0.15 <= auprc <= 0.28


def test_champion_challenger_promotion_success():
    np.random.seed(42)
    n = 1000
    y_true = np.random.choice([0, 1], size=n, p=[0.7, 0.3])
    
    # Champion: moderate accuracy
    y_score_champ = np.clip(y_true * 0.5 + np.random.normal(0.3, 0.2, n), 0, 1)
    
    # Challenger: significantly improved accuracy
    y_score_chal = np.clip(y_true * 0.8 + np.random.normal(0.2, 0.1, n), 0, 1)
    
    pipeline = ChampionChallengerPipeline(alpha_significance=0.05, n_bootstraps=300)
    
    champ_auprc = compute_auprc(y_true, y_score_champ)
    pipeline.register_champion("model-yolo-v1", "v1.0.0", champ_auprc)
    
    result = pipeline.evaluate_challenger(
        challenger_model_id="model-yolo-v2",
        challenger_version="v2.0.0",
        y_true=y_true,
        y_score_champion=y_score_champ,
        y_score_challenger=y_score_chal
    )
    
    assert result["promoted"] is True
    assert result["status"] == "PROMOTED"
    assert result["is_significant"] is True
    assert result["delta_auprc"] > result["required_diff"]
    assert pipeline.champion.version == "v2.0.0"


def test_champion_challenger_rejection():
    np.random.seed(42)
    n = 500
    y_true = np.random.choice([0, 1], size=n, p=[0.7, 0.3])
    
    # Champion: high accuracy
    y_score_champ = np.clip(y_true * 0.8 + np.random.normal(0.2, 0.1, n), 0, 1)
    
    # Challenger: worse accuracy
    y_score_chal = np.clip(y_true * 0.4 + np.random.normal(0.3, 0.2, n), 0, 1)
    
    pipeline = ChampionChallengerPipeline(alpha_significance=0.05, n_bootstraps=200)
    champ_auprc = compute_auprc(y_true, y_score_champ)
    pipeline.register_champion("model-yolo-v1", "v1.0.0", champ_auprc)
    
    result = pipeline.evaluate_challenger(
        challenger_model_id="model-yolo-v2",
        challenger_version="v2.0.0",
        y_true=y_true,
        y_score_champion=y_score_champ,
        y_score_challenger=y_score_chal
    )
    
    assert result["promoted"] is False
    assert result["status"] == "REJECTED"
    assert pipeline.champion.version == "v1.0.0"


# =====================================================================
# Tests: SPRT False Alarm Rate Rollback Controller (L8 Delivery)
# =====================================================================

def test_sprt_controller_clean_stream():
    # p0 = 0.01 (1%), stream has ~0.5% FAR -> should accept H0
    sprt = SPRTController(p0=0.01, p1=0.05, alpha=0.05, beta=0.05)
    
    decisions = []
    np.random.seed(42)
    for _ in range(300):
        # 0.5% chance of false alarm
        is_fa = np.random.rand() < 0.005
        d = sprt.update(is_fa)
        decisions.append(d)
        if d == SPRTDecision.ACCEPT_H0:
            break
            
    assert SPRTDecision.ACCEPT_H0 in decisions
    assert sprt.is_aborted is False


def test_sprt_controller_rollback_trigger():
    # Simulated bad canary model generating 15% false alarm rate (target p0=1%, p1=5%)
    rollback_called = []
    
    def on_rollback(metrics):
        rollback_called.append(metrics)
        
    sprt = SPRTController(p0=0.01, p1=0.05, alpha=0.05, beta=0.05, on_rollback_callback=on_rollback)
    
    np.random.seed(42)
    for _ in range(200):
        # 15% false alarm rate
        is_fa = np.random.rand() < 0.15
        d = sprt.update(is_fa)
        if d == SPRTDecision.REJECT_H0:
            break
            
    assert sprt.decision == SPRTDecision.REJECT_H0
    assert sprt.is_aborted is True
    assert len(rollback_called) == 1
    assert rollback_called[0]["s_n"] >= sprt.B


def test_sprt_input_validation():
    with pytest.raises(ValueError, match="Requires 0 < p0 < p1 < 1"):
        SPRTController(p0=0.05, p1=0.01)
        
    with pytest.raises(ValueError, match="Requires 0 < alpha, beta < 1"):
        SPRTController(alpha=-0.1)


# =====================================================================
# Tests: Progressive Canary Rollout Scheduler (L8 Delivery)
# =====================================================================

def test_canary_progressive_rollout_lifecycle():
    scheduler = CanaryRolloutScheduler(
        champion_version="v1.0.0",
        challenger_version="v2.0.0",
        stages=[0.05, 0.20, 1.00]
    )
    
    # 1. Start Rollout
    scheduler.start_rollout()
    assert scheduler.state == CanaryState.IN_PROGRESS
    assert scheduler.current_stage_idx == 0
    
    # Test fleet distribution at 5% stage
    num_devices = 500
    device_ids = [f"camera-node-{uuid.uuid4()}" for _ in range(num_devices)]
    
    v2_count_stage0 = sum(
        1 for d in device_ids if scheduler.get_device_target_version(d) == "v2.0.0"
    )
    # Roughly 5% (around 15-40 out of 500)
    assert 10 <= v2_count_stage0 <= 45
    
    # 2. Advance to Stage 1 (20%)
    success = scheduler.advance_stage()
    assert success is True
    assert scheduler.current_stage_idx == 1
    
    v2_count_stage1 = sum(
        1 for d in device_ids if scheduler.get_device_target_version(d) == "v2.0.0"
    )
    # Roughly 20% (around 70-130 out of 500)
    assert 70 <= v2_count_stage1 <= 130
    
    # 3. Advance to Stage 2 (100% full promotion stage)
    success = scheduler.advance_stage()
    assert success is True
    assert scheduler.current_stage_idx == 2
    
    # All devices receive v2.0.0 at 100% stage
    for d in device_ids:
        assert scheduler.get_device_target_version(d) == "v2.0.0"

    # 4. Finalize rollout completion
    success = scheduler.advance_stage()
    assert success is True
    assert scheduler.state == CanaryState.COMPLETED


def test_canary_automated_rollback_interception():
    scheduler = CanaryRolloutScheduler(
        champion_version="v1.0.0",
        challenger_version="v2.0.0",
        stages=[0.05, 0.20, 1.00]
    )
    scheduler.start_rollout()
    
    device_id = "camera-sample-target"
    # Force high false alarm injection
    for _ in range(50):
        decision = scheduler.record_canary_alert(is_false_alarm=True)
        if decision == SPRTDecision.REJECT_H0:
            break
            
    # Automated rollback should have fired
    assert scheduler.state == CanaryState.ROLLED_BACK
    # All devices immediately revert to champion
    assert scheduler.get_device_target_version(device_id) == "v1.0.0"
    # Cannot advance when aborted
    assert scheduler.advance_stage() is False
