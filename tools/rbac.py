"""
tools/rbac.py (SIH PS 26117)
============================
User Roles, Multi-User Isolation, RBAC Management, and Air-Gapped JWT Authentication.
Provides zero-dependency PBKDF2 password hashing, HMAC-SHA256 JWT token verification,
and PostgreSQL backend persistence.
"""

import os
import secrets
import time
import json
import hmac
import base64
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from tools.db import execute_query, get_db_connection

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "sovereign_agent_air_gapped_jwt_secret_key_2026")
LEGACY_SALT = "sovereign_pbkdf2_salt_airgap"


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hashes a plain text password using PBKDF2-HMAC-SHA256 with a unique random salt."""
    if not salt:
        salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return f"{salt}${derived}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a plain text password against stored hash, supporting both unique salts ($salt$hash) and legacy static hashes."""
    if not stored_hash:
        return False
    if "$" not in stored_hash:
        legacy_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), LEGACY_SALT.encode("utf-8"), 100000).hex()
        return hmac.compare_digest(legacy_hash, stored_hash)

    try:
        salt, derived = stored_hash.split("$", 1)
        expected = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
        return hmac.compare_digest(expected, derived)
    except Exception as e:
        logging.error(f"Error parsing stored password hash: {e}")
        return False


def create_jwt_token(user_id: str, role: str, expires_in_seconds: int = 86400 * 7) -> str:
    """Generates an air-gapped HMAC-SHA256 signed JWT token."""
    header = json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8")
    payload = json.dumps({
        "sub": user_id,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in_seconds
    }).encode("utf-8")

    b64_header = base64.urlsafe_b64encode(header).decode("utf-8").rstrip("=")
    b64_payload = base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")

    signing_input = f"{b64_header}.{b64_payload}".encode("utf-8")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    b64_signature = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")

    return f"{b64_header}.{b64_payload}.{b64_signature}"


def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verifies and decodes an HMAC-SHA256 JWT token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        b64_header, b64_payload, b64_signature = parts

        signing_input = f"{b64_header}.{b64_payload}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()

        sig_padded = b64_signature + "=" * (-len(b64_signature) % 4)
        actual_sig = base64.urlsafe_b64decode(sig_padded)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_padded = b64_payload + "=" * (-len(b64_payload) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_padded)
        payload = json.loads(payload_bytes.decode("utf-8"))

        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception as e:
        logging.error(f"Error decoding JWT token: {e}")
        return None


DEFAULT_USERS = [
    {
        "user_id": "engineer1",
        "username": "engineer1",
        "name": "Sathwik (Lead Engineer)",
        "role": "user",
        "department": "Refinery Operations",
        "avatar_color": "bg-emerald-500",
        "password": "engineer123"
    },
    {
        "user_id": "admin",
        "username": "admin",
        "name": "System Administrator",
        "role": "admin",
        "department": "Enterprise IT & Security",
        "avatar_color": "bg-blue-600",
        "password": "admin123"
    },
    {
        "user_id": "analyst1",
        "username": "analyst1",
        "name": "Dr. Ananya (Data Analyst)",
        "role": "user",
        "department": "Process & Quality Engineering",
        "avatar_color": "bg-amber-500",
        "password": "analyst123"
    }
]


def init_rbac_db(db_path: Any = None):
    """Ensures PostgreSQL default user accounts exist and 2FA columns are migrated."""
    try:
        execute_query("ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(128);", commit=True)
        execute_query("ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE;", commit=True)
        execute_query("ALTER TABLE users ADD COLUMN IF NOT EXISTS backup_codes TEXT;", commit=True)

        for u in DEFAULT_USERS:
            pwd_hash = hash_password(u["password"])
            execute_query(
                """
                INSERT INTO users (user_id, username, name, role, department, avatar_color, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
                """,
                (u["user_id"], u["username"], u["name"], u["role"], u["department"], u["avatar_color"], pwd_hash),
                commit=True
            )
    except Exception as e:
        logging.error(f"Error seeding RBAC default accounts in PostgreSQL: {e}")


