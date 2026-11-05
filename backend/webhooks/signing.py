"""Webhook signatures, Stripe-style: X-Nettle-Signature: t=<unix time>,v1=<hex>.

v1 = HMAC-SHA256(secret, f"{t}.{raw body}"). Receivers recompute it with their
secret, compare in constant time, and reject old timestamps (replay protection).
verify_signature() is what Nettle would publish for integrators.
"""
import hashlib
import hmac
import time

TOLERANCE_SECONDS = 300


def sign(secret, body: bytes, timestamp=None):
    timestamp = int(timestamp if timestamp is not None else time.time())
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def verify_signature(secret, header, body: bytes, now=None, tolerance=TOLERANCE_SECONDS):
    try:
        parts = dict(item.split("=", 1) for item in header.split(","))
        timestamp = int(parts["t"])
        received = parts["v1"]
    except (KeyError, ValueError):
        return False
    if abs((now if now is not None else time.time()) - timestamp) > tolerance:
        return False
    expected = sign(secret, body, timestamp).split("v1=", 1)[1]
    return hmac.compare_digest(expected, received)
