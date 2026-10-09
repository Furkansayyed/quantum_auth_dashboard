"""
Database layer — MongoDB via PyMongo
Handles all user CRUD operations for QEAP-256 authentication.
"""

from datetime import datetime, timezone
import os
QEAP_SERVER_SECRET = os.environ.get("QEAP_SECRET", "qeap256-server-key-university-of-mumbai")
try:
    from pymongo import MongoClient, ASCENDING
    from pymongo.errors import DuplicateKeyError, ConnectionFailure
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    DuplicateKeyError = Exception  # placeholder

from werkzeug.security import generate_password_hash, check_password_hash

# ─────────────────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────────────────

MONGO_URI  = os.environ.get("MONGO_URI",  "mongodb://localhost:27017/")
DB_NAME    = os.environ.get("MONGO_DB",   "quantum_auth")
COLL_USERS = "users"
COLL_SESSIONS = "sessions"
COLL_AUDIT = "audit_log"


# ─────────────────────────────────────────────────────────
#  Connection
# ─────────────────────────────────────────────────────────

_client = None
_db     = None

def get_db():
    global _client, _db
    if _db is not None:
        return _db
    if not MONGO_AVAILABLE:
        raise RuntimeError("pymongo not installed — run: pip install pymongo")
    _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    _client.admin.command("ping")   # raises ConnectionFailure if down
    _db = _client[DB_NAME]
    _ensure_indexes()
    return _db


def _ensure_indexes():
    """Create indexes on first connection."""
    db = _client[DB_NAME]
    db[COLL_USERS].create_index([("username", ASCENDING)], unique=True)
    db[COLL_USERS].create_index([("email", ASCENDING)], unique=True)
    db[COLL_AUDIT].create_index([("username", ASCENDING)])
    db[COLL_AUDIT].create_index([("timestamp", ASCENDING)])


def check_connection() -> dict:
    """Return connection status for health-check endpoint."""
    if not MONGO_AVAILABLE:
        return {"ok": False, "error": "pymongo not installed", "db": None}
    try:
        db = get_db()
        info = db.client.server_info()
        return {
            "ok": True,
            "version": info.get("version", "?"),
            "db": DB_NAME,
            "uri": MONGO_URI.split("@")[-1]  # hide credentials
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "db": DB_NAME}


# ─────────────────────────────────────────────────────────
#  User operations
# ─────────────────────────────────────────────────────────

# def create_user(username: str, email: str, password: str,
#                 full_name: str, quantum_identity: dict) -> dict:
#     """
#     Insert a new user with QEAP-256 quantum identity.
#     Returns {"ok": True, "user_id": str} or {"ok": False, "error": str}
#     """
#     try:
#         db = get_db()
#         now = datetime.now(timezone.utc)
#         doc = {
#             "username"         : username.lower().strip(),
#             "email"            : email.lower().strip(),
#             "full_name"        : full_name.strip(),
#             "password_hash"    : generate_password_hash(password),
#             # QEAP-256 quantum identity fields
#             "algorithm"        : quantum_identity["algorithm"],
#             "quantum_seed"     : quantum_identity["quantum_seed"],
#             "basis_string"     : quantum_identity["basis_string"],
#             "qiv_hex"          : quantum_identity["qiv_hex"],
#             "chsh_fingerprint" : quantum_identity["chsh_fingerprint"],
#             "fidelity"         : quantum_identity["fidelity"],
#             "qiv_hash"         : quantum_identity["qiv_hash"],
#             "n_pairs"          : quantum_identity["n_pairs"],
#             "quantum_engine"   : quantum_identity["engine"],
#             # Meta
#             "created_at"       : now,
#             "updated_at"       : now,
#             "login_count"      : 0,
#             "last_login"       : None,
#             "is_active"        : True,
#         }
#         result = db[COLL_USERS].insert_one(doc)
#         _audit(username, "REGISTER", True, f"QEAP-256 identity created, CHSH={quantum_identity['chsh_fingerprint']}")
#         return {"ok": True, "user_id": str(result.inserted_id)}
#     except DuplicateKeyError as e:
#         field = "username" if "username" in str(e) else "email"
#         return {"ok": False, "error": f"That {field} is already registered"}
#     except Exception as e:
#         return {"ok": False, "error": str(e)}
def create_user(username: str, email: str, password: str,
                full_name: str, quantum_identity: dict) -> dict:

    try:
        db = get_db()
        now = datetime.now(timezone.utc)

        # Validate quantum fields
        required_fields = [
            "algorithm", "quantum_seed", "basis_string",
            "qiv_hex", "chsh_fingerprint", "fidelity",
            "qiv_hash", "n_pairs", "engine"
        ]

        for field in required_fields:
            if field not in quantum_identity:
                return {"ok": False, "error": f"Missing field: {field}"}

        if not (0 <= quantum_identity["fidelity"] <= 1):
            return {"ok": False, "error": "Invalid fidelity"}

        # Hash sensitive quantum data
        from hashlib import sha256
        quantum_seed_hash = sha256(
    str(quantum_identity["quantum_seed"]).encode()).hexdigest()

        doc = {
            "username": username.lower().strip(),
            "email": email.lower().strip(),
            "full_name": full_name.strip(),
            "password_hash": generate_password_hash(password),

            "quantum_identity": {
                "algorithm": quantum_identity["algorithm"],
                "basis_string": quantum_identity["basis_string"],
                "qiv_hex": quantum_identity["qiv_hex"],
                "chsh_fingerprint": quantum_identity["chsh_fingerprint"],
                "fidelity": quantum_identity["fidelity"],
                "qiv_hash": quantum_identity["qiv_hash"],
                "n_pairs": quantum_identity["n_pairs"],
                "engine": quantum_identity["engine"],
                "quantum_seed_hash": quantum_seed_hash
            },

            "created_at": now,
            "updated_at": now,
            "login_count": 0,
            "last_login": None,
            "is_active": True,
        }

        result = db[COLL_USERS].insert_one(doc)

        _audit(username, "REGISTER", True,
               f"QEAP identity created, CHSH={quantum_identity['chsh_fingerprint']}")

        return {"ok": True, "user_id": str(result.inserted_id)}

    except DuplicateKeyError as e:
        field = "username" if "username" in str(e) else "email"
        return {"ok": False, "error": f"{field} already exists"}

    except Exception as e:
        return {"ok": False, "error": str(e)}

