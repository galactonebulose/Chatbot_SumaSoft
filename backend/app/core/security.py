import hashlib
import os

def hash_password(password: str) -> str:
    """Hash password using cryptographically secure PBKDF2-SHA256 from standard library"""
    salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    # Store salt and hash concatenated by a colon
    return f"{salt.hex()}:{pw_hash.hex()}"

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against its PBKDF2-SHA256 hash"""
    try:
        salt_hex, hash_hex = hashed_password.split(":")
        salt = bytes.fromhex(salt_hex)
        pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return pw_hash.hex() == hash_hex
    except Exception:
        return False
