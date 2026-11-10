# HumanBridge — Product Requirements Document

**Version:** 1.0 · **Date:** 2026-11-10 · **Status:** Approved hackathon MVP scope, not production specification  
**Deadline:** November 13, 2026, 01:30 IST · **Target submission:** November 12, well before deadline  
**Owner:** Hackathon development team · **Primary AI coding environment:** Codex in the actual local repository

## 0. Evidence and truthfulness contract

**Observed in user's Sandbox terminal (VERIFIED):**
- Orders v2 AUTHORIZE flow: a $5 USD order was buyer-approved and authorized.
- Payments v2: a **single final capture** of **$2.25 USD** succeeded; capture status and amount were read back as `COMPLETED` and `2.25`.
- A separate $5 authorization was successfully **VOIDED**; state read back as `VOIDED`.
- This is a *Sandbox* test; no real funds moved. The remaining $2.75 was not captured, but timing of hold removal was not tested.

**Inspected in starter repository (OBSERVED):**
- React + Vite frontend; FastAPI backend; SQLite; Gemini extraction function; scripted sample receipt generator; PayPal Sandbox REST client.
- The frontend renders a batch of 4 generated receipts and 3 review tasks with *scripted readings*.
- Backend tests: seven tests passed in the authoring environment; these include mocked PayPal behaviors, not real calls from the application.
- `frontend/src/main.jsx`: reusable `Button` defaults to `type='button'`, and Reviewer + upload forms do not override it. This prevents their `onSubmit` handlers from firing when those buttons are clicked.

**Not yet verified (UNKNOWN):**
- Actual Gemini extraction from the full application with the team's API key.
- A complete reviewer submit → requester acceptance → final capture through the *full application UI*.
- Successful production deployment and browser automation.
- Accuracy improvements or cost savings on unseen documents.
- Customer adoption, PayPal revenue impact, or uniqueness versus competitors.

**Required labeling:** Do not call the solution production-ready, an escrow, a reviewer marketplace, or an automatic payout platform. Do not describe a synthetic dataset as real merchant transaction data. Do not claim human-review results are factually correct solely because arithmetic validation passes.

## 1. Product summary

**Name:** HumanBridge  
**Pitch:** *When AI isn't reliable enough, buy a second opinion.*

HumanBridge is a **Sandbox-only, fixed-provider paid human-verification service** for AI-extracted receipt totals. It extracts fields from receipt images, flags specific uncertainty signals, creates a narrow human-review task, and enables the **requester** to authorize a payment budget with PayPal and later accept or skip each submitted review. The application then makes **one final capture** for the accepted service fees—or voids the authorization if no work was accepted.

PayPal handles the buyer-approved authorization and the verified settlement; the **application** enforces the budget ceiling. The configured merchant is the verification service provider. Reviewers do not receive individual PayPal payouts in this MVP.

## 2. Audience, problem and value

**Requester:** A small-business operator using AI to process receipts and wanting to avoid silent errors without paying to review everything.

**Reviewer:** A participating human who checks only the flagged receipt region, submits a proposed correction, and does not control payment.

**Problem:** Fully automatic document extraction may silently misread totals; reviewing every document consumes human time. A requester needs a transparent, selective review workflow linked to an approved cost.

**Value hypothesis:** Selective review might recover more actual extraction errors for a given number of human reviews than random review, while requiring less labor than reviewing everything. This must be **measured on a labeled evaluation set**. PayPal business impact (additional transactions / support for agent-initiated service purchases) is a **hypothesis**, not measured revenue.

## 3. Hackathon requirements

The official project requires meaningful PayPal + AI integration, a functional build or complete runnable setup, public source repository with top-level license, identification of tools used, and a public YouTube demo **under three minutes**. The judges assess technology, design, impact, innovation, and presentation. No sponsor tool is mandatory.

**Winning demo objective:** Show one genuinely live AI reading of a receipt, one documented reason for human escalation, one human correction and requester acceptance, and a PayPal Sandbox capture ID for the approved service total. Include a concise, reproducible evaluation, without unsupported savings numbers.

## 4. Scope and exclusions

### P0 — Must work before submission