def authenticate_user(username: str, password: str, db_path: Any = None) -> Optional[Dict[str, Any]]:
    """Authenticates username and password against PostgreSQL database."""
    init_rbac_db()
    try:
        row = execute_query(
            "SELECT user_id, username, name, role, department, avatar_color, password_hash, totp_enabled FROM users WHERE username = %s",
            (username,),
            fetch_one=True
        )

        if not row:
            return None

        uid, uname, name, role, dept, avatar, pwd_hash, totp_enabled = row
        if verify_password(password, pwd_hash or ""):
            return {
                "user_id": uid,
                "username": uname,
                "name": name,
                "role": role,
                "department": dept,
                "avatar_color": avatar,
                "totp_enabled": bool(totp_enabled) if totp_enabled is not None else False
            }
        return None
    except Exception as e:
        logging.error(f"Error authenticating user '{username}': {e}")
        return None


def get_all_users(db_path: Any = None) -> List[Dict[str, Any]]:
    """Returns list of registered users with thread counts from PostgreSQL."""
    init_rbac_db()
    try:
        rows = execute_query(
            "SELECT user_id, username, name, role, department, avatar_color, created_at, totp_enabled FROM users",
            fetch_all=True
        ) or []

        users = []
        for r in rows:
            uid = r[0]
            t_cnt_res = execute_query(
                "SELECT COUNT(*) FROM threads WHERE user_id = %s",
                (uid,),
                fetch_one=True
            )
            t_cnt = t_cnt_res[0] if t_cnt_res else 0
            users.append({
                "user_id": uid,
                "username": r[1],
                "name": r[2],
                "role": r[3],
                "department": r[4],
                "avatar_color": r[5],
                "created_at": str(r[6]) if r[6] else None,
                "totp_enabled": bool(r[7]) if len(r) > 7 and r[7] is not None else False,
                "thread_count": t_cnt
            })
        return users
    except Exception as e:
        logging.error(f"Error getting users: {e}")
        return DEFAULT_USERS


def get_user_by_id(user_id: str, db_path: Any = None) -> Optional[Dict[str, Any]]:
    """Fetches a user profile by user_id."""
    users = get_all_users(db_path)
    for u in users:
        if u["user_id"] == user_id:
            return u
    return None


