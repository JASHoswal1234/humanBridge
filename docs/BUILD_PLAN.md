# HumanBridge — Codex build plan

**Priority:** A working end-to-end judges' demo. **Do not attempt all phases in one coding-agent turn.**

## Phase 0 — Repair broken interaction and establish tests (first)

**Scope:** Fix both React form submissions, improve actionable feedback, add regression tests. No redesign or API rewrite.

- Identify why `Submit verification` does not trigger `Reviewer.submit` and why upload's `Analyze` button may fail similarly.
- Explicit `type="submit"` on both submit buttons. Preserve the default `type="button"` elsewhere to prevent accidental submissions.
- Add a test of the reviewer form click leading to POST `/api/tasks/{id}/submit` and visible `SUBMITTED` confirmation; test upload form click too. Prefer Vitest + React Testing Library or a modest browser test. If dependencies cannot be installed, record manual test steps and add tests with an explicit `not_run` status.
- Validate backend with `python -m pytest -q`, frontend with `npm run build`.

**Gate:** Click submit works without pressing Enter; receipt upload works without pressing Enter; all tests/build pass. Stop if not true.

## Phase 1 — Make AI genuine, reliable and explainable

- Replace primary scripted demo path with a sample **image** batch that calls Gemini live. It is acceptable to keep a separate clearly labeled recorded/replay fallback for network outage.
- Preserve raw image and both structured model responses, including provenance and errors. No fake LLM output.
- Display first/second total, precise reasons for escalation, and actual source image. Use typed JSON/Pydantic validation and null for unreadable fields.
- Add request timeouts, retry limits (safe model-only retries), and useful user-visible failures.
- Add `LIVE_GEMINI` test using mocked model response plus manual test instructions for actual API key. Do not commit key.

**Gate:** A newly uploaded image returns actual model-derived fields through UI, or an explicit error. Recorded example cannot masquerade as live output.

## Phase 2 — Reviewer/requester workflow and payment reliability

- Poll or refetch task statuses so reviewer submission appears to requester within ~5 seconds, without manually clicking Refresh.
- For each task, show Pending → Submitted → Accepted/Skipped clearly. Requester sees correction and evidence before Accept.
- Provide clear confirmation before settlement; no capture if tasks remain undecided.
- Replace `example.com` return/cancel URLs with real app routes if feasible; do not rely on redirect as payment verification.
- Verify order approved and amount USD; verify authorization ID; capture only server-approved cents with `final_capture:true`; verify capture status/amount/ID. All-skipped path voids and verifies `VOIDED`.
- On retries or timeouts: preserve idempotency identifiers and query PayPal before attempting another capture; don't fake success.
- Add integration tests with mocked PayPal client for capture, void, rejection, retries/error paths. The **user** will perform the live Sandbox checkout test in the UI.

**Gate:** Full app works from clean batch through requester approval, reviewer submit, requester acceptance, and final PayPal Sandbox capture. A zero-cost batch voids properly. UI shows true PayPal IDs.

## Phase 3 — UX polish and honest evidence

- Improve hierarchy, typography, responsive layout, micro-interactions and empty/loading/error/success states. Follow existing design system where possible; avoid major UI library installation for decoration.
- Remove repeated intrusive "demo" labels while preserving an accurate single source/provenance disclosure (live AI vs sample image vs recorded replay).
- If time remains, evaluate labeled receipt fixtures using actual model predictions. Include fair AI-only, full-review, random-k, selective-k baselines. Publish raw counts, cost assumption, seed, and held-out data limitations. Do not claim a calibrated model or production savings.
- Provide a concise events/evidence view that lets judges inspect actual PayPal order/authorization/capture references.

**Gate:** Five-minute judge clickthrough has zero dead buttons. At least one real Gemini extraction and one actual Sandbox capture demonstrable. Claims are limited to actual measurements.

## Phase 4 — Deliver and submit

- Setup instructions clean-clone tested on Windows; `.env.example` safe, `.gitignore` correct, MIT license visible.
- Hosted demo (Sandbox-only with non-sensitive documents) or unambiguous runnable instructions.
- Public repository, public YouTube demo **under three minutes**, complete Devpost fields, tools used, screenshots, known limitations.
- Feature freeze before the submission date. Submit on November 12 with buffer before Nov 13, 01:30 IST deadline.

**Gate:** Working deployed/runnable project, repo, public video, Devpost submission actually completed.

## Cut order if behind

Cut: extra model providers → elaborate charts → extra fixture generation → animated components → reviewer matching/marketplace → advanced account infrastructure. **Never cut** working submit, real AI, real Sandbox PayPal capture/void, requester approval, and honest demo.
