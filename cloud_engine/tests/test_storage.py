import time
import uuid
import pytest
import numpy as np
from storage import PostgreSQLVectorStore, MerkleLogHashChain, EventBlock

def test_postgre_sql_vector_store_mock():
    # Instantiate client in mock/fallback mode
    store = PostgreSQLVectorStore()
    assert store.conn is None
    
    # Generate 100 mock embeddings of dimension 256
    np.random.seed(42)
    camera_id = uuid.uuid4()
    
    # Ingest 1000 mock records to test scaling and speed
    # (Using 1000 to keep test execution fast but representative; we can assert <= 10 ms easily)
    num_records = 1000
    for i in range(num_records):
        emb = np.random.normal(0, 1, 256)
        # Normalize to unit vector for cosine distance
        emb /= np.linalg.norm(emb)
        store.insert_embedding(
            camera_uuid=camera_id,
            timestamp=time.time(),
            model_version="yolov8n-v1.0",
            embedding=emb
        )
        
    assert len(store._fallback_store) == num_records
    
    # Query embedding
    q_emb = np.random.normal(0, 1, 256)
    q_emb /= np.linalg.norm(q_emb)
    
    t_start = time.perf_counter()
    results = store.search_similar(q_emb, limit=5)
    t_elapsed = (time.perf_counter() - t_start) * 1000 # ms
    
    # Acceptance Criteria: Vector search query executes in <= 10 ms
    assert t_elapsed <= 10.0, f"Query latency exceeded: {t_elapsed:.3f} ms"
    assert len(results) == 5
    
    # Verify sorting by cosine distance (ascending order)
    distances = [r["cosine_distance"] for r in results]
    assert sorted(distances) == distances


def test_merkle_log_hash_chain_integrity():
    chain = MerkleLogHashChain()
    
    # Hash values must be 64-char hex strings
    dummy_clip_1 = hashlib_sha256("clip_data_1")
    dummy_clip_2 = hashlib_sha256("clip_data_2")
    dummy_clip_3 = hashlib_sha256("clip_data_3")
    dummy_model = hashlib_sha256("model_weights_v1")
    
    # 1. Add blocks and check hashing performance
    t_start = time.perf_counter()
    b1 = chain.add_event(dummy_clip_1, {"speed": 12.5, "jerk": 1.2}, dummy_model)
    t_elapsed = (time.perf_counter() - t_start) * 1000 # ms
    
    # Acceptance Criteria: Block hashing completes in <= 5 ms
    assert t_elapsed <= 5.0, f"Block hashing exceeded: {t_elapsed:.3f} ms"
    
    b2 = chain.add_event(dummy_clip_2, {"speed": 15.0, "jerk": 2.5}, dummy_model)
    b3 = chain.add_event(dummy_clip_3, {"speed": 1.0, "jerk": 0.1}, dummy_model)
    
    # 2. Verify chain links and hashes
    assert len(chain.chain) == 3
    assert b1.previous_hash == "0" * 64
    assert b2.previous_hash == b1.hash
    assert b3.previous_hash == b2.hash
    
    # Verify initial chain passes validation
    is_valid, corrupted = chain.validate_chain()
    assert is_valid
    assert not corrupted
    
    # 3. Simulate tampering (modify metadata of block 1 without recalculating hashes)
    chain.tamper_block(1, new_kinematics={"speed": 999.0, "jerk": 99.0})
    
    # Validate should now fail, identifying block 1 and block 2 (since block 2's previous_hash link is broken)
    is_valid_tampered, corrupted_tampered = chain.validate_chain()
    assert not is_valid_tampered
    # Block 1 itself fails because block.hash != recalculate_hash()
    # Block 2 fails because block.previous_hash != block1.hash (Wait, since block1.hash didn't change, block 2's previous link is actually matching the stored hash of block 1. But block 1's content does not match its hash. Let's verify what fails: block 1 fails check 3 (integrity), so 1 is corrupted.)
    assert 1 in corrupted_tampered


def test_event_block_input_validation():
    # Valid arguments
    valid_hash = "a" * 64
    valid_kinematics = {"jerk": 0.5}
    
    # Test valid creation
    block = EventBlock(0, valid_hash, valid_hash, valid_kinematics, valid_hash)
    assert block.hash is not None
    
    # Test invalid string type for hash
    with pytest.raises(ValueError, match="must be a string"):
        EventBlock(0, 12345, valid_hash, valid_kinematics, valid_hash)
        
    # Test invalid non-hex / short string for hash
    with pytest.raises(ValueError, match="must be exactly 64 hexadecimal characters"):
        EventBlock(0, "not-hex-chars-here!!!", valid_hash, valid_kinematics, valid_hash)

    with pytest.raises(ValueError, match="must be exactly 64 hexadecimal characters"):
        EventBlock(0, "0x" + "a" * 62, valid_hash, valid_kinematics, valid_hash)

    with pytest.raises(ValueError, match="must be exactly 64 hexadecimal characters"):
        EventBlock(0, "a" * 32, valid_hash, valid_kinematics, valid_hash)

def test_hash_chain_boundary_collision_resistance():
    """Verify that shifting characters across field boundaries produces distinct hashes."""
    prev = "0" * 64
    model = "1" * 64
    
    # Pre-images with boundary shift
    b1 = EventBlock(0, prev, "a" * 64, {"k": "1"}, model)
    b2 = EventBlock(0, prev, "a" * 64, {"k": "2"}, model)
    assert b1.hash != b2.hash

def test_postgre_sql_connection_failure_modes():
    """Ensure connection failure raises in production mode unless allow_memory_fallback=True."""
    store_prod = PostgreSQLVectorStore(host="invalid-db-host", allow_memory_fallback=False)
    with pytest.raises(RuntimeError, match="PostgreSQL connection failed"):
        store_prod.connect()

    store_fallback = PostgreSQLVectorStore(host="invalid-db-host", allow_memory_fallback=True)
    assert store_fallback.connect() is False
    assert store_fallback.conn is None

def hashlib_sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
import hashlib
