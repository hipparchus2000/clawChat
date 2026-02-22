"""
Encryption module for ClawChat UDP Hole Punching.

Implements AES-256-GCM encryption for:
- Security files (PBKDF2 key derivation)
- UDP packets (session keys)
"""

import os
import base64
import hashlib
import secrets
from typing import Union, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class CryptoError(Exception):
    """Base exception for cryptographic errors."""
    pass


class DecryptionError(CryptoError):
    """Raised when decryption fails."""
    pass


class AuthenticationError(CryptoError):
    """Raised when authentication tag verification fails."""
    pass


def derive_key(password: bytes, salt: bytes, iterations: int = 100000) -> bytes:
    """
    Derive a key from password using PBKDF2-HMAC-SHA256.
    
    Args:
        password: The password/secret to derive from
        salt: Random salt
        iterations: Number of iterations (default: 100000)
        
    Returns:
        32-byte derived key
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
        backend=default_backend()
    )
    return kdf.derive(password)


def hkdf_extract(salt: bytes, input_key: bytes) -> bytes:
    """Extract phase of HKDF."""
    h = hashlib.sha256()
    h.update(salt)
    h.update(input_key)
    return h.digest()


def hkdf_expand(prk: bytes, info: bytes, length: int = 32) -> bytes:
    """Expand phase of HKDF."""
    okm = b''
    previous = b''
    counter = 1
    
    while len(okm) < length:
        h = hashlib.sha256()
        h.update(previous)
        h.update(info)
        h.update(bytes([counter]))
        previous = h.digest()
        okm += previous
        counter += 1
    
    return okm[:length]


def generate_nonce(size: int = 12) -> bytes:
    """Generate a cryptographically secure nonce."""
    return secrets.token_bytes(size)


def derive_session_keys(shared_secret: bytes, connection_id: str, timestamp: int) -> dict:
    """
    Derive multiple session keys from shared secret.
    
    Args:
        shared_secret: The shared secret from security file
        connection_id: Unique connection identifier
        timestamp: Unix timestamp
        
    Returns:
        Dictionary with encryption_key, mac_key, iv_key, next_key_seed
    """
    context = f"{connection_id}:{timestamp}".encode()
    salt = hashlib.sha256(context).digest()
    info = b"ClawChat v2.0 Session Keys"
    
    # Extract
    prk = hkdf_extract(salt, shared_secret)
    
    # Expand to 128 bytes (4x 32-byte keys)
    keys = hkdf_expand(prk, info, length=128)
    
    return {
        'encryption_key': keys[0:32],
        'mac_key': keys[32:64],
        'iv_key': keys[64:96],
        'next_key_seed': keys[96:128]
    }


class CryptoManager:
    """
    Manages encryption/decryption operations.
    
    Supports both file encryption (PBKDF2) and packet encryption (direct keys).
    """
    
    def __init__(self):
        self._session_keys = None
        self._key_expiry = 0
    
    def encrypt_file(self, plaintext: bytes, password: bytes, 
                     iterations: int = 100000) -> dict:
        """
        Encrypt data for security file storage.
        
        Args:
            plaintext: Data to encrypt
            password: Bootstrap password/key
            iterations: PBKDF2 iterations
            
        Returns:
            Dictionary with encrypted package (salt, iv, ciphertext, tag)
        """
        # Generate random salt and nonce
        salt = secrets.token_bytes(32)
        nonce = generate_nonce(12)
        
        # Derive key
        key = derive_key(password, salt, iterations)
        
        # Encrypt
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        
        # ciphertext includes auth tag at the end (16 bytes)
        actual_ciphertext = ciphertext[:-16]
        tag = ciphertext[-16:]
        
        return {
            'version': '2.0',
            'salt': base64.b64encode(salt).decode('ascii'),
            'iv': base64.b64encode(nonce).decode('ascii'),
            'ciphertext': base64.b64encode(actual_ciphertext).decode('ascii'),
            'tag': base64.b64encode(tag).decode('ascii'),
            'algorithm': 'aes-256-gcm-pbkdf2',
            'iterations': iterations
        }
    
    def decrypt_file(self, package: dict, password: bytes) -> bytes:
        """
        Decrypt security file data.
        
        Args:
            package: Encrypted package dictionary
            password: Bootstrap password/key
            
        Returns:
            Decrypted plaintext
        """
        try:
            # Decode components
            salt = base64.b64decode(package['salt'])
            nonce = base64.b64decode(package['iv'])
            ciphertext = base64.b64decode(package['ciphertext'])
            tag = base64.b64decode(package['tag'])
            iterations = package.get('iterations', 100000)
            
            # Derive key
            key = derive_key(password, salt, iterations)
            
            # Reconstruct ciphertext with tag
            full_ciphertext = ciphertext + tag
            
            # Decrypt
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, full_ciphertext, None)
            
            return plaintext
            
        except Exception as e:
            raise DecryptionError(f"Failed to decrypt: {e}")
    
    def set_session_keys(self, keys: dict):
        """Set session keys for packet encryption."""
        self._session_keys = keys
    
    def encrypt_packet(self, plaintext: bytes, associated_data: bytes = None) -> bytes:
        """
        Encrypt a UDP packet.
        
        Args:
            plaintext: Data to encrypt
            associated_data: Additional authenticated data (optional)
            
        Returns:
            nonce + ciphertext (with embedded auth tag)
        """
        if not self._session_keys:
            raise CryptoError("Session keys not set")
        
        nonce = generate_nonce(12)
        key = self._session_keys['encryption_key']
        
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
        
        return nonce + ciphertext
    
    def decrypt_packet(self, ciphertext: bytes, associated_data: bytes = None) -> bytes:
        """
        Decrypt a UDP packet.
        
        Args:
            ciphertext: nonce + ciphertext (with embedded auth tag)
            associated_data: Additional authenticated data (optional)
            
        Returns:
            Decrypted plaintext
        """
        if not self._session_keys:
            raise CryptoError("Session keys not set")
        
        if len(ciphertext) < 28:  # 12 nonce + 16 min ciphertext
            raise DecryptionError("Ciphertext too short")
        
        nonce = ciphertext[:12]
        encrypted_data = ciphertext[12:]
        key = self._session_keys['encryption_key']
        
        try:
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, encrypted_data, associated_data)
            return plaintext
        except Exception as e:
            raise AuthenticationError(f"Decryption failed: {e}")


# Example usage
if __name__ == "__main__":
    # Test encryption
    crypto = CryptoManager()
    
    # Test file encryption
    message = b"Hello, Secure World!"
    password = b"bootstrap-key-123"
    
    encrypted = crypto.encrypt_file(message, password)
    print(f"Encrypted: {encrypted}")
    
    decrypted = crypto.decrypt_file(encrypted, password)
    print(f"Decrypted: {decrypted}")
    assert decrypted == message
    
    # Test session key derivation
    shared_secret = secrets.token_bytes(32)
    keys = derive_session_keys(shared_secret, "conn-123", 1234567890)
    print(f"Session keys derived: {list(keys.keys())}")
    
    # Test packet encryption
    crypto.set_session_keys(keys)
    packet = b"Secret message"
    encrypted_packet = crypto.encrypt_packet(packet)
    decrypted_packet = crypto.decrypt_packet(encrypted_packet)
    assert decrypted_packet == packet
    
    print("All tests passed!")
