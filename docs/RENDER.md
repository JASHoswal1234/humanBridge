# Manual Render Free preview

In the Render dashboard choose **New → Web Service**, connect the public GitHub repository **JASHoswal1234/humanBridge**, and use the following settings.

| Setting | Value |
|---|---|
| Branch | main |
| Root Directory | Leave blank (repository root) |
| Language / runtime | Python 3 |
| Instance type | Free |
| Build Command | `python -m pip install -r backend/requirements.txt && npm --prefix frontend ci --include=dev && npm --prefix frontend run build` |
| Start Command | `python -m uvicorn api:app --app-dir backend --host 0.0.0.0 --port $PORT --workers 1 --no-access-log` |
| Health Check Path | /api/health |
| Persistent disks / databases / additional services | None |
| Auto-deploy | Off for manual deployments |

Under **Environment** set the variables below, then click **Deploy Web Service**. Render provides PORT and RENDER_EXTERNAL_URL. FastAPI serves the Vite build and relative API routes on the same HTTPS origin. Node and npm are included in the native runtime. [Render native runtimes](https://render.com/docs/native-runtimes)

| Key | Value |
|---|---|
| HUMANBRIDGE_FREE_PREVIEW | 1 |
| PYTHON_VERSION | 3.11.14 |
| NODE_VERSION | 22.18.0 |
| DB_PATH | /tmp/humanbridge/humanbridge.db |
| UPLOAD_DIR | /tmp/humanbridge/uploads |
| GEMINI_MODEL | gemini-3.1-flash-lite |
| GEMINI_API_KEY | Enter a private Gemini key from a free-tier project with billing disabled |

Leave PayPal credentials unset. Use only the Free instance and included quotas. Use the scripted walkthrough if free Gemini quota is unavailable. The backend disables payments on Render and whenever HUMANBRIDGE_FREE_PREVIEW=1, even if credentials are present. Reviewers can submit values; requesters can compare, request revisions and skip. Paid acceptance and settlement stay in the local Sandbox workflow.

Free services spin down after inactivity. **Uploaded receipts, SQLite records and review links disappear on spin-down, restart or redeploy.** Start a new batch after waking the service. Use synthetic receipts only. [Render Free lifecycle](https://render.com/docs/free)

After deployment open /api/health and /api/config. Confirm free_preview is true and paypal_enabled is false. Open the root page, use New live batch, upload the folded synthetic sample, and inspect both Gemini readings. A flagged result offers a task-scoped review. Confirm the settlement panel says Payments disabled. Share the assigned URL after this check.
