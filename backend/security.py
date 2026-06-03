"""Security hardening helpers:
- Brute force protection (in-memory, per email+IP).
- Per-IP rate limiting (sliding window, in-memory).
- Security response headers middleware.

All in-memory: works fine for single-instance deployment. For multi-instance
deployments, swap stores with Redis. Comments below mark the swap points.
"""
from __future__ import annotations

import os
import time
import asyncio
from collections import defaultdict, deque
from typing import Dict, Tuple, Deque

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# ---------- Config (env-overridable) ----------
BRUTE_FAIL_LIMIT = int(os.environ.get("BRUTE_FAIL_LIMIT", "3"))
BRUTE_LOCK_MINUTES = int(os.environ.get("BRUTE_LOCK_MINUTES", "30"))
RATE_LIMIT_AUTH_PER_MIN = int(os.environ.get("RATE_LIMIT_AUTH_PER_MIN", "30"))
RATE_LIMIT_GENERAL_PER_MIN = int(os.environ.get("RATE_LIMIT_GENERAL_PER_MIN", "200"))

_lock = asyncio.Lock()

# ----- Brute-force store: { (email_lower, ip): {"fails": int, "lock_until": ts} } -----
_brute: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(
    lambda: {"fails": 0, "lock_until": 0.0}
)

# ----- Rate limit store: { (ip, bucket): deque[timestamps] } -----
_rl: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    """Return best-guess client IP (respects X-Forwarded-For if present)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# ===================== BRUTE FORCE =====================
async def check_brute(email: str, ip: str) -> None:
    """Raise 429 if (email, ip) is locked out."""
    key = (email.lower(), ip)
    async with _lock:
        entry = _brute[key]
        now = time.time()
        if entry["lock_until"] > now:
            remain = int(entry["lock_until"] - now)
            mins = max(1, remain // 60)
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Akun/IP terkunci karena terlalu banyak percobaan login gagal. "
                    f"Coba lagi dalam {mins} menit."
                ),
            )


async def record_failed_login(email: str, ip: str) -> None:
    """Increment fail counter. Lock if threshold reached."""
    key = (email.lower(), ip)
    async with _lock:
        entry = _brute[key]
        entry["fails"] += 1
        if entry["fails"] >= BRUTE_FAIL_LIMIT:
            entry["lock_until"] = time.time() + BRUTE_LOCK_MINUTES * 60


async def reset_login_attempts(email: str, ip: str) -> None:
    """On successful login, clear counters."""
    key = (email.lower(), ip)
    async with _lock:
        _brute[key] = {"fails": 0, "lock_until": 0.0}


async def get_brute_status(email: str, ip: str) -> dict:
    key = (email.lower(), ip)
    async with _lock:
        entry = _brute[key]
        return {
            "fails": entry["fails"],
            "locked": entry["lock_until"] > time.time(),
            "lock_until_ts": entry["lock_until"],
        }


# ===================== RATE LIMIT =====================
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding-window rate limit. Higher limit on /api/auth/* not granted —
    those are protected separately by brute force AND a tighter bucket below."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Skip rate limiting for non-API paths (let nginx/static handle)
        if not path.startswith("/api/"):
            return await call_next(request)

        ip = _client_ip(request)
        is_auth = path.startswith("/api/auth/")
        bucket = "auth" if is_auth else "general"
        limit = RATE_LIMIT_AUTH_PER_MIN if is_auth else RATE_LIMIT_GENERAL_PER_MIN

        now = time.time()
        window_start = now - 60.0
        key = (ip, bucket)
        async with _lock:
            dq = _rl[key]
            while dq and dq[0] < window_start:
                dq.popleft()
            if len(dq) >= limit:
                # Tell client how long to wait
                retry_after = int(dq[0] + 60 - now) if dq else 60
                return Response(
                    content=(
                        f'{{"detail":"Terlalu banyak permintaan. '
                        f'Coba lagi dalam {retry_after} detik.","error":"rate_limited"}}'
                    ),
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": str(max(1, retry_after))},
                )
            dq.append(now)
        return await call_next(request)


# ===================== SECURITY HEADERS =====================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Defense-in-depth response headers."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        h = response.headers
        # HSTS — force HTTPS for 1 year (only enable when on HTTPS).
        # Browsers ignore on http://, so safe to always send.
        h.setdefault("Strict-Transport-Security",
                     "max-age=31536000; includeSubDomains")
        # Prevent MIME-sniffing
        h.setdefault("X-Content-Type-Options", "nosniff")
        # Mitigate clickjacking
        h.setdefault("X-Frame-Options", "DENY")
        # Referrer minimization
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # Disable powerful features the app doesn't use
        h.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )
        # Conservative CSP for API JSON responses (no executable content)
        if response.media_type == "application/json":
            h.setdefault("Content-Security-Policy",
                         "default-src 'none'; frame-ancestors 'none'")
        # Cache control for sensitive endpoints
        if request.url.path.startswith("/api/"):
            h.setdefault("Cache-Control", "no-store")
        return response