def create_new_user(
    username: str,
    password: str,
    name: str,
    role: str = "user",
    department: str = "General Engineering",
    avatar_color: str = "bg-blue-500",
    db_path: Any = None
) -> Dict[str, Any]:
    """Creates a new user account (Admin functionality)."""
    user_id = username.lower().strip()
    pwd_hash = hash_password(password)

    execute_query(
        """
        INSERT INTO users (user_id, username, name, role, department, avatar_color, password_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (user_id, username, name, role, department, avatar_color, pwd_hash),
        commit=True
    )
    return {
        "user_id": user_id,
        "username": username,
        "name": name,
        "role": role,
        "department": department,
        "avatar_color": avatar_color,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }


def change_user_password(user_id: str, old_password: str, new_password: str, db_path: Any = None) -> bool:
    """Verifies old password and updates user password hash in PostgreSQL database."""
    row = execute_query(
        "SELECT password_hash FROM users WHERE user_id = %s",
        (user_id,),
        fetch_one=True
    )

    if not row:
        raise ValueError("User account not found")

    pwd_hash = row[0]
    if not verify_password(old_password, pwd_hash or ""):
        raise ValueError("Incorrect current password")

    new_hash = hash_password(new_password)
    execute_query(
        "UPDATE users SET password_hash = %s WHERE user_id = %s",
        (new_hash, user_id),
        commit=True
    )
    return True


def delete_user_account(user_id: str) -> bool:
    """Deletes a user account and associated threads/files from PostgreSQL database."""
    if user_id.lower() == "admin":
        raise ValueError("System Administrator account 'admin' cannot be deleted")

    user = get_user_by_id(user_id)
    if not user:
        raise ValueError(f"User account '{user_id}' not found")

    # Fetch and delete user threads
    threads = execute_query("SELECT thread_id FROM threads WHERE user_id = %s", (user_id,), fetch_all=True) or []
    for t in threads:
        tid = t[0]
        execute_query("DELETE FROM checkpoints WHERE thread_id = %s", (tid,), commit=True)
        execute_query("DELETE FROM checkpoint_writes WHERE thread_id = %s", (tid,), commit=True)
        execute_query("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (tid,), commit=True)
        execute_query("DELETE FROM messages WHERE thread_id = %s", (tid,), commit=True)
        execute_query("DELETE FROM file_metadata WHERE thread_id = %s", (tid,), commit=True)
        execute_query("DELETE FROM threads WHERE thread_id = %s", (tid,), commit=True)

    # Delete user record
    execute_query("DELETE FROM users WHERE user_id = %s", (user_id,), commit=True)
    return True


def link_thread_to_user(thread_id: str, user_id: str, db_path: Any = None):
    """Links a thread_id to a specific user_id in threads table."""
    try:
        execute_query(
            """
            INSERT INTO threads (thread_id, user_id, title)
            VALUES (%s, %s, 'New Conversation')
            ON CONFLICT (thread_id) DO UPDATE SET user_id = EXCLUDED.user_id
            """,
            (thread_id, user_id),
            commit=True
        )
    except Exception as e:
        logging.error(f"Error linking thread '{thread_id}' to user '{user_id}': {e}")


def update_thread_title(thread_id: str, title: str, only_if_default: bool = True):
    """Updates title of thread in PostgreSQL threads table."""
    try:
        clean_title = title.strip()[:60] if title else "New Conversation"
        if only_if_default:
            execute_query(
                """
                UPDATE threads 
                SET title = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE thread_id = %s AND (title IS NULL OR title = '' OR title = 'New Conversation')
                """,
                (clean_title, thread_id),
                commit=True
            )
        else:
            execute_query(
                "UPDATE threads SET title = %s, updated_at = CURRENT_TIMESTAMP WHERE thread_id = %s",
                (clean_title, thread_id),
                commit=True
            )
    except Exception as e:
        logging.error(f"Error updating title for thread '{thread_id}': {e}")


def get_thread_user_map(db_path: Any = None) -> Dict[str, str]:
    """Returns mapping of thread_id -> user_id."""
    try:
        rows = execute_query("SELECT thread_id, user_id FROM threads", fetch_all=True) or []
        return {r[0]: r[1] for r in rows}
    except Exception as e:
        logging.error(f"Error getting thread_user map: {e}")
        return {}


def get_admin_audit_metrics(db_path: Any = None) -> Dict[str, Any]:
    """Returns comprehensive system metrics for Admin Panel view."""
    users = get_all_users(db_path)

    workspace_dir = Path("workspace")
    total_bytes = 0
    total_files = 0
    if workspace_dir.exists():
        for f in workspace_dir.rglob("*"):
            if f.is_file():
                total_bytes += f.stat().st_size
                total_files += 1

    storage_mb = round(total_bytes / (1024 * 1024), 2)

    kb_doc_count = 0
    kb_chunk_count = 0
    try:
        from tools.rag_kb import get_reference_files
        files = get_reference_files()
        kb_doc_count = len(files)
        kb_chunk_count = sum(f.get("chunk_count", 0) for f in files)
    except Exception:
        pass

    return {
        "total_users": len(users),
        "total_threads": sum(u.get("thread_count", 0) for u in users),
        "workspace_storage_mb": storage_mb,
        "workspace_files_count": total_files,
        "rag_kb_documents": kb_doc_count,
        "rag_kb_chunks": kb_chunk_count,
        "users": users
    }
