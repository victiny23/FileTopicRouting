# Doc Center File Routing Demo

Upload or paste an article; a multi-class topic model (`ml_multi_v1`) decides whether it belongs in the **Doc Center** (cloud computing / telecommunications) or **Quarantine**.

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
2. Predict topic with `data/models/ml_multi_v1.joblib`
3. If topic is `cloud_computing` or `telecommunications` → **accepted** to Doc Center
4. Otherwise → **quarantined**, with a message listing allowed topics

Session file lists (Doc Center / Quarantine) live in memory on the API process and reset when the backend restarts.
