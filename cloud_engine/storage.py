import os
import time
import hashlib
import json
import logging
import uuid
import struct
import re
import math
import numpy as np

_SHA256_HEX = re.compile(r'\A[0-9a-f]{64}\Z')

class PostgreSQLVectorStore:
    def __init__(self, db_conn=None, host=None, dbname=None, user=None, password=None, port=None, allow_memory_fallback=False):
        """
        Manages PostgreSQL client connection and operations for pgvector.
        Uses environment variables or direct arguments for configuration.
        Falling back to in-memory mode requires explicit opt-in via allow_memory_fallback=True.
        """
        self.host = host or os.getenv("DB_HOST", "localhost")
        self.dbname = dbname or os.getenv("DB_NAME", "physedge")
        self.user = user or os.getenv("DB_USER", "postgres")
        self.password = password or os.getenv("DB_PASSWORD", "")
        self.port = port or os.getenv("DB_PORT", "5432")
        self.allow_memory_fallback = allow_memory_fallback
        
        self.conn = db_conn
        self.logger = logging.getLogger("physedge.storage")
        
        # In-memory fallback dictionary to simulate database for testing
        self._fallback_store = []
        
    def connect(self):
        """
        Connects to the PostgreSQL database.
        Raises RuntimeError if connection fails, unless allow_memory_fallback is True.
        """
        if self.conn is not None:
            return True
            
        try:
            import psycopg2
            self.conn = psycopg2.connect(
                host=self.host,
                database=self.dbname,
                user=self.user,
                password=self.password,
                port=self.port
            )
            self.logger.info("Successfully connected to PostgreSQL database.")
            return True
        except Exception as e:
            if not self.allow_memory_fallback:
                raise RuntimeError(f"PostgreSQL connection failed: {e}") from e
            self.logger.warning(f"PostgreSQL connection failed: {e}. Operating in VOLATILE mock/fallback mode.")
            self.conn = None
            return False

    def init_schema(self):
        """
        Creates the vector extension and schema for event embeddings.
        Follows OpenSSF security standards by using parameterized schemas where applicable.
        """
        if self.conn is None:
            # Mock mode: no-op
            return
            
        try:
            with self.conn.cursor() as cursor:
                # 1. Load the vector extension
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # 2. Create the event_embeddings table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS event_embeddings (
                        id SERIAL PRIMARY KEY,
                        camera_uuid UUID NOT NULL,
                        timestamp TIMESTAMPTZ NOT NULL,
                        model_version VARCHAR(64) NOT NULL,
                        embedding vector(256) NOT NULL
                    );
                """)
                
                # 3. Create HNSW index
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS event_embeddings_hnsw_idx 
                    ON event_embeddings USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64);
                """)
            self.conn.commit()
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise RuntimeError(f"Failed to initialize schema: {e}")

    def insert_embedding(self, camera_uuid, timestamp, model_version, embedding):
        """
        Inserts an event embedding. 
        Validates inputs and uses parameterized queries to prevent SQL injection (OpenSSF Standard).
        """
        # Validate UUID
        if isinstance(camera_uuid, uuid.UUID):
            cam_str = str(camera_uuid)
        else:
            try:
                cam_str = str(uuid.UUID(str(camera_uuid)))
            except (ValueError, TypeError, AttributeError):
                raise ValueError(f"camera_uuid must be a valid UUID, got {camera_uuid!r}")

        # Validate embedding
        if not isinstance(embedding, (list, tuple, np.ndarray)) or len(embedding) != 256:
            raise ValueError("Embedding must be a numeric list/array of exactly 256 dimensions.")
        
        emb_list = [float(x) for x in embedding]
        if not all(math.isfinite(x) for x in emb_list):
            raise ValueError("Embedding contains non-finite (NaN/Inf) values.")

        if not isinstance(model_version, str) or len(model_version) > 64 or not model_version:
            raise ValueError("Invalid model_version format.")
            
        if self.conn is None:
            # Fallback mode
            record = {
                "id": len(self._fallback_store) + 1,
                "camera_uuid": cam_str,
                "timestamp": timestamp,
                "model_version": model_version,
                "embedding": np.array(emb_list)
            }
            self._fallback_store.append(record)
            return record["id"]
            
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO event_embeddings (camera_uuid, timestamp, model_version, embedding)
                    VALUES (%s, %s, %s, %s) RETURNING id;
                """, (cam_str, timestamp, model_version, emb_list))
                record_id = cursor.fetchone()[0]
            self.conn.commit()
            return record_id
        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"Database insertion failed: {e}")

    def search_similar(self, query_embedding, limit=5):
        """
        Performs a cosine similarity search against event embeddings.
        Uses parameterized query to prevent SQL injection.
        """
        if not isinstance(query_embedding, (list, tuple, np.ndarray)) or len(query_embedding) != 256:
            raise ValueError("Query embedding must be of size 256.")
            
        q_list = [float(x) for x in query_embedding]
        if not all(math.isfinite(x) for x in q_list):
            raise ValueError("Query embedding contains non-finite (NaN/Inf) values.")
        
        if self.conn is None:
            if not self._fallback_store:
                return []
            
            # Vectorized numpy calculations
            embeddings = np.array([r["embedding"] for r in self._fallback_store])
            q_arr = np.array(q_list)
            
            # Compute cosine distances: 1 - (A . B) / (||A|| * ||B||)
            dots = np.dot(embeddings, q_arr)
            norms_a = np.linalg.norm(embeddings, axis=1)
            norm_b = np.linalg.norm(q_arr)
            
            denom = norms_a * norm_b
            denom[denom == 0.0] = 1.0 # Guard division by zero
            
            distances = 1.0 - (dots / denom)
            
            # Get indices sorted by distance
            sorted_indices = np.argsort(distances)[:limit]
            
            output = []
            for idx in sorted_indices:
                record = self._fallback_store[idx]
                output.append({
                    "id": record["id"],
                    "camera_uuid": record["camera_uuid"],
                    "timestamp": record["timestamp"],
                    "model_version": record["model_version"],
                    "cosine_distance": float(distances[idx])
                })
            return output
            
        try:
            with self.conn.cursor() as cursor:
                # pgvector cosine distance operator is <=>
                cursor.execute("""
                    SELECT id, camera_uuid, timestamp, model_version, (embedding <=> %s) AS distance
                    FROM event_embeddings
                    ORDER BY distance ASC
                    LIMIT %s;
                """, (q_list, limit))
                rows = cursor.fetchall()
                
            output = []
            for row in rows:
                output.append({
                    "id": row[0],
                    "camera_uuid": row[1],
                    "timestamp": row[2],
                    "model_version": row[3],
                    "cosine_distance": float(row[4])
                })
            return output
        except Exception as e:
            raise RuntimeError(f"Search query failed: {e}")


def _encode_field(s: str) -> bytes:
    b = s.encode('utf-8')
    return struct.pack('>I', len(b)) + b


class EventBlock:
    def __init__(self, index, previous_hash, clip_hash, kinematics_data, model_hash, timestamp=None):
        self.index = index
        self.previous_hash = previous_hash
        self.clip_hash = clip_hash
        self.kinematics_data = kinematics_data
        self.model_hash = model_hash
        self.timestamp = timestamp or time.time()
        self.hash = self.calculate_hash()
        
    def calculate_hash(self):
        # Validate hex format for hashes to follow OpenSSF standards
        self._validate_hex(self.previous_hash, "previous_hash")
        self._validate_hex(self.clip_hash, "clip_hash")
        self._validate_hex(self.model_hash, "model_hash")
        
        # Serialize kinematics deterministically
        if isinstance(self.kinematics_data, dict):
            kinematics_str = json.dumps(self.kinematics_data, sort_keys=True)
        else:
            kinematics_str = str(self.kinematics_data)
            
        # Length-prefixed domain-separated canonical encoding to prevent boundary-shifting collisions
        data = (
            _encode_field(self.previous_hash.lower()) +
            _encode_field(self.clip_hash.lower()) +
            _encode_field(kinematics_str) +
            _encode_field(self.model_hash.lower())
        )
        return hashlib.sha256(data).hexdigest()

    def _validate_hex(self, value, field_name="hash"):
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string, got {type(value).__name__}")
        val = value.lower()
        if not _SHA256_HEX.match(val):
            raise ValueError(f"{field_name} must be exactly 64 hexadecimal characters, got {value!r}")


class MerkleLogHashChain:
    def __init__(self, genesis_hash=None):
        self.genesis_hash = genesis_hash or "0" * 64
        self.chain = []
        
    def add_event(self, clip_hash, kinematics, model_hash):
        """
        Creates and appends a new event block to the log.
        Computes SHA-256 with length-delimited pre-image:
        B_i = SHA256(len(B_{i-1}) || B_{i-1} || len(ClipHash) || ClipHash || len(Kinematics) || Kinematics || len(ModelHash) || ModelHash)
        """
        index = len(self.chain)
        previous_hash = self.chain[-1].hash if self.chain else self.genesis_hash
        
        block = EventBlock(index, previous_hash, clip_hash, kinematics, model_hash)
        self.chain.append(block)
        return block

    def validate_chain(self):
        """
        Verifies forensic integrity of all event logs in the chain.
        Returns a tuple: (is_valid, list of corrupted indices)
        """
        corrupted_indices = []
        
        for idx, block in enumerate(self.chain):
            # 1. Verify index
            if block.index != idx:
                corrupted_indices.append(idx)
                continue
                
            # 2. Verify previous_hash link
            expected_prev_hash = self.chain[idx - 1].hash if idx > 0 else self.genesis_hash
            if block.previous_hash != expected_prev_hash:
                corrupted_indices.append(idx)
                continue
                
            # 3. Verify current block's hash integrity
            try:
                if block.hash != block.calculate_hash():
                    corrupted_indices.append(idx)
                    continue
            except Exception:
                corrupted_indices.append(idx)
                continue
                
        is_valid = len(corrupted_indices) == 0
        return is_valid, corrupted_indices
        
    def tamper_block(self, index, new_clip_hash=None, new_kinematics=None, new_model_hash=None):
        """
        Simulates forensic tampering of historical video clips or metadata for audit verification testing.
        """
        return self._unsafe_tamper_for_tests(index, new_clip_hash=new_clip_hash, new_kinematics=new_kinematics, new_model_hash=new_model_hash)

    def _unsafe_tamper_for_tests(self, index, new_clip_hash=None, new_kinematics=None, new_model_hash=None):
        if index < 0 or index >= len(self.chain):
            raise IndexError("Block index out of bounds.")
            
        block = self.chain[index]
        if new_clip_hash is not None:
            block.clip_hash = new_clip_hash
        if new_kinematics is not None:
            block.kinematics_data = new_kinematics
        if new_model_hash is not None:
            block.model_hash = new_model_hash
