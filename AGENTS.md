# HumanBridge — instructions for Codex and other coding agents

Read `docs/PRD.md` and `docs/PROJECT_STATUS.md` before coding. Inspect the repository; do not assume the planned features are implemented.

## Mission
Ship a coherent, *actually functioning* PayPal AI Hackathon entry before November 13, 2026, 01:30 IST. Favor a single tested end-to-end experience over extra features. The primary demo must use a real Gemini extraction and a real PayPal **Sandbox** authorization/capture. Do not invent model outputs, payment statuses, savings, or verification results.

## Non-negotiable invariants
1. **Sandbox only:** Use `https://api-m.sandbox.paypal.com`; never add production credentials or live payment requests. Never print secrets or upload real PII.
2. **Money is server-owned:** Amounts are integer cents/Decimal; frontend totals are display-only. No capture unless buyer authorized and requester explicitly accepted work. Capture at most application-approved fee total and app budget. Use one final capture; void if accepted amount is zero.
3. **Payment truth from PayPal:** Store real order/authorization/capture IDs, read back status and amount from PayPal. PayPal return redirects are not proof. Respect idempotency and avoid duplicate capture on retries.
4. **Product honesty:** Captured money goes to the configured Sandbox merchant, NOT an individual reviewer. No escrow/payout claims. "Not captured" is not synonymous with "hold immediately released".
5. **AI truthfulness:** Real model results must be real model calls. Sample document images may be generated; scripted readings must never be displayed as live Gemini. Arithmetic validation is not proof of document correctness. Do not claim calibrated confidence without validation.
6. **UI integrity:** Every interactive control needs a real action, visible loading/error/success states, keyboard accessibility and sensible disabled states.
7. **No unnecessary rewrites:** Preserve working FastAPI, React, SQLite and PayPal modules unless a concrete issue requires changing them. Avoid adding major frameworks, multiple model providers or platform-wide architecture.
8. **Tests before polish:** Write regression test for each reported bug. Run backend tests and frontend build after each relevant milestone. If browser tools are unavailable, clearly say what was not tested.

## Actual repo baseline (inspected 2026-11-10)
- `backend/api.py`: FastAPI, SQLite routes / task/payment state.
- `backend/paypal_client.py`: PayPal Sandbox only.
- `backend/ai_engine.py`: Gemini extract + heuristic.
- `backend/demo_data.py`: generated images AND pre-scripted readings (not real AI).
- `frontend/src/main.jsx`: requester and reviewer UI. **Known bug**: form buttons inherit `type='button'`; reviewer submit and upload do not trigger form submission by click.
- Seven backend tests passed in the baseline authoring environment. The app's live Gemini and browser end-to-end behavior have **not** been verified yet.
- The user independently verified authorize $5 / single final capture $2.25 / void $5 in a separate Sandbox smoke test.

## Commands
Backend (Windows PowerShell):
```powershell
cd backend
python -m pip install -r requirements.txt
python -m pytest -q
python -m uvicorn api:app --reload --port 8000
```
Frontend (separate PowerShell):
```powershell
cd frontend
npm install
npm run build
npm run dev
```
Use `backend/.env.example` to create a local `backend/.env`; never read secrets back into chat or commit them.

## Workflow
- Implement only the current milestone in `docs/BUILD_PLAN.md`; finish its acceptance tests before the next.
- At start: inspect code/tests, summarize findings and planned small diff; mention blockers.
- At finish: summarize changed files, commands actually run/results, manual testing still needed, outstanding risks. Update `docs/PROJECT_STATUS.md` based on *observed evidence*, not optimism.
- Ask for approval before introducing a new payment model, expanding to real money or changing business claims.