1. **Real AI receipt processing**: upload one or several non-sensitive PNG/JPEG/WebP test receipts; make genuine Gemini API calls; show structured receipt fields and any model disagreement/validation failures. Failure states must be visible, not silently replaced by scripted results.
2. **Transparent escalation**: flag missing totals, disagreement between two readings, and subtotal+tax inconsistency (where all necessary fields are present). Explain why each receipt was or was not flagged. These are heuristics, not calibrated confidence probabilities.
3. **Human review**: task-specific reviewer page with a cropped evidence region, editable corrected total, working submit button, server-persisted `SUBMITTED` status, and clear success/error feedback.
4. **Requester decision**: display submitted answers; allow explicit Accept or Skip; update the UI without a manual full-page refresh. Requester acceptance is required before payment for a task.
5. **Real PayPal Sandbox flow**: buyer approves a USD authorization; application verifies order and authorization; only server-computed accepted fees are eligible for capture. Single final partial capture, amount read-back and PayPal IDs visible. If all tasks skipped, void with verified status.
6. **Quality UX**: cohesive visual hierarchy, responsive layout, input validation, accessible labels, loading/disabled/error/success states, no nonfunctional buttons, no prominently fictional results masquerading as live processing.
7. **Reproducible demo**: sample receipt *images* with known correct answers are acceptable, but the primary demo must send the images to Gemini live. If a replay fallback exists, label it clearly as a recorded/replay mode, not live inference.
8. **Submission readiness**: tests, reproducible setup, safe `.env.example`, public license, README, screenshots, and under-three-minute YouTube recording.

### P1 — Valuable only after P0 is stable

- Evaluation results comparing AI-only, random-k review, selective-k review, and full review on a labeled held-out test set.
- Better reviewer crops localized around the total if reliable; if not, present bottom-region heuristic honestly.
- Approval redirect to a real local callback route rather than an `example.com` placeholder.
- More reliable partial payment retry/status polling and rate-limited model calls.

### Out of scope

- Arbitrary reviewer payouts, KYC, multi-merchant marketplace, escrow, live commercial payments, subscription billing, training/calibrating a novel ML risk model, broad document-type support, autonomous spending without buyer approval, full identity management or production-grade sensitive-document hosting.

## 5. End-to-end user journeys and acceptance criteria

### Journey A — A flagged receipt gets paid review

1. Requester starts a new batch and uploads a known-answer test image.
2. Backend invokes Gemini and stores the returned structured readings plus their provenance (`LIVE_GEMINI`).
3. Heuristic flags a specific field and explains the reason.
4. Requester creates a PayPal AUTHORIZE order for the displayed budget and approves it in Sandbox Checkout.
5. Backend verifies that the order is `APPROVED`, authorizes it, stores the authorization ID, and shows `AUTHORIZED`.
6. Reviewer opens a narrow review link, enters a corrected total, and clicks Submit. The backend persists `SUBMITTED`; UI shows confirmation.
7. Requester sees the submitted answer (without manual refresh), chooses Accept, and the backend persists `ACCEPTED`.
8. After all review tasks are Accepted or Skipped, requester clicks Settle. Backend totals fees for accepted tasks only, checks the app budget ceiling, captures once with `final_capture=true`, verifies capture amount/status via PayPal GET and stores capture ID.
9. UI shows actual captured amount and not-captured amount. It does **not** claim that an unused hold disappeared immediately.

**Acceptance:** The flow works from a clean browser session with no database manipulation, manual API calls or editing of code; any error is actionable.

### Journey B — Nothing gets paid

1. Requester authorizes a batch with review tasks.
2. All tasks are Skipped.
3. Settle voids the authorization and independently reads back `VOIDED`.

**Acceptance:** $0 captured; no empty or fake capture record.

### Journey C — Model fails or predicts no review required

1. A Gemini request fails or yields unusable JSON; UI reports an explicit processing error and permits retry without inventing data.
2. If no task is flagged, explain that no paid review is necessary and do not offer a misleading authorization action.

### Journey D — Reviewer UI regression

1. Open a pending task using the generated token URL.
2. Enter `32.40` and click **Submit verification** (no Enter-key workaround).
3. The request is sent exactly once and state becomes `SUBMITTED`, with an on-screen confirmation.

**Acceptance:** Automated browser/component regression test or equivalent verified interaction covers this. The upload form submit button receives the same protection.

## 6. Model and policy contract

