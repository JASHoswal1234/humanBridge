# HumanBridge — project status and evidence log

**Last verified in this handoff:** 2026-11-11. **This file must be updated by Codex after every milestone.**

## Confirmed working

- [x] Standalone user-executed Sandbox smoke test: $5 authorize -> $2.25 single final capture, status COMPLETED, correct amount.
- [x] Standalone user-executed Sandbox smoke test: second $5 authorization voided, read-back VOIDED.
- [x] React/FastAPI app runs locally (user screenshot); app shows scripted sample receipts and has stored a verified Sandbox authorization.
- [x] Seven backend unit/integration tests passed in authoring environment (mock PayPal), not a UI browser run.
- [x] Reviewer click saved `32.40` through FastAPI. After a browser reload, the reviewer saw `SUBMITTED` and the saved total. The requester saw the answer after clicking Refresh.
- [x] Analyze sends the selected file on click. Chrome verified a real FastAPI image-validation error and retry availability. A browser regression separately verified the success UI with a controlled API response.

## Known broken / unverified

- [x] Discount arithmetic repaired for new extractions. Historical findings retain their original inputs and rules.

- [x] Live Gemini extraction verified through a Chrome upload, two separate provider calls, raw-response comparison and refresh. Broader reliability and accuracy remain unmeasured.
- [x] Requester observed submissions and reviewer observed revision requests automatically in the integrated Chrome test.
- [x] Live application capture verified through authenticated PayPal read-back for the later batch d0d0cc3bba394e80. See Phase 3 evidence below.
- [ ] Full app zero-cost void through UI verified.
- [x] Six-case synthetic evaluation with frozen real model readings and AI-assisted visual transcriptions. This pilot does not estimate production accuracy.
- [ ] Public deployment, clean-room setup, public demo video and Devpost submission.

## Product facts / boundaries

- Configured Sandbox merchant, not reviewer, receives captured payments; **no payouts** in current MVP.
- App is not an escrow; buyer payment authorization is not a guarantee of immediate remaining-hold release.
- The downloadable sample is a generated image processed through the live upload route. The separate scripted batch still uses recorded-in-code readings.
- Batch-owner cookies and task-scoped reviewer capabilities protect receipts in Phase 2. Use synthetic or non-sensitive inputs only.

## Milestone log

| Date | Phase | Files changed | Tests executed | Outcome | Open blockers |
|---|---|---|---|---|---|
| 2026-11-10 | Baseline inspection | None | Backend pytest 7 passed | Form-submit root cause established | UI and Gemini untested |
| 2026-11-10 | Phase 0 | React forms and upload focus style, Playwright config and form tests, frontend package files, test-output ignore, this log | 3 Chrome regressions, 7 backend tests, 2 integrated Chrome checks and Vite production build passed | Both forms submit on click and expose pending, failure and success feedback | Live Gemini extraction and full UI Sandbox settlement await their milestones |
| 2026-11-10 | Phase 1 | Gemini engine, upload API and SQLite schema, model configuration, requester UI and styles, upload tests and opt-in live browser check | 17 backend tests, 3 browser regressions, production build and live Chrome upload passed | Raw Gemini responses matched persisted fields and refreshed UI | Model availability, quota and extraction accuracy across diverse receipts remain unmeasured |
| 2026-11-10 | Phase 2 | Review, payment and access routes, Sandbox client, React UI, rules, tests and browser evidence | 23 backend tests, 3 Chrome regressions, production build and mocked browser journey passed. Live Gemini upload and Sandbox order creation passed. | Buyer approval required for order 9AT65856GL2100331 | Live in-app authorization, capture, and void awaiting verification |
| 2026-11-11 | Phase 3 | Receipt arithmetic, acceptance guard, comparison and evaluation UI, benchmark and tests | 32 backend tests, 10 Chrome regressions, integrated browser test, production build, real Gemini calls and read-only PayPal verification | USD 0.75 final capture confirmed; correct INR discount receipt reconciles | Small synthetic pilot; local demo only |

### Phase 0 verification

Both form actions inherited the shared button's `type="button"`. Each now explicitly uses `type="submit"`. The reviewer uses the status returned by the submit endpoint. Upload retains the file on failure and clears it after success.

