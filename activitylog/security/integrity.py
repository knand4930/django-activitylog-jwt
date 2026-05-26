"""Tamper detection, credential encryption, and integrity verification."""

import base64
import hashlib
import hmac
import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_FERNET_AVAILABLE = False
try:
    from cryptography.fernet import Fernet

    _FERNET_AVAILABLE = True
except ImportError:
    pass


def _get_fernet_key() -> bytes:
    """Derive a 32-byte Fernet key from Django SECRET_KEY."""
    raw = settings.SECRET_KEY.encode()
    digest = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_credential(value: str) -> str:
    """Encrypt a database credential using Django SECRET_KEY."""
    if not _FERNET_AVAILABLE:
        logger.warning("cryptography not installed — storing credential in plain text")
        return value
    f = Fernet(_get_fernet_key())
    return f.encrypt(value.encode()).decode()


def decrypt_credential(token: str) -> str:
    """Decrypt a previously encrypted credential."""
    if not _FERNET_AVAILABLE:
        return token
    try:
        f = Fernet(_get_fernet_key())
        return f.decrypt(token.encode()).decode()
    except Exception:
        return token


# ---------------------------------------------------------------------------
# HMAC-based tamper detection
# ---------------------------------------------------------------------------

def compute_hmac(data: dict) -> str:
    """Compute HMAC-SHA256 signature for a log entry dict."""
    key = settings.SECRET_KEY.encode()
    payload = json.dumps(data, sort_keys=True, default=str).encode()
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def verify_hmac(data: dict, signature: str) -> bool:
    """Constant-time HMAC verification."""
    expected = compute_hmac(data)
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Bulk integrity checker
# ---------------------------------------------------------------------------

class IntegrityChecker:
    """Verify integrity hashes across all event tables."""

    MODELS = None  # populated lazily to avoid circular import

    def _get_models(self):
        if self.MODELS is None:
            from activitylog.models import (
                CorsEvent,
                CRUDEvent,
                LoginEvent,
                RequestEvent,
                SystemEvent,
            )
            self.MODELS = [CRUDEvent, LoginEvent, RequestEvent, CorsEvent, SystemEvent]
        return self.MODELS

    def check_all(self, fix: bool = False) -> dict:
        results = {}
        for model in self._get_models():
            results[model.__name__] = self._check_model(model, fix)
        return results

    def _check_model(self, model, fix: bool) -> dict:
        total = 0
        tampered = 0
        fixed = 0
        qs = model.objects.exclude(integrity_hash__isnull=True).iterator(chunk_size=500)
        for obj in qs:
            total += 1
            if not obj.verify_integrity():
                tampered += 1
                logger.warning("Tampered %s pk=%s", model.__name__, obj.pk)
                if fix:
                    obj.integrity_hash = obj.compute_integrity_hash()
                    obj.save(update_fields=["integrity_hash"])
                    fixed += 1
        return {"total": total, "tampered": tampered, "fixed": fixed}
