"""
tools/totp_utils.py (SIH PS 26117)
==================================
TOTP (Time-based One-Time Password) & Emergency Recovery Code Utilities.
Provides air-gapped TOTP secret generation, QR code rendering, code verification,
and single-use backup recovery code management.
"""

import io
import json
import pyotp
import qrcode
import base64
import secrets
import hashlib
import logging
from typing import Tuple, List, Dict, Any, Optional

from tools.rbac import hash_password, verify_password
from tools.db import execute_query

ISSUER_NAME = "SovereignWorkbench"


def generate_totp_secret() -> str:
    """Generates a random Base32 TOTP secret string."""
    return pyotp.random_base32()


def generate_totp_qr_data_url(username: str, secret: str) -> Tuple[str, str]:
    """
    Generates an otpauth:// URI and converts it to a PNG base64 Data URL string.
    Returns (otpauth_uri, qr_data_url).
    """
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=username, issuer_name=ISSUER_NAME)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_png = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return provisioning_uri, f"data:image/png;base64,{b64_png}"


def generate_backup_codes(count: int = 8) -> Tuple[List[str], List[str]]:
    """
    Generates single-use emergency recovery codes.
    Returns (raw_codes, hashed_codes).
    Raw codes are displayed once to the user to copy/print.
    Hashed codes are persisted in the database for secure verification.
    """
    raw_codes = []
    hashed_codes = []

    for _ in range(count):
        # 8-character alphanumeric string split into two 4-char groups e.g. "a1b2-c3d4"
        code_part1 = secrets.token_hex(2)
        code_part2 = secrets.token_hex(2)
        raw_code = f"{code_part1}-{code_part2}"
        raw_codes.append(raw_code)

        # Hash code using SHA-256 for fast, deterministic single-use lookup
        hashed_code = hashlib.sha256(raw_code.encode("utf-8")).hexdigest()
        hashed_codes.append(hashed_code)

    return raw_codes, hashed_codes


def verify_totp_code(secret: str, code: str) -> bool:
    """
    Verifies a 6-digit TOTP code against the secret key.
    Allows valid_window=1 (±30s clock drift tolerance for air-gapped environments).
    """
    if not secret or not code:
        return False
    clean_code = str(code).strip().replace(" ", "")
    if len(clean_code) != 6 or not clean_code.isdigit():
        return False

    totp = pyotp.TOTP(secret)
    return totp.verify(clean_code, valid_window=1)


def verify_and_consume_backup_code(user_id: str, raw_code: str) -> bool:
    """
    Checks if raw_code matches one of the user's single-use recovery codes.
    If matched, consumes (removes) that code from the user's database entry and returns True.
    """
    if not user_id or not raw_code:
        return False

    clean_code = str(raw_code).strip().lower().replace(" ", "")
    hashed_input = hashlib.sha256(clean_code.encode("utf-8")).hexdigest()

    row = execute_query(
        "SELECT backup_codes FROM users WHERE user_id = %s",
        (user_id,),
        fetch_one=True
    )
    if not row or not row[0]:
        return False

    try:
        codes = json.loads(row[0])
        if not isinstance(codes, list):
            return False

        if hashed_input in codes:
            codes.remove(hashed_input)
            execute_query(
                "UPDATE users SET backup_codes = %s WHERE user_id = %s",
                (json.dumps(codes), user_id),
                commit=True
            )
            return True
    except Exception as e:
        logging.error(f"Error parsing backup codes for user {user_id}: {e}")

    return False