- `npm test` in `frontend` ran Playwright in installed Chrome. All three tests failed against the original UI and passed after the repair. They cover one reviewer POST with the token and corrected value, pending state and confirmed status; a rejected total corrected and resubmitted with Enter; and one multipart upload per attempt, the error, retry with Enter, the displayed document and cleared file input. These tests control the API responses. To reproduce, install frontend dependencies with `npm ci` and use Chrome, or set `PLAYWRIGHT_CHANNEL=msedge` for installed Edge.
- `python -m pytest -q` passed all seven existing tests in a temporary copy of the backend source and tests with its own SQLite database and uploads. Engine cases were consistent totals, disagreement, missing amounts and decimal cleanup. Workflow cases were token-protected reviewer submission, funded final capture and unused authorization void. The payment cases used the existing PayPal test double. Pytest emitted one Starlette TestClient dependency deprecation warning.
- Two additional Chrome checks used the real FastAPI routes and a temporary SQLite database. The reviewer click persisted `32.40` across reload and requester refresh. Analyze sent an invalid PNG to FastAPI and displayed its file-validation error with the same file available to retry.
- `npm run build` in `frontend` passed with Vite 6.4.6. All Phase 0 checks completed. The initial sandboxed runs stalled on local networking and were rerun with local process/network access.
- Live Gemini extraction and a buyer-approved Sandbox checkout, capture or void were outside this milestone. Successful receipt analysis in the browser suite used a fixture response. The recommended next check is a single non-sensitive receipt through the full upload UI with a genuine Gemini response.

### Phase 1 verification

- Final configuration check with no model override passed on document `3e25b2c7a83f47a2`. Gemini returned response IDs `BeryavaYLaHejNAP3o6e-Qs` and `E-ryapriMLSf3LUPl83ruQE`. Both returned the same header and monetary fields as the first successful run. Pass one transcribed the printed “Goods / Services” label with null quantity and amount. Pass two returned null line items. Both raw responses matched the stored readings. Line-item differences are visible side by side and do not independently trigger a total-review task.
- An intervening live run received HTTP 503. The final configuration permits one model-only retry on transient server errors with a 60-second timeout per request. The final success establishes recovery on a subsequent run; it does not establish how many internal SDK retries occurred.

- Chrome uploaded the generated SAMPLE STATIONERY PNG via Analyze. The configured `gemini-2.5-flash` request returned HTTP 404. After checking the provider catalog, a run requesting `gemini-3.5-flash` succeeded. Both responses reported `gemini-3.6-flash`. The default, example and local model setting were updated.
- Document `dd222ddb1fd7496a`, attempt `cc6d0d26afd1495eab7953d5e5843879`, response IDs `CenyarPUH-L4v_gPicCCqQc` and `GenyauGXJ8vfg8UPxLq2gQM`. Both readings returned SAMPLE STATIONERY, 2026-11-10, subtotal 30.00, tax 2.40 and total 32.40. Visual inspection matched those fields to the source. The receipt prints a dollar sign and has no itemized prices. Both readings returned null for currency and line items. No validation rule flagged it.
- The opt-in `node tests/live-gemini.mjs` command in frontend uses the configured backend key and isolated temporary storage. It compares both parsed raw SDK response texts from SQLite to the upload API output and checks the six scalar fields for both passes in Chrome after reload.
- `python -m pytest -q` passed 17 tests using isolated storage. Ten Phase 1 cases cover valid extraction, missing and contradictory totals, replay after refresh, serial and concurrent duplicates, retry after timeout/API failure/malformed or schema-invalid JSON, invalid and oversized images, and cross-pass findings. Gemini is mocked in these tests. The seven existing cases include mocked PayPal capture and void. One Starlette TestClient deprecation warning.
- `npm test` passed all three Chrome form regressions with controlled API responses. `npm run build` passed. Live PayPal was outside this milestone.
- Per-batch duplicate detection uses identical file bytes. A re-encoded image has a different digest. A crashed request's claim can be replaced on retry after five minutes. Older documents remain readable and lack new pass metadata. At the Phase 1 milestone uploads were publicly served locally. Phase 2 removed that route. Use non-sensitive receipts. Two passes from one model can share errors, and arithmetic rules can flag legitimate adjustments.

### Phase 2 verification and handoff

