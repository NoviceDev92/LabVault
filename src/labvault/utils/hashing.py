import hashlib
from pathlib import Path

def compute_sha256(filepath: Path | str, chunk_size: int = 8192) -> str:
    """Compute the SHA-256 hash of a file efficiently by reading in chunks."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(chunk_size), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
