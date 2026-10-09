# ✨ QEAP-256 Quantum Authentication Platform

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Local%20%26%20Docker-4EA94B?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Quantum](https://img.shields.io/badge/Quantum-Simulation%20Engine-8A2BE2)](https://qiskit.org/)

</div>

**Authors:** Furkan Sayyed, Srivaramangai Ramanujam  
**Affiliation:** Dept. of Information Technology, University of Mumbai

A full-stack research platform for quantum-secured authentication using the **QEAP-256** protocol, backed by MongoDB and a live simulation dashboard that connects directly to peer-reviewed publication work.

---

## 🚀 Overview

QEAP-256 is a hybrid quantum-classical authentication model that blends:

- deterministic key derivation using `HMAC-SHA256`
- Bell-pair identity generation
- CHSH-based entanglement validation
- PBKDF2 password verification
- MongoDB-backed audit logging and user tracking

This project turns that protocol into a working Flask application with a browser-based dashboard, registration/login flows, and research-grade simulation views.

### Key Highlights

- 🔐 Quantum-aware authentication flow
- 🧪 Live Bell / CHSH / BB84 simulations
- 📊 Research dashboard with comparative analysis
- 🗄️ MongoDB persistence for users and audit logs
- 🧠 Qiskit-ready backend with NumPy fallback
- 🔑 JWT-based session handling and user profiles

---

## 📚 Published Papers

| # | Title | Journal |
|---|-------|---------|
| 1 | From Passwords to Qubits: Harnessing Entanglement for Next-Generation Authentication | IJESE, Apr 2025 |
| 2 | Entangled Qubits and PQC: A Simulated Performance Analysis | IJIRT, Jan 2026 |
| 3 | Zero-Trust Quantum Authentication for Distributed Systems | IJCA, Jun 2025 |

---

## 🧬 QEAP-256 Algorithm

**QEAP-256** (Quantum Entanglement Authentication Protocol, 256-symbol space) is a hybrid quantum-classical authentication protocol invented by the authors.

### Registration flow

1. Server derives a deterministic seed from `HMAC-SHA256(server_secret, username)`
2. Seed prepares **8 entangled Bell pairs** (16 qubits) in state `|Φ+⟩ = 1/√2(|00⟩ + |11⟩)`
3. Each pair is measured in a randomly-seeded basis (`Z` or `X`)
4. The 16-bit result becomes the user's **Quantum Identity Vector (QIV)**
5. A **CHSH fingerprint** (S-score) is computed and stored alongside the QIV
6. The record is stored in MongoDB as:

```json
{
  "username": "furkan556",
  "password_hash": "pbkdf2:sha256:...",
  "qiv_hex": "A3F1...",
  "chsh_fingerprint": 2.7841,
  "qiv_hash": "sha256:..."
}
```

### Login flow

1. Classical password check using PBKDF2-SHA256 via Werkzeug
2. Re-derive the seed from `HMAC-SHA256(server_secret, username)`
3. Re-run the Bell circuit and reconstruct the QIV
4. Verify:
   - QIV match
   - CHSH `S > 2.0`
   - integrity hash
5. If all checks pass, issue a JWT

### Security properties

- **No-cloning theorem:** the QIV cannot be copied or forged
- **CHSH guard:** `S <= 2.0` indicates a classical or tampered state and triggers rejection
- **Deterministic re-derivation:** only the server secret can regenerate the correct QIV
- **Hybrid security:** password hash + QIV + CHSH = 3 independent verification layers
- **Audit trail:** login and registration attempts are recorded in MongoDB

---

## ⚡ Quick Start

### Prerequisites

- Python 3.10+
- MongoDB running locally on port `27017`

### 1) Install dependencies

```bash
pip install flask numpy PyJWT Werkzeug pymongo
```

### 2) Optional: install Qiskit for real quantum simulation

```bash
pip install qiskit qiskit-aer
```

When Qiskit is installed, the engine badge shows **Qiskit Backend** and simulations run on the real `AerSimulator`. Without it, a faithful NumPy implementation is used.

### 3) Start MongoDB

```bash
# macOS
brew services start mongodb-community

# Ubuntu/Debian
sudo systemctl start mongod

# Windows
net start MongoDB

# Or use Docker
docker run -d -p 27017:27017 --name mongo mongo:7
```

### 4) Run the app

```bash
cd quantum_auth_dashboard
python app.py
```

Open: **http://127.0.0.1:5000**

---

## 🏗️ Project Structure

```text
quantum_auth_dashboard/
├── app.py                       # Flask app — auth + simulation routes
├── auth/
│   ├── qeap.py                  # QEAP-256 algorithm (register + verify)
│   ├── db.py                    # MongoDB layer (users, sessions, audit log)
│   └── __init__.py
├── quantum/
│   └── engine.py                # Quantum simulation engine (Bell / CHSH / BB84)
│                                # Uses Qiskit if installed, NumPy fallback
├── templates/
│   ├── index.html               # Research dashboard (5 simulation panels)
│   ├── login.html               # Login page with QEAP-256 step trace
│   ├── register.html            # Registration page with Bell-pair visualizer
│   └── dashboard.html           # User profile + QIV display + community
├── requirements.txt
├── README.md
└── .env.example                 # Optional local env configuration
```

---

## 🌐 Pages & Routes

| Route | Description |
|-------|-------------|
| `GET /` | Research simulation dashboard |
| `GET /login` | Login page |
| `GET /register` | Registration page with quantum identity animation |
| `GET /dashboard` | Post-login user dashboard (requires JWT) |

## 🔌 API Endpoints

### Authentication

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/api/auth/status` | Engine + MongoDB status |
| `POST` | `/api/auth/register` | Register a new user and run QEAP-256 registration |
| `POST` | `/api/auth/login` | Validate password + QEAP-256 verification |
| `GET` | `/api/auth/me` | Current user profile (JWT required) |
| `GET` | `/api/auth/audit` | User audit log (JWT required) |
| `GET` | `/api/auth/users` | All platform users (JWT required) |
| `POST` | `/api/auth/logout` | Logout (client discards JWT) |

### Simulations

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/simulate/bell` | Bell-state authentication simulation |
| `POST` | `/api/simulate/chsh` | CHSH inequality test |
| `POST` | `/api/simulate/bb84` | BB84 QKD protocol simulation |
| `POST` | `/api/simulate/compare` | Compare all scenarios |

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QEAP_SECRET` | `qeap256-server-key-...` | Server secret for QEAP-256 seed derivation |
| `JWT_SECRET` | `jwt-qeap256-secret` | JWT signing key |
| `JWT_EXPIRY_HOURS` | `24` | JWT expiry in hours |
| `FLASK_SECRET` | `qeap256-dev-secret` | Flask session secret |
| `MONGO_URI` | `mongodb://localhost:27017/` | MongoDB connection URI |
| `MONGO_DB` | `quantum_auth` | MongoDB database name |

> For production, always set strong secrets via environment variables.

---

## 🗄️ MongoDB Collections

| Collection | Purpose |
|------------|---------|
| `users` | User accounts with QEAP-256 quantum identity fields |
| `audit_log` | Login/register events with timestamps |

### User document schema

```json
{
  "username": "furkan556",
  "email": "furkan@example.com",
  "full_name": "Furkan Sayyed",
  "password_hash": "pbkdf2:sha256:...",
  "algorithm": "QEAP-256",
  "quantum_seed": 12345678,
  "basis_string": "ZXZXZXZX",
  "qiv_hex": "A3F1...",
  "chsh_fingerprint": 2.7841,
  "fidelity": 0.875,
  "qiv_hash": "sha256...",
  "n_pairs": 8,
  "quantum_engine": "NumPy",
  "login_count": 5,
  "last_login": "2025-04-17T10:30:00Z",
  "created_at": "2025-01-15T08:00:00Z",
  "is_active": true
}
```

---

## 🧾 Citation

If you use this platform or QEAP-256 in your work, please cite:

```text
Sayyed, F., & Ramanujam, S. (2025). From Passwords to Qubits: Harnessing Entanglement
for Next-Generation Authentication. IJESE, 13(5). DOI: 10.35940/ijese.D2593.13050425

Sayyed, F., & Ramanujam, S. (2026). Entangled Qubits and PQC: A Simulated Performance
Analysis for Post-Quantum Authentication. IJIRT, 12(8).

Sayyed, F., & Ramanujam, S. (2025). Zero-Trust Quantum Authentication for Distributed
Systems Using Device-Independent Protocols. IJCA, 187(20).
```

---

<p align="center">
  <strong>Built for research, simulation, and secure authentication experimentation.</strong>
</p>