**Model input:** Receipt image bytes.  
**Model output:** validated JSON fields `merchant`, `date`, `subtotal`, `tax`, `total`. Unknown fields stay `null` rather than hallucinated. Two readings from the same model are correlated, so don't call them independent evidence or calibrated confidence.

**Policy input:** parsed numbers, disagreement flags and arithmetic checks.  
**Policy output:** `flagged: boolean` and specific reasons. Financial arithmetic uses Python `Decimal`, never float. A passed arithmetic check is not proof of truth.

**Optional prioritization:** Require evidence of uncertainty; use an explicitly assumed error cost and a stated per-review fee. Do not present risk scores as measured probabilities unless properly validated.

## 7. Payment and data rules

- Sandbox API hostname only: `https://api-m.sandbox.paypal.com`.
- Use OAuth `client_credentials` server-side; no Client Secret or access token in frontend or logs.
- Store order ID, authorization ID, capture ID and PayPal-request idempotency identifiers.
- Treat frontend amounts/status as untrusted. Server computes totals from accepted tasks and enforces a strict *application-level* ceiling.
- A payment can enter settlement only after authorized budget and every review task has a final decision.
- Never retry capture blindly after timeout: query PayPal and reconcile persisted state/idempotency first.
- Browser success redirect is not payment proof; verify via server-to-PayPal API.
- The capture goes to the configured Sandbox merchant, **not** directly to each reviewer.
- Allow a failed PayPal operation to remain visibly recoverable. No false green badges.
- Tokenized reviewer URL is an MVP convenience, not authenticated identity. Avoid uploading real customer PII. Existing `/uploads` content is publicly served; deployment must use non-sensitive test files or upgrade access controls.

## 8. UI / UX requirements

**Design goal:** restrained, high-quality fintech SaaS—not a debugging screen or a dashboard full of technical labels. Strong visual hierarchy, generous spacing, responsive cards, meaningful microcopy, semantic status colors.

**Primary areas:**
- Requester workspace: upload and batch overview, AI result comparison + reasons, review queue with acceptance, PayPal budget and settlement summary.
- Reviewer workspace: minimum necessary crop, field to correct, submit status, fee disclosed.
- Evidence/results: transaction IDs and audit timeline; optional evaluation with actual computed metrics.

**Interactions:** All primary buttons must work with mouse, keyboard and ordinary form submit behavior; every asynchronous action shows busy state; errors identify the failed step. Poll or refetch review-task status automatically (3–5 seconds is acceptable) so a separate reviewer tab is reflected without manual refresh. No demo-only controls that silently change state without the backend.

**Copy:** Replace repetitive "simulated/demo" badges on every card with a single unobtrusive source disclosure near a relevant sample dataset. Clearly label `Live AI` vs `Sample images` vs `Recorded replay` where applicable. Never hide that PayPal transactions are Sandbox-only.

## 9. Existing code map (inspected 2026-11-10)

```
frontend/src/main.jsx       Single-file React requester/reviewer UI; contains submit-button bug
frontend/src/styles.css      Current styling
frontend/vite.config.js      Proxies /api and /uploads to local FastAPI :8000
backend/api.py              FastAPI routes, SQLite state, upload handling, payment state machine
backend/ai_engine.py        Gemini model extraction, arithmetic/disagreement, crop heuristic
backend/paypal_client.py    Sandbox-only Orders/Payments REST calls
backend/demo_data.py        Sample image generator PLUS SCRIPTED extraction readings
backend/tests/              7 tests passed in authoring environment
backend/.env.example        PayPal and Gemini environment keys
```

Current endpoints: `/api/batches`, `/api/batches/demo`, `/api/batches/{id}/documents`, `/api/batches/{id}`, `/api/batches/{id}/payment/{create,authorize,settle}`, `/api/tasks/{id}`, `/api/tasks/{id}/submit`, and `/api/batches/{id}/tasks/{id}/{accept,skip}`.

**Known immediate bug:** `Button` defaults `type='button'`; Reviewer and Upload forms omit `type='submit'`. Fix both and add a test first.

**Known gaps:** Live Gemini not yet verified; manual requester refresh; no fair evaluation module; placeholder PayPal return URLs; sample mode's extraction results bypass Gemini; missing production authentication/access controls (explicitly out of scope for demo with synthetic receipts).

## 10. Evaluation methodology (P1 only, after working MVP)