def get_user_by_username(username: str) -> dict | None:
    """Return the user document or None."""
    try:
        db = get_db()
        return db[COLL_USERS].find_one({"username": username.lower().strip()})
    except Exception:
        return None


def get_user_by_email(email: str) -> dict | None:
    try:
        db = get_db()
        return db[COLL_USERS].find_one({"email": email.lower().strip()})
    except Exception:
        return None


def verify_password(stored_hash: str, password: str) -> bool:
    return check_password_hash(stored_hash, password)


def record_login(username: str, success: bool, ip: str = ""):
    """Update last_login and login_count after a successful login."""
    try:
        db = get_db()
        if success:
            db[COLL_USERS].update_one(
                {"username": username.lower()},
                {"$set":  {"last_login": datetime.now(timezone.utc)},
                 "$inc":  {"login_count": 1}}
            )
        _audit(username, "LOGIN", success, f"ip={ip}")
    except Exception:
        pass


def get_all_users(limit: int = 100) -> list:
    """Return list of users (sans sensitive fields) for admin view."""
    try:
        db = get_db()
        cursor = db[COLL_USERS].find(
            {},
            {"password_hash": 0, "qiv_hash": 0, "quantum_seed": 0}
        ).sort("created_at", -1).limit(limit)
        users = []
        for u in cursor:
            u["_id"] = str(u["_id"])
            if u.get("created_at"):
                u["created_at"] = u["created_at"].isoformat()
            if u.get("last_login"):
                u["last_login"] = u["last_login"].isoformat()
            users.append(u)
        return users
    except Exception:
        return []


def get_user_count() -> int:
    try:
        return get_db()[COLL_USERS].count_documents({})
    except Exception:
        return 0


def get_audit_log(username: str = None, limit: int = 20) -> list:
    try:
        db = get_db()
        q = {"username": username.lower()} if username else {}
        cursor = db[COLL_AUDIT].find(q).sort("timestamp", -1).limit(limit)
        logs = []
        for l in cursor:
            l["_id"] = str(l["_id"])
            if l.get("timestamp"):
                l["timestamp"] = l["timestamp"].isoformat()
            logs.append(l)
        return logs
    except Exception:
        return []


# ─────────────────────────────────────────────────────────
#  Audit log
# ─────────────────────────────────────────────────────────

def _audit(username: str, action: str, success: bool, detail: str = ""):
    try:
        db = get_db()
        db[COLL_AUDIT].insert_one({
            "username" : username.lower(),
            "action"   : action,
            "success"  : success,
            "detail"   : detail,
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception:
        pass
