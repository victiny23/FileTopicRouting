# Doc Center File Routing Demo

Upload or paste an article; a multi-class topic model (`ml_multi_v1`) routes it to **Doc Center**, **Needs review**, or **Quarantine** using max-proba confidence abstain.

## Requirements

- **Python 3.11+** (scikit-learn 1.8.0 is required to load the saved model; system Python 3.9 is not enough)
- **Node.js 18+** and npm

## Setup

### Backend

```bash
cd backend
python3.11 -m venv .venv   # or: /opt/anaconda3/bin/python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API: [http://127.0.0.1:8000](http://127.0.0.1:8000)  
Health: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI: [http://localhost:5173](http://localhost:5173)  
Vite proxies `/api` to the backend on port 8000.

## How routing works

1. Extract text from `.txt` / `.md` / `.pdf`, or use pasted text
2. Predict topic + `max-proba` with `data/models/ml_multi_v1.joblib`
3. If `max-proba < τ` (default **0.26**, OOF-tuned in `ml_multi_v1`) → **Needs review**
4. Else if topic is `cloud_computing` or `telecommunications` → **Doc Center**
5. Else → **Quarantine**

Reviewers can Accept (→ Doc Center) or Reject (→ Quarantine) items in Needs review. Session lists and τ live in API memory and reset when the backend restarts.

## Demo roles (mock switch in the UI)

- **User** — upload; see last-upload outcome (accepted / needs review / quarantined); browse Doc Center only
- **Reviewer** — adjust τ; see all three queues; open files; Accept / Reject on Needs review
