"""
Quantum Authentication Research Dashboard
Flask backend — simulation APIs + QEAP-256 auth endpoints
"""

import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, render_template, jsonify, request

import jwt as pyjwt

from quantum.engine import (
    simulate_bell_auth, simulate_chsh, simulate_bb84,
    simulate_comparison, QISKIT_AVAILABLE
)
from auth.qeap import register_quantum_identity, verify_quantum_identity
from auth.db   import (
    create_user, get_user_by_username, get_user_by_email,
    verify_password, record_login, get_all_users,
    get_user_count, get_audit_log, check_connection,
    MONGO_AVAILABLE
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "qeap256-dev-secret-change-in-prod")

QEAP_SERVER_SECRET = os.environ.get("QEAP_SECRET", "qeap256-server-key-university-of-mumbai")
JWT_SECRET  = os.environ.get("JWT_SECRET", "jwt-qeap256-secret")
JWT_EXPIRY  = int(os.environ.get("JWT_EXPIRY_HOURS", 24))

EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


def _make_jwt(username, full_name):
    payload = {
        "sub" : username,
        "name": full_name,
        "iat" : datetime.now(timezone.utc),
        "exp" : datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY),
        "alg" : "QEAP-256",
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _decode_jwt(token):
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None


def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth  = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
        elif "token" in request.cookies:
            token = request.cookies.get("token")
        if not token:
            return jsonify({"ok": False, "error": "Authentication required"}), 401
        payload = _decode_jwt(token)
        if not payload:
            return jsonify({"ok": False, "error": "Invalid or expired token"}), 401
        request.current_user = payload
        return f(*args, **kwargs)
    return decorated


# ── Pages ────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html", qiskit=QISKIT_AVAILABLE)

@app.route("/login")
def login_page():
    return render_template("login.html", qiskit=QISKIT_AVAILABLE)

@app.route("/register")
def register_page():
    return render_template("register.html", qiskit=QISKIT_AVAILABLE)

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html", qiskit=QISKIT_AVAILABLE)


# ── Auth status ──────────────────────────────────────────
@app.route("/api/auth/status")
def api_auth_status():
    db_status = check_connection()
    return jsonify({
        "mongo_available" : MONGO_AVAILABLE,
        "mongo_connected" : db_status["ok"],
        "mongo_info"      : db_status,
        "qiskit_available": QISKIT_AVAILABLE,
        "engine"          : "Qiskit" if QISKIT_AVAILABLE else "NumPy Simulator",
        "algorithm"       : "QEAP-256",
        "user_count"      : get_user_count() if db_status["ok"] else 0,
    })


# ── Register ─────────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}
    username  = (data.get("username") or "").strip()
    email     = (data.get("email") or "").strip()
    password  = (data.get("password") or "").strip()
    full_name = (data.get("full_name") or "").strip()

    errors = {}
    if len(username) < 3:
        errors["username"] = "At least 3 characters"
    if username and not re.match(r"^[a-zA-Z0-9_\-]+$", username):
        errors["username"] = "Letters, numbers, _ and - only"
    if not email or not EMAIL_RE.match(email):
        errors["email"] = "Valid email required"
    if len(password) < 6:
        errors["password"] = "At least 6 characters"
    if not full_name:
        errors["full_name"] = "Full name required"
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    if get_user_by_username(username):
        return jsonify({"ok": False, "errors": {"username": "Username already taken"}}), 409
    if get_user_by_email(email):
        return jsonify({"ok": False, "errors": {"email": "Email already registered"}}), 409

    qi = register_quantum_identity(username, QEAP_SERVER_SECRET)
    result = create_user(username, email, password, full_name, qi)
    if not result["ok"]:
        return jsonify({"ok": False, "error": result["error"]}), 500

    token = _make_jwt(username, full_name)
    return jsonify({
        "ok"     : True,
        "message": "Quantum identity created successfully",
        "token"  : token,
        "user"   : {"username": username, "full_name": full_name, "email": email},
        "quantum": {
            "algorithm"       : qi["algorithm"],
            "qiv_hex"         : qi["qiv_hex"],
            "chsh_fingerprint": qi["chsh_fingerprint"],
            "fidelity"        : qi["fidelity"],
            "n_pairs"         : qi["n_pairs"],
            "engine"          : qi["engine"],
            "elapsed_ms"      : qi["elapsed_ms"],
        }
    }), 201
  

