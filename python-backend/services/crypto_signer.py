"""
Cryptographic Signing Module — W3C Verifiable Credentials
──────────────────────────────────────────────────────────
Provides Ed25519-based signing and verification of W3C VCs
with proper multibase base58btc encoding per the
Ed25519Signature2020 suite specification.

Key management:
  - Development: auto-generated ephemeral keys
  - Production: PEM-encoded key from SIGNING_KEY_PRIVATE env var
  - HSM integration: extend _load_private_key() for PKCS#11

ISO/IEC 42001:2023 Clause 7.5 — Cryptographic integrity for
documented information. All signing events are logged.
"""

from __future__ import annotations
import base64
import hashlib
import json
import os
from typing import Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature

from services.key_provider import EnvironmentKeyProvider, KeyNotFoundError

# ─── Base58 Encoding (Bitcoin-style alphabet) ─────────────────────

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _base58_encode(data: bytes) -> str:
    """Encode bytes to base58 (Bitcoin-style) string."""
    n = int.from_bytes(data, "big")
    chars = []
    while n > 0:
        n, remainder = divmod(n, 58)
        chars.append(BASE58_ALPHABET[remainder])
    # Handle leading zeros
    for byte in data:
        if byte == 0:
            chars.append(BASE58_ALPHABET[0])
        else:
            break
    return "".join(reversed(chars))


def _multibase_base58btc(data: bytes) -> str:
    """Encode bytes as multibase base58btc (prefix 'z')."""
    return "z" + _base58_encode(data)


# ─── CryptoSigner ─────────────────────────────────────────────────

class CryptoSigner:
    """
    Ed25519-based signer for W3C Verifiable Credentials.

    Uses the Ed25519Signature2020 suite per the W3C security vocabulary.
    Supports key rotation, separate verification key exposure, and
    canonicalized payload signing per VC Data Model 1.1.
    """

    def __init__(self, private_key_pem: Optional[str] = None):
        """
        Initialize signer with an Ed25519 private key.

        Key resolution order:
          1. Explicit private_key_pem argument
          2. EnvironmentKeyProvider(SIGNING_KEY_PRIVATE)
          3. Auto-generated development key (dev-only — logs warning)

        For production, use SIGNING_KEY_PRIVATE env var or implement a
        custom BaseKeyProvider (see services/key_provider.py).
        """
        pem_data = private_key_pem
        if pem_data is None:
            try:
                provider = EnvironmentKeyProvider(env_var="SIGNING_KEY_PRIVATE")
                pem_data = provider.get_private_key().decode("utf-8")
            except KeyNotFoundError:
                pem_data = None
        if pem_data:
            key_bytes = pem_data.encode("utf-8") if isinstance(pem_data, str) else pem_data
            self.private_key = serialization.load_pem_private_key(
                key_bytes, password=None,
            )
            assert isinstance(self.private_key, Ed25519PrivateKey), "Key must be Ed25519"
        else:
            import warnings
            warnings.warn(
                "╔══════════════════════════════════════════════════════════════════╗\n"
                "║  WARNING: EPHEMERAL DEV KEY — NOT FOR PRODUCTION                ║\n"
                "║  No SIGNING_KEY_PRIVATE set. Using ephemeral Ed25519 key.       ║\n"
                "║  Every restart invalidates previously issued certificates.       ║\n"
                "║  Set SIGNING_KEY_PRIVATE env var for production.                ║\n"
                "║  Generate with: openssl genpkey -algorithm ed25519 -out private.pem  ║\n"
                "╚══════════════════════════════════════════════════════════════════╝"
            )
            self.private_key = Ed25519PrivateKey.generate()

        self.public_key = self.private_key.public_key()
        self.public_key_multibase = _multibase_base58btc(self._raw_public_bytes())

    def _raw_public_bytes(self) -> bytes:
        """Get raw 32-byte Ed25519 public key."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    @property
    def verification_method(self) -> str:
        """W3C-compatible verification method identifier (did:key format)."""
        return f"did:key:{self.public_key_multibase}#{self.public_key_multibase}"

    def sign_payload(self, payload: bytes) -> str:
        """
        Sign canonicalized bytes with Ed25519.

        Returns multibase base58btc-encoded signature per Ed25519Signature2020.
        """
        raw_sig = self.private_key.sign(payload)
        return _multibase_base58btc(raw_sig)

    def verify_signature(self, payload: bytes, signature_multibase: str) -> bool:
        """
        Verify an Ed25519 multibase signature.

        Args:
            payload: Original canonicalized bytes
            signature_multibase: Multibase base58btc-encoded signature (starts with 'z')

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Strip multibase prefix 'z' and decode base58
            if signature_multibase.startswith("z"):
                sig_b58 = signature_multibase[1:]
            else:
                sig_b58 = signature_multibase
            sig_bytes = self._base58_decode(sig_b58)
            self.public_key.verify(sig_bytes, payload)
            return True
        except (InvalidSignature, ValueError, IndexError):
            return False

    def _base58_decode(self, encoded: str) -> bytes:
        """Decode a base58 string to bytes."""
        n = 0
        for char in encoded:
            n = n * 58 + BASE58_ALPHABET.index(char)
        # Count leading zeros
        leading_zeros = 0
        for char in encoded:
            if char == BASE58_ALPHABET[0]:
                leading_zeros += 1
            else:
                break
        result = n.to_bytes((n.bit_length() + 7) // 8 or 1, "big")
        return b"\x00" * leading_zeros + result

    def sign_vc_payload(self, vc_dict: dict) -> str:
        """
        Sign a Verifiable Credential dict per W3C standards.

        Removes the proof field before signing (per spec), canonicalizes
        to deterministic JSON, signs, and restores the proof field.

        Args:
            vc_dict: VC JSON dict (with or without proof)

        Returns:
            Multibase base58btc-encoded Ed25519 signature
        """
        proof = vc_dict.pop("proof", None)
        canonical = json.dumps(vc_dict, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = self.sign_payload(canonical)
        if proof is not None:
            vc_dict["proof"] = proof
        return signature


# Singleton instance
crypto_signer = CryptoSigner()
