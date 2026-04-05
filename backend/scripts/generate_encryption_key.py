#!/usr/bin/env python3
"""
Generate a new AES-256 encryption key for the CKD prediction system.

Usage:
    python3 scripts/generate_encryption_key.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.encryption import generate_encryption_key


def main():
    """Generate and display a new encryption key."""
    print("=" * 80)
    print("CKD Prediction System - Encryption Key Generator")
    print("=" * 80)
    print()
    
    # Generate key
    key = generate_encryption_key()
    
    print("Generated AES-256 encryption key:")
    print()
    print(f"  {key}")
    print()
    print("To use this key, set it as an environment variable:")
    print()
    print(f"  export ENCRYPTION_KEY='{key}'")
    print()
    print("Or add it to your .env file:")
    print()
    print(f"  ENCRYPTION_KEY={key}")
    print()
    print("=" * 80)
    print("IMPORTANT: Store this key securely!")
    print("- Never commit this key to version control")
    print("- Use a secrets manager in production (AWS Secrets Manager, Vault, etc.)")
    print("- Keep a secure backup of this key")
    print("- If you lose this key, encrypted data cannot be recovered")
    print("=" * 80)


if __name__ == "__main__":
    main()