Use a committed set of *synthetic but image-based* receipt fixtures with correct values known at generation, plus a few separately labeled permission-safe real receipts if available. Run actual extraction on images, store model version, prompts and timestamp. Keep train/tuning fixtures separate from held-out evaluation; do not tune on the held-out set.

Compare:
- **AI only:** extracted totals without review.
- **Full review:** every receipt's total is reviewed (cost upper bound; don't claim all human answers correct).
- **Random k:** randomly select k cases to review, where k equals the selective review count; use seeded random repetitions and report mean/range.
- **Selective k:** heuristic chooses k cases for review.

Metrics: exact-match total accuracy against known ground truth; errors found per reviewed item; number of review tasks; estimated review cost at clearly stated fee. Synthetic data cannot support claims of real-world savings or calibrated error probabilities. If results are disappointing, publish the result honestly.

## 11. Engineering quality gates

- **P0.1**: Reviewer + upload submits work via click and Enter; error and success state visible; regression tests pass.
- **P0.2**: A sample *image* is analyzed by a genuine Gemini call and persisted as `LIVE_GEMINI`; model errors aren't hidden.
- **P0.3**: Review state persists through reviewer and requester views; auto-refresh; accepting task updates approved service total.
- **P0.4**: Full app sandbox tests reproduce authorized budget → correct final partial capture and void paths. User has already verified these behaviors in a standalone smoke test.
- **P0.5**: Frontend build and backend tests pass; fresh local setup works without secrets committed; demo script shows actual data and PayPal IDs.
- **P0.6**: README, LICENSE, public repo, hosted demo OR complete setup, public YouTube video under 3 minutes, Devpost project submitted before deadline.

## 12. Timeline / ownership

- **November 10:** Fix forms, add tests, get live Gemini processing and reviewer state flow working; make one real API-backed journey.
- **November 11:** Build coherent UI and integration reliability, run end-to-end manual QA, deploy Sandbox-only instance.
- **November 12:** Limited evaluation and evidence, fix regressions, finalize README and demo video, submit early.

**Cut rule:** If running behind, cut model comparisons, fancy visual effects, extra source formats and additional charts *before* cutting the working PayPal flow, live Gemini processing or actual reviewer interaction.

## 13. Outstanding decisions / risks

1. Which specific Gemini model/version is actually available to the team's API key? Existing code defaults to `gemini-2.5-flash`; do not assume a working quota.
2. Are our pre-approved sample images sufficient to trigger genuine model disagreement consistently? If not, allow visibly manual flagging of a real uncertain case or use an accurately labeled recorded AI result; do not fabricate live outcomes.
3. Will frontend browser tests run in the team's Windows environment? If not, perform documented manual click tests and ship regression tests that can run in CI later.
4. Hosted demo may expose receipt images/review URLs; use synthetic/non-sensitive data and strong demo-only access boundaries.
5. The current prototype has no user authentication. Never present it as a production financial service.
6. PayPal captures may fail after authorization; the UI needs an honest error state and a safe retry/reconciliation approach.

## 14. Product decisions log

- 2026-11-10: Selected HumanBridge over checkout audit, escrow and upcycling concepts after competitive review; novelty remains limited and must be demonstrated through selective paid review.
- 2026-11-10: Verified $5 authorize → $2.25 final capture and separate unused-authorization void in the user's Sandbox; no evidence of immediate hold release.
- 2026-11-10: Fixed-provider model selected; no Payouts or marketplace claims.
- 2026-11-10: Rejected 24-sample calibrated ML pitch; use transparent heuristic and fair baseline comparisons.
- 2026-11-10: Identified submit-button form bug and decided to fix before adding features.
- 2026-11-10: Codex will implement small, tested milestones; this PRD owns scope, acceptance and claims.

## 15. Official references

- [PayPal authorize/capture later](https://developer.paypal.com/platforms/checkout/standard/customize/auth-capture/)
- [PayPal Orders v2 API](https://developer.paypal.com/api/orders/v2/)
- [PayPal Payments v2 API](https://developer.paypal.com/api/payments/v2/)
- [Google GenAI Python SDK](https://googleapis.github.io/python-genai/)

**When resuming after lost chat context:** Read this PRD, `AGENTS.md`, `docs/BUILD_PLAN.md`, and `docs/PROJECT_STATUS.md` in that order. Inspect actual code and run tests. The files are the written plan, not evidence that every feature has shipped.