**Live run, November 10.** The synthetic receipt prints subtotal 30.00, discount 2.00, tax 2.40 and total 30.40. Both Gemini passes processed the image. The subtotal-plus-tax rule produced one review task because it does not model discounts. This illustrates a flag on a legitimate adjustment. Two attempts with the default Gemini model returned HTTP 503. The successful test used a process-local model override to gemini-3.1-flash-lite. Provider responses were uPHyaqHpM9HZjNAPwvvw-Ak and vPHyaqKyGInWg8UP4syAsQk.

The real Sandbox merchant created USD 5.00 AUTHORIZE order 9AT65856GL2100331 for batch fdd6a6a598104d47. Attempting authorization before buyer approval returned HTTP 409 after a PayPal order lookup. The live run stopped there. No live authorization ID, capture ID, capture amount, or void was observed for this order. The requester Chrome profile was reopened at http://127.0.0.1:18276. In that window open Sandbox checkout, approve as buyer, return and verify authorization. A reviewer can then inspect the crop, submit the printed total, and the requester can accept the USD 0.75 service fee and confirm settlement. The approval redirect alone does not change payment state. The local server and temporary requester profile were retained for handoff.

**Checks actually run**

- Backend, isolated SQLite and image storage. `python -m pytest -q` passed 23 tests with one Starlette TestClient deprecation warning. Includes revision and stale revision rejection, duplicate submit/accept, unauthorized batch and document access, scoped reviewer crops, budget and order/authorization binding checks, capture amount mismatch, ambiguous POST reply, failed read-back, final capture replay and all-skipped void.
- Frontend. `npm test` passed 3 Chrome form regressions. `npm run build` passed. `node tests/settlement.mjs` passed against the built frontend, FastAPI and SQLite with controlled Gemini and PayPal providers. Chrome uploaded the synthetic image, authorized, submitted, requested revision, resubmitted, saw the change automatically, accepted, confirmed a USD 0.75 final capture and reloaded the verified record.
- Live. `node tests/settlement.mjs --live` reached buyer approval with the model override above. [Live awaiting-buyer screenshot](evidence/phase2-sandbox-awaiting-buyer.png) and [mocked final settlement screenshot](evidence/phase2-mocked-settlement.png).

**Access and reliability limits**