# ── Login ────────────────────────────────────────────────
@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data       = request.get_json(silent=True) or {}
    identifier = (data.get("username") or data.get("email") or "").strip()
    password   = (data.get("password") or "").strip()
    ip         = request.remote_addr or ""

    if not identifier or not password:
        return jsonify({"ok": False, "error": "Credentials required"}), 400

    user = get_user_by_username(identifier) or get_user_by_email(identifier)
    if not user:
        record_login(identifier, False, ip)
        return jsonify({"ok": False, "error": "Invalid credentials"}), 401

    if not user.get("is_active"):
        return jsonify({"ok": False, "error": "Account disabled"}), 403

    if not verify_password(user["password_hash"], password):
        record_login(user["username"], False, ip)
        return jsonify({"ok": False, "error": "Invalid credentials"}), 401

    qv = verify_quantum_identity(
        username        = user["username"],
        server_secret   = QEAP_SERVER_SECRET,
        stored_qiv_hex  = user["quantum_identity"]["qiv_hex"],
        stored_chsh     = user["quantum_identity"]["chsh_fingerprint"],
        stored_qiv_hash = user["quantum_identity"]["qiv_hash"],
    )

    if not qv["verified"]:
        record_login(user["username"], False, ip)
        return jsonify({"ok": False, "error": f"Quantum verification failed: {qv['reason']}", "quantum": qv}), 401

    record_login(user["username"], True, ip)
    token = _make_jwt(user["username"], user["full_name"])
    return jsonify({
        "ok"     : True,
        "message": "Authentication successful",
        "token"  : token,
        "user"   : {
            "username"   : user["username"],
            "full_name"  : user["full_name"],
            "email"      : user["email"],
            "login_count": user.get("login_count", 0) + 1,
            "last_login" : user["last_login"].isoformat() if user.get("last_login") else None,
        },
        "quantum": {
            "algorithm" : qv["algorithm"],
            "chsh_score": qv["chsh_score"],
            "fidelity"  : qv["fidelity"],
            # "qiv_match" : qv["qiv_match"],
            "chsh_pass" : qv["chsh_pass"],
            "steps"     : qv["steps"],
            "elapsed_ms": qv["elapsed_ms"],
            "engine"    : qv["engine"],
        }
    })


@app.route("/api/auth/me")
@jwt_required
def api_me():
    user = get_user_by_username(request.current_user["sub"])
    if not user:
        return jsonify({"ok": False, "error": "User not found"}), 404
    return jsonify({
        "ok"  : True,
        "user": {
            "username"        : user["username"],
            "full_name"       : user["full_name"],
            "email"           : user["email"],
            "algorithm"       : user.get("algorithm", "QEAP-256"),
            "qiv_hex"         : user["quantum_identity"]["qiv_hex"],
            "chsh_fingerprint": user["quantum_identity"]["chsh_fingerprint"],
            "fidelity"        : user["quantum_identity"]["fidelity"],
            "n_pairs"         : user.get("n_pairs"),
            "quantum_engine"  : user.get("quantum_engine"),
            "login_count"     : user.get("login_count", 0),
            "created_at"      : user["created_at"].isoformat() if user.get("created_at") else None,
            "last_login"      : user["last_login"].isoformat() if user.get("last_login") else None,
        }
    })


@app.route("/api/auth/audit")
@jwt_required
def api_audit():
    logs = get_audit_log(username=request.current_user["sub"], limit=30)
    return jsonify({"ok": True, "logs": logs})


@app.route("/api/auth/users")
@jwt_required
def api_users():
    users = get_all_users(limit=50)
    return jsonify({"ok": True, "users": users, "count": len(users)})


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    return jsonify({"ok": True, "message": "Logged out"})


# ── Simulation APIs (unchanged) ──────────────────────────
@app.route("/api/status")
def api_status():
    return jsonify({
        "qiskit_available": QISKIT_AVAILABLE,
        "engine": "Qiskit" if QISKIT_AVAILABLE else "NumPy Quantum Simulator",
        "papers": [
            {"id":1,"title":"From Passwords to Qubits","journal":"IJESE 2025"},
            {"id":2,"title":"Entangled Qubits and PQC", "journal":"IJIRT 2026"},
            {"id":3,"title":"Zero-Trust Quantum Auth",  "journal":"IJCA 2025"},
        ]
    })

@app.route("/api/simulate/bell", methods=["POST"])
def api_bell():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify({"ok":True,"data":simulate_bell_auth(
            min(int(data.get("n_trials",40)),100), bool(data.get("eavesdrop",False)))})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}), 500

@app.route("/api/simulate/chsh", methods=["POST"])
def api_chsh():
    data = request.get_json(silent=True) or {}
    sc = data.get("scenario","normal")
    if sc not in ("normal","eavesdrop","malicious_device","high_noise"): sc="normal"
    try:
        return jsonify({"ok":True,"data":simulate_chsh(min(int(data.get("n_rounds",50)),100), sc)})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}), 500

@app.route("/api/simulate/bb84", methods=["POST"])
def api_bb84():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify({"ok":True,"data":simulate_bb84(
            min(int(data.get("n_bits",100)),300),
            max(0.0,min(1.0,float(data.get("eavesdrop_rate",0.0)))))})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}), 500

@app.route("/api/simulate/compare", methods=["POST"])
def api_compare():
    try:
        return jsonify({"ok":True,"data":simulate_comparison()})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}), 500


if __name__ == "__main__":
    db_info = check_connection()
    print("\n" + "═"*60)
    print("  QEAP-256 Quantum Authentication Platform")
    print(f"  Engine  : {'Qiskit' if QISKIT_AVAILABLE else 'NumPy Quantum Simulator'}")
    print(f"  MongoDB : {'✓ ' + db_info.get('version','') if db_info['ok'] else '✗ ' + db_info.get('error','')}")
    print(f"  URL     : http://127.0.0.1:5000")
    print("═"*60 + "\n")
    app.run(debug=True, port=5000)