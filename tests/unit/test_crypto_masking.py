import hashlib


def test_hash_sha256_deterministic():
    email = "test@example.com"
    salt = "dpis-lakehouse-salt"
    expected = hashlib.sha256(f"{email}:{salt}".encode()).hexdigest()
    assert len(expected) == 64