- New batches issue a random HttpOnly, SameSite=Strict cookie scoped to their API path. The database stores its hash. Old batches lacking ownership evidence remain on disk and cannot be claimed via the web. Clearing cookies loses requester access. Reviewer links are transferable bearer capabilities. Share them only with the intended reviewer. The generated link keeps its token in the URL fragment, and the server delivers only that task's crop through a scoped cookie. The fixed crop can still contain sensitive data. Original files, SQLite and browser profiles need OS-level protection. This local HTTP demo has no user accounts, recovery or reviewer-token revocation.
- Settlements use integer cents, the server-owned accepted fee sum, a fixed application budget, verified USD authorization, order binding and persisted idempotency identifiers. A submitted value passes a numeric-format check. Only the requester may accept the current revision. The capture amount and invoice identifier must match the PayPal read-back. An uncertain settlement stays pending for reconciliation. New capture POST replays stop after five minutes; an unresolved provider result may require manual reconciliation. A configured merchant receives any captured amount.
- Start the built app and frontend on the same origin, or use the Vite proxy. Set APP_PUBLIC_URL on the backend to the requester origin for Sandbox return/cancel links (default http://127.0.0.1:5173). The browser test starts an isolated instance with its own return URL. Subsequent live verification still depends on buyer approval and PayPal availability.

### Phase 2 live settlement reconciliation — November 10, 2026

**Phase 2 has not passed the live settlement gate.** A read-only PayPal Sandbox Orders v2 lookup for order `9AT65856GL2100331` returned `PAYER_ACTION_REQUIRED`, intent `AUTHORIZE`, purchase-unit reference `fdd6a6a598104d47`, USD 5.00, zero authorizations and zero captures. The order lookup alone cannot explain what happened in the buyer's browser.

The isolated handoff SQLite database still records `AWAITING_BUYER`, no verified authorized amount or currency, no authorization ID, no pending or completed capture ID, and zero captured cents. Its only task is `PENDING` with no reviewer value or format check. The fee is 75 cents and the sum of accepted fees is zero. The audit trail ends at order creation. The separate default database contains an older authorized order with three pending tasks and zero locally recorded captured cents.

There is no capture resource to verify for final-capture semantics, USD 0.75 or COMPLETED status. The prior live dashboard screenshot shows USD 0.00 captured. The USD 0.75 screenshot is explicitly mocked. A fresh authenticated browser reload could not be verified because Windows Computer Use could not establish the active browser URL. Capture replay remains covered by earlier mocked regression tests only. This reconciliation issued no payment mutation or duplicate capture requests.

Both repository evidence screenshots were visually checked and show synthetic receipt data. No buyer credentials or API secrets were visible. An exact-value scan found no configured API credential values in Git-tracked or nonignored workspace files. The live settlement harness disables access logging and discards server stdout and stderr. This inspection does not cover third-party logs or establish that every external logging system is free of sensitive data.

### Existing-order checkout diagnosis — November 11, 2026

**Live gate still open.** On November 10 the app's saved URL exactly matched the payer-action link returned by PayPal for order 9AT65856GL2100331, and the Orders API reported PAYER_ACTION_REQUIRED. On November 11 a merchant-authenticated GET of that same order returned HTTP 404, RESOURCE_NOT_FOUND, issue INVALID_RESOURCE_ID. The API did not specify the cause. SQLite retained batch fdd6a6a598104d47 and its original order ID. Buyer approval has never been confirmed for this order. The diagnostic issued no authorization or capture and created no replacement order.

The standalone smoke script and app use the same configured merchant client ID, Sandbox endpoint, AUTHORIZE intent, USD 5.00, NO_SHIPPING and CONTINUE. The smoke script prints the approval link, uses example.com callbacks, then checks the order directly. The app stores the provider link and used a new browser tab. Its callbacks target the requester origin (the live harness supplied http://127.0.0.1:18276). Previously the app ignored the returned token and restored the last local batch. The available handoff-profile history showed no matching checkout or return visit at inspection. It cannot establish actions in another browser or explain the buyer's earlier attempt.

The repaired checkout uses a same-tab link, remembers the originating batch, includes its ID in newly created callbacks, rejects mismatched return tokens, and automatically makes an owner-scoped read-only status check. Only a confirmed approval offers authorization. The authorization endpoint independently checks the order, serializes overlapping attempts using a temporary SQLite claim, reuses the persisted PayPal request ID, and reconciles an existing authorization. Cancel, pending buyer action, authorization in progress, verified authorization, lookup failure, and unavailable orders have distinct feedback. The dedicated server on port 18276 was restarted against the original DB and the new endpoint was confirmed installed.

**Verification.** In a disposable Chrome session the production UI replayed the previously observed pending state with the actual stored link. Clicking it sent a top-level navigation to the exact Sandbox URL and received HTTP 200 with zero app-page exceptions. This checked navigation only. The latest real Orders GET still returned 404. No buyer login or approval was performed. Browser errors from the original buyer session could not be reconstructed.

- Backend: python -m pytest -q passed 25 tests, one Starlette TestClient deprecation warning. Includes token mismatch, unapproved order, missing order, overlapping authorization and repeated verification.
- Frontend: npm test passed all 10 Chrome tests, including approved and cancelled redirects, return without approval, wrong token, repeated checks, expired and missing orders. Provider responses were controlled.
- Production: npm run build passed. node tests/settlement.mjs passed the integrated Chrome/FastAPI journey with mock providers.

### Phase 3 — verified November 11, 2026

**Existing live payment.** The latest completed application batch was d0d0cc3bba394e80. Merchant-authenticated GETs for order 1B333614S2898610X, authorization 3G9762350K405751E and capture 0BE79771PC5698017 confirmed a final COMPLETED capture of USD 0.75. PayPal returned the expected related authorization and order IDs, an authorization parent link, a matching invoice identifier and final_capture=true. SQLite recorded CAPTURED, 75 captured cents and one ACCEPTED task with a 75-cent fee. The stored AI total was 260.19 and reviewer total was 260.18. This is a different order from the earlier unavailable checkout. No new PayPal mutation was used. The production dashboard displayed the same authorization ID, capture ID and USD 0.75 after reload at 1280px and 390px with zero horizontal overflow. Browser verification used a temporary database snapshot with a disposable owner credential. The original record was opened read-only.

**Receipt and reviewer evidence.** New Gemini readings capture typed discounts, charges and rounding adjustments with magnitude and their relation to the printed subtotal. Each printed component is quantized to two decimal places with Decimal ROUND_HALF_UP before summation, and the rounded total must match exactly. Included adjustments are not applied twice. Only the printed tax is used. Unknown adjustment amount/direction defers arithmetic and requests review. Absent subtotal or tax leaves the equation unavailable. Equivalent recognized dates compare canonically; ambiguous numeric dates are not assigned a guessed locale. Legacy stored readings lack adjustment provenance and retain their historical findings.

A genuine two-pass Gemini check on a non-sensitive reconstruction of the INR receipt returned subtotal 245.00, discount 24.50 (subtract), tax 39.69 and total 260.19 on both passes. Model gemini-3.1-flash-lite, response IDs povzasSxOdP0694P6JavmQQ and rovzasL9Bp2EjuMPwtjp2Qw. Neither pass triggered a review finding. For new acceptance decisions a one-cent arithmetic conflict or disagreement with every readable model total requires a requester explanation. The backend enforces this inside the same transaction as acceptance and records the reason and findings. No retroactive reason was assigned to the live capture.

**Evaluation.** Six fixed, separately generated receipts, seed 4317, two real Gemini responses per image and AI-assisted visual transcriptions (provenance corrected in Phase 4). Both readings matched all six labeled totals. Full review returned four correct totals and two unreadable responses. The selective rule requested zero reviews, so same-budget random review also selected zero. All four policies detected and corrected zero AI errors. At an assumed USD 0.75 per requested review, estimated full-review spending was USD 4.50 and the other policies USD 0.00. Corrections per review were 0 for full review and undefined for the three zero-review policies. These are modeled costs; the evaluation created no payments. This run cannot measure the ability to catch errors or establish an accuracy or spending advantage. See [reproduction instructions](../evaluation/README.md).

**Verification and readiness.** Backend pytest passed 32 tests with one Starlette TestClient deprecation warning. The 10 frontend Chrome regressions and Vite production build passed. The production-build browser workflow with controlled providers passed submission, revision, a conflicting one-cent correction, disabled acceptance until a reason was entered, persisted approval, mock settlement and reload. Deploy the backend and corresponding frontend build together. The app is suitable for a local Sandbox demonstration. Public hosting, production identity, zero-cost live UI void and external deployment remain unverified. Receipt access, local storage, model availability, and limited evaluation coverage remain deployment constraints.

## Phase 4 • submission readiness, November 11

**Local fallback passed from a clean Windows Git clone.** New Python venv, pip install, npm ci, production Vite build, backend tests and the compiled same-origin Chrome settlement journey all succeeded without copying the private database, uploads or provider keys. Python 3.10.7 and Node 22.18.0. The standard Chrome suite also passed in the working checkout.

| Check actually executed | Result |
|---|---|
| python -m pytest -q | 33 passed in the working checkout and 33 in the clean clone. One Starlette TestClient deprecation warning in each. Includes hosted-origin cookie and callback regression. |
| npm test | 12 Chrome tests passed, including seven checkout states, three form regressions and two keyboard/layout checks at 390 and 1280 px. Initial sandbox browser access was denied and the default test port was occupied; the completed suite used an available loopback port. |
| npm ci and npm run build | Clean install and production build passed. npm reported zero known vulnerabilities in this install. |
| node tests/settlement.mjs | Passed in both checkouts with actual HTTP, browser, SQLite and mock providers. Covered upload, revision, repeat submission, acceptance, final settlement and reload. |
| node tests/live-gemini.mjs | Actual synthetic image upload passed. Two Gemini responses pZDzav2CJJ3cqfkPgb7p8AE and p5DzaqTHI46-694PyfnZMQ returned 32.40. Persisted readings matched provider outputs and survived reload. No findings. |
| evaluation/benchmark.py score and evaluation/challenge.py | Original frozen six cases rescored; three additional degraded synthetic images processed by two genuine calls each. Blur passed; crop lacked a total; fold preserved the correct total but triggered subtotal/arithmetic findings. No human evaluation or payments on the challenge. |
| Security and repository | Release audit checked 53 tracked files against configured API credentials, stored reviewer tokens, common key patterns and restricted data paths. No matches. Historical evidence screenshots show synthetic receipts. Removed eight generated fixture PNGs from Git tracking while retaining local files. Runtime data and private .env are ignored. |
| Render Blueprint | Validated locally against Render's official JSON schema. No provider account was provisioned. Hosted HTTPS, restart persistence, callback and model access await a deployed URL. |
| PayPal Sandbox | No new order or charge in Phase 4. The earlier authenticated Phase 3 read-back of the USD 0.75 final capture remains the live financial evidence. Live in-app zero-cost void remains unverified. |

**Evaluation attribution correction.** The six responses previously supplied were AI-assisted visual readings. Four matched and two abstained. The six-case run has zero initial total errors and zero selective reviews. Accuracy uplift, independently measured human accuracy and realized savings remain unmeasured. The separate three-case run preserves all outcomes, including a flagged receipt whose total was correct. [Method and evidence](../evaluation/README.md)

**Release materials.** Root README with architecture and clean setup; root MIT license; private-variable template; optional Render Blueprint and dashboard runbook; timed 2:45 narration and recording checklist; [desktop](evidence/phase4-desktop.png) and [mobile](evidence/phase4-mobile.png) product screenshots. Use the printed fold fixture for conditional review. The original historical discount batch remains evidence of a service payment even though the accepted correction differed from the printed total.

**Outstanding owner actions.** If a hosted demo is desired, approve the Render service and disk cost, supply keys privately and complete the restart smoke test. Public batch creation has no per-user quota; limit Gemini quota before sharing. Record and verify the public video, enter the links and team details and submit. There is no tested public application URL or submitted entry in this handoff.

## Final UI revision • The Evidence Desk • November 12

The requester now sees a downloadable synthetic folded receipt on the landing page, then an evidence workspace with a source image, paired readings, highlighted policy findings, review decisions and a settlement ledger. The active workflow link follows persisted task and payment state. For batches with multiple receipts, the selector initially opens a flagged receipt when one exists. The reviewer screen shows only its assigned crop, original proposed total and submission form. All three fonts are served locally with their SIL Open Font Licenses.

| Check | Observed result |
|---|---|
| npm test | 12 Chrome regressions passed. Coverage includes approval/cancel/expired/wrong-token returns, duplicate verification, upload and reviewer failure/retry, and keyboard/layout checks. |
| npm run build | Production Vite build passed, including embedded sample and three local WOFF2 faces (85,252 bytes total). |
| python -m pytest -q | 33 backend tests passed. One existing Starlette TestClient deprecation warning. |
| node tests/settlement.mjs | Compiled frontend, real HTTP and isolated SQLite passed upload, review, revision, resubmission, override reason, requester acceptance, final settlement and reload with fixture providers. Checked all four active navigation stages against the fixture workflow. |
| Responsive evidence | Home, populated requester and crop-only reviewer checked at 1440, 768 and 390 CSS pixels; no page-level horizontal overflow. Desktop and mobile decision and settled states also passed the overflow check. |

[Before and after screenshots](evidence/evidence-desk) include home, requester and reviewer at desktop and mobile widths. The decision and settled PNGs are stamped as browser fixtures with mocked Gemini and PayPal. The original Phase 3 authenticated capture remains the live financial evidence. No new external AI or PayPal transaction ran for this frontend revision. Browser checks used desktop Chrome viewport emulation; physical iOS/Safari and hosted deployment remain untested for this revision.

## Native Render Free preview • November 12

Prepared a single Python web service with a Vite production build, one FastAPI worker, ephemeral SQLite and uploaded images under /tmp/humanbridge. This free configuration supersedes the earlier paid-disk proposal. Receipts, tasks and batches disappear on sleep, restart or redeploy. The server blocks order creation, approval lookup, authorization, paid acceptance and settlement in preview mode. Local Sandbox payment behavior remains covered by the existing mocked tests.

Verification: 35 backend tests passed (one existing Starlette warning), 12 Chrome regressions passed, and the Vite production build passed. An additional Chrome smoke test opened the compiled application in preview mode, saw the disabled payment panel, submitted an unpaid scripted review and observed it on the requester page. Live hosted Gemini and the public Render URL await deployment. [Manual dashboard settings](RENDER.md)
