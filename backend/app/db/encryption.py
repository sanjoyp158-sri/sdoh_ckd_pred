"""
AES-256 encryption utilities for data at rest.

Implements encryption/decryption for sensitive patient data stored in PostgreSQL.
Uses AES-256-GCM for authenticated encryption.
"""

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import base64
from typing import Optional


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data using AES-256.
    
    Uses AES-256-GCM (Galois/Counter Mode) which provides both confidentiality
    and authenticity. Each encryption operation uses a unique nonce.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption service.
        
        Args:
            encryption_key: Base64-encoded 256-bit encryption key.
                          If not provided, reads from ENCRYPTION_KEY environment variable.
        """
        if encryption_key is None:
            encryption_key = os.getenv("ENCRYPTION_KEY")
            if encryption_key is None:
                raise ValueError(
                    "Encryption key not provided. Set ENCRYPTION_KEY environment variable "
                    "or pass encryption_key parameter."
                )
        
        # Decode the base64-encoded key
        try:
            self.key = base64.b64decode(encryption_key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {e}")
        
        # Verify key length (must be 32 bytes for AES-256)
        if len(self.key) != 32:
            raise ValueError(
                f"Encryption key must be 256 bits (32 bytes), got {len(self.key)} bytes"
            )
        
        # Initialize AESGCM cipher
        self.cipher = AESGCM(self.key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string using AES-256-GCM.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded string containing nonce + ciphertext + tag
        """
        if not plaintext:
            return ""
        
        # Convert string to bytes
        plaintext_bytes = plaintext.encode('utf-8')
        
        # Generate random 96-bit nonce (12 bytes recommended for GCM)
        nonce = os.urandom(12)
        
        # Encrypt with associated data (empty in this case)
        ciphertext = self.cipher.encrypt(nonce, plaintext_bytes, None)
        
        # Combine nonce + ciphertext and encode as base64
        encrypted_data = nonce + ciphertext
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt AES-256-GCM encrypted string.
        
        Args:
            encrypted_text: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            ValueError: If decryption fails (wrong key, corrupted data, or tampered data)
        """
        if not encrypted_text:
            return ""
        
        try:
            # Decode from base64
            encrypted_data = base64.b64decode(encrypted_text)
            
            # Extract nonce (first 12 bytes) and ciphertext (remaining bytes)
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            
            # Decrypt
            plaintext_bytes = self.cipher.decrypt(nonce, ciphertext, None)
            
            # Convert bytes to string
            return plaintext_bytes.decode('utf-8')
            
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")
    
    def encrypt_bytes(self, plaintext_bytes: bytes) -> bytes:
        """
        Encrypt raw bytes using AES-256-GCM.
        
        Args:
            plaintext_bytes: Bytes to encrypt
            
        Returns:
            Encrypted bytes (nonce + ciphertext + tag)
        """
        if not plaintext_bytes:
            return b""
        
        # Generate random nonce
        nonce = os.urandom(12)
        
        # Encrypt
        ciphertext = self.cipher.encrypt(nonce, plaintext_bytes, None)
        
        # Combine nonce + ciphertext
        return nonce + ciphertext
    
    def decrypt_bytes(self, encrypted_bytes: bytes) -> bytes:
        """
        Decrypt AES-256-GCM encrypted bytes.
        
        Args:
            encrypted_bytes: Encrypted bytes
            
        Returns:
            Decrypted plaintext bytes
            
        Raises:
            ValueError: If decryption fails
        """
        if not encrypted_bytes:
            return b""
        
        try:
            # Extract nonce and ciphertext
            nonce = encrypted_bytes[:12]
            ciphertext = encrypted_bytes[12:]
            
            # Decrypt
            return self.cipher.decrypt(nonce, ciphertext, None)
            
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")


def generate_encryption_key() -> str:
    """
    Generate a new 256-bit encryption key.
    
    Returns:
        Base64-encoded 256-bit key suitable for AES-256
    """
    key = AESGCM.generate_key(bit_length=256)
    return base64.b64encode(key).decode('utf-8')


def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """
    Derive a 256-bit encryption key from a password using PBKDF2.
    
    This is useful for generating keys from user passwords or passphrases.
    
    Args:
        password: Password to derive key from
        salt: Salt for key derivation (generated if not provided)
        
    Returns:
        Tuple of (derived_key, salt)
    """
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits
        salt=salt,
        iterations=480000,  # OWASP recommendation as of 2023
    )
    
    key = kdf.derive(password.encode('utf-8'))
    return key, salt


# Global encryption service instance (initialized on first use)
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get global encryption service instance.
    
    Returns:
        EncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
