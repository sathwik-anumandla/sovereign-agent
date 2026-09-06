"""
tools/rbac.py (SIH PS 26117)
============================
User Roles, Multi-User Isolation, RBAC Management, and Air-Gapped JWT Authentication.
Provides zero-dependency PBKDF2 password hashing and HMAC-SHA256 JWT token verification.
"""

import sqlite3
import time
import json
import hmac
import base64
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path("workbench_checkpoints.db")
SECRET_KEY = "sovereign_agent_air_gapped_jwt_secret_key_2026"
SALT = "sovereign_pbkdf2_salt_airgap"


def hash_password(password: str) -> str:
    """Hashes a plain text password using PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), SALT.encode("utf-8"), 100000).hex()


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a plain text password against stored hash."""
    return hmac.compare_digest(hash_password(password), stored_hash)


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

        # Add padding back if necessary
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


def init_rbac_db(db_path: Path = DB_PATH):
    """Initializes sqlite RBAC tables (users, thread_users) and seeds default accounts with passwords."""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 1. Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT,
                avatar_color TEXT,
                password_hash TEXT,
                created_at TEXT
            )
        """)

        # Migration check: Ensure password_hash column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        if "password_hash" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")

        # 2. Thread ownership table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS thread_users (
                thread_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # Seed default users if table is empty or missing password_hash
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        for u in DEFAULT_USERS:
            pwd_hash = hash_password(u["password"])
            cursor.execute(
                """
                INSERT INTO users (user_id, username, name, role, department, avatar_color, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET password_hash=excluded.password_hash
                """,
                (u["user_id"], u["username"], u["name"], u["role"], u["department"], u["avatar_color"], pwd_hash, now_str)
            )
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error initializing RBAC SQLite tables: {e}")


def authenticate_user(username: str, password: str, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    """Authenticates username and password against SQLite database."""
    init_rbac_db(db_path)
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, name, role, department, avatar_color, password_hash FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        uid, uname, name, role, dept, avatar, pwd_hash = row
        if verify_password(password, pwd_hash or ""):
            return {
                "user_id": uid,
                "username": uname,
                "name": name,
                "role": role,
                "department": dept,
                "avatar_color": avatar
            }
        return None
    except Exception as e:
        logging.error(f"Error authenticating user '{username}': {e}")
        return None


def get_all_users(db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """Returns list of registered users with thread counts."""
    init_rbac_db(db_path)
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT user_id, username, name, role, department, avatar_color, created_at FROM users")
        rows = cursor.fetchall()

        users = []
        for r in rows:
            uid = r[0]
            cursor.execute("SELECT COUNT(*) FROM thread_users WHERE user_id = ?", (uid,))
            t_cnt = cursor.fetchone()[0]
            users.append({
                "user_id": uid,
                "username": r[1],
                "name": r[2],
                "role": r[3],
                "department": r[4],
                "avatar_color": r[5],
                "created_at": r[6],
                "thread_count": t_cnt
            })
        conn.close()
        return users
    except Exception as e:
        logging.error(f"Error getting users: {e}")
        return DEFAULT_USERS


def get_user_by_id(user_id: str, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
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
    db_path: Path = DB_PATH
) -> Dict[str, Any]:
    """Creates a new user account (Admin functionality)."""
    init_rbac_db(db_path)
    user_id = username.lower().strip()
    pwd_hash = hash_password(password)
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (user_id, username, name, role, department, avatar_color, password_hash, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, username, name, role, department, avatar_color, pwd_hash, now_str)
    )
    conn.commit()
    conn.close()
    return {
        "user_id": user_id,
        "username": username,
        "name": name,
        "role": role,
        "department": department,
        "avatar_color": avatar_color,
        "created_at": now_str
    }


def change_user_password(user_id: str, old_password: str, new_password: str, db_path: Path = DB_PATH) -> bool:
    """Verifies old password and updates user password hash in SQLite database."""
    init_rbac_db(db_path)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise ValueError("User account not found")

    pwd_hash = row[0]
    if not verify_password(old_password, pwd_hash or ""):
        conn.close()
        raise ValueError("Incorrect current password")

    new_hash = hash_password(new_password)
    cursor.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (new_hash, user_id))
    conn.commit()
    conn.close()
    return True



def link_thread_to_user(thread_id: str, user_id: str, db_path: Path = DB_PATH):
    """Links a thread_id to a specific user_id."""
    init_rbac_db(db_path)
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT OR REPLACE INTO thread_users (thread_id, user_id, created_at) VALUES (?, ?, ?)",
            (thread_id, user_id, now_str)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error linking thread '{thread_id}' to user '{user_id}': {e}")


def get_thread_user_map(db_path: Path = DB_PATH) -> Dict[str, str]:
    """Returns mapping of thread_id -> user_id."""
    init_rbac_db(db_path)
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT thread_id, user_id FROM thread_users")
        rows = cursor.fetchall()
        conn.close()
        return {r[0]: r[1] for r in rows}
    except Exception as e:
        logging.error(f"Error getting thread_user map: {e}")
        return {}


def get_admin_audit_metrics(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """Returns comprehensive system metrics for Admin Panel view."""
    init_rbac_db(db_path)
    users = get_all_users(db_path)

    workspace_dir = Path("workspaces")
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
