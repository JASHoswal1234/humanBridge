# HumanBridge — PayPal AI Hackathon MVP

**When AI is uncertain, buy a second opinion.** A document extraction agent flags uncertain receipt totals, creates a narrow human review task, and charges only requester-accepted review work through PayPal Sandbox authorization and final capture.

> Prototype status: working app code, locally tested backend endpoints and frontend build. Real PayPal checkout and Gemini calls require YOUR credentials and have not been executed by the authoring environment. Your earlier stand-alone smoke test verified $5 authorization, $2.25 single final capture and void using your Sandbox account.

## Prerequisites
- Python 3.10+
- Node.js 20+
- Sandbox Business app Client ID and Secret (from developer.paypal.com)
- Sandbox Personal account for checkout approval
- Optional: Gemini API key for real receipt analysis

## 1. Backend (PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit backend/.env with PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, GEMINI_API_KEY
python -m uvicorn api:app --reload --port 8000
```

API health at `http://127.0.0.1:8000/api/health`.

## 2. Frontend (new PowerShell terminal)

```powershell
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173**.

## 3. Functional walkthrough

1. Click **Load scripted demo**. This creates four synthetic receipt images with **pre-scripted extraction results**; no Gemini API call occurs and the UI labels this clearly. Three are flagged for total review.
2. Click **Create $5 authorization order**. PayPal Sandbox checkout opens in a new tab.
3. Approve with your *Sandbox Personal* account; landing on `example.com/return` is expected (the backend uses the return URL from the tested smoke script).
4. Return to the HumanBridge app. Click **I've approved — verify & authorize**. Backend checks order state with PayPal and invokes authorize.
5. Open each reviewer link in a second tab. Review the bottom-region crop and submit the correct total (e.g. $32.40 for North Stationery, $19.80 for Blue Bicycle, $22.00 for Harbour Grocery).
6. Back in requester tab, click **Refresh**, then **Accept** each submitted review. Alternatively **Skip** a task to avoid paying for that review.
7. Click **Capture $2.25 (final)** (if all three accepted), or lower if some skipped. Backend does a *single final* partial capture and reads back capture status and amount. If all skipped it voids the unused authorization.
8. Inspect PayPal IDs and the audit trail.

For a **live Gemini demo**, click **New live batch**, upload 1–4 receipt images and set GEMINI_API_KEY. The two readings and validators are real, but not guaranteed independent, accurate or calibrated. A clearly readable receipt may generate **zero** review tasks; use an ambiguous image to test escalation.

## API routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/config` | Client-safe enabled features (no secrets) |
| POST | `/api/batches/demo` | Scripted synthetic demo batch |
| POST | `/api/batches` | Empty live batch |
| POST | `/api/batches/{id}/documents` | Upload image and run Gemini |
| GET | `/api/batches/{id}` | Full batch state |
| POST | `/api/batches/{id}/payment/create` | Create PayPal AUTHORIZE order |
| POST | `/api/batches/{id}/payment/authorize` | Verify buyer approval and authorize |
| GET | `/api/tasks/{id}?token=...` | Reviewer task info |
| POST | `/api/tasks/{id}/submit` | Submit reviewed total |
| POST | `/api/batches/{id}/tasks/{task_id}/accept` | Requester accepts work |
| POST | `/api/batches/{id}/tasks/{task_id}/skip` | Requester skips work |
| POST | `/api/batches/{id}/payment/settle` | Final capture of accepted work, or void |

## Architecture and claims

- `backend/api.py`: FastAPI routes, SQLite state and payment lifecycle
- `backend/paypal_client.py`: Sandbox-only REST implementation and stable request IDs
- `backend/ai_engine.py`: Gemini extraction with Pydantic schema, transparent rules for disagreement/arithmetic
- `backend/demo_data.py`: Synthetic receipt generator and **explicitly simulated** readings
- `frontend/`: React, Vite, CSS frontend
- Data: local SQLite and images under `backend/data/`, ignored by Git

**Payment:** the configured Sandbox merchant receives the captured amount. This is a fixed verification provider model, **not** peer-to-peer worker payout or escrow. HumanBridge enforces the application-level budget; the PayPal authorization itself is not claimed as a cryptographically strict or absolute merchant spend cap. The amount not captured is **not** claimed to have been released instantly.

**AI:** Two reads from one Gemini model are correlated; consistency checks are not proof of correctness. Human requester acceptance is required before capture. The demo batch uses scripted values to verify workflow functionality, not to claim real AI accuracy. The bottom-region crop is only a heuristic and is **not** a PII guarantee.

## Security and deployment limitations

**Sandbox and demonstration use only.** The app intentionally does not implement requester authentication, reviewer identity verification, multi-tenant access control, webhook signature verification, production monitoring, or secure sensitive-data retention. Do **not** deploy it for real customer documents or live payments. The reviewer URLs contain bearer tokens, but uploaded images are served without access control, so use only synthetic/non-sensitive test images. Add authentication, private image access, background jobs, atomic state locks, and privacy controls before any production use.

On public hosted demos, keep *all* checkout credentials in Sandbox and use synthetic receipts only. A `dist/` build is optionally served by FastAPI from the same origin for deployment.

## First tests

```powershell
cd backend
python -m pytest -q
```

## Official docs

- [PayPal authorize and capture](https://developer.paypal.com/checkout/delay-capture/)
- [PayPal Orders v2](https://developer.paypal.com/api/orders/v2/)
- [Google Gen AI Python SDK](https://googleapis.github.io/python-genai/)

## Hackathon submission checklist

- [ ] Live Gemini example works on a real test receipt
- [ ] Local end-to-end Sandbox checkout works
- [ ] Reviewer correction and acceptance verified
- [ ] PayPal final capture and optional zero-cost void verified
- [ ] Fair evaluation of AI-only, random, full and selective review completed and published
- [ ] README updated with actual outputs/screenshots
- [ ] Hosted demo or complete clean-setup instructions
- [ ] Public repository with LICENSE
- [ ] Public YouTube demo under three minutes
- [ ] Submission completed before deadline
