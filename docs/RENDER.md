# Optional Render deployment

The local installation remains available independently of Render. One native Python web service builds Vite and serves the bundle, API, document routes and payment callbacks. The optional Blueprint proposes Starter compute and a 1 GB disk. A paid service is necessary to attach a disk. Review the dashboard's compute and storage charges before authorizing provisioning. [Render persistent disks](https://render.com/docs/disks) · [Current pricing](https://render.com/pricing)

## Dashboard steps

1. Confirm the selected GitHub branch contains render.yaml, the current frontend, and backend. Sign in to Render, select **New → Blueprint**, connect GitHub, select **JASHoswal1234/humanBridge** and choose that branch. Use the repository root and render.yaml.
2. Inspect the proposed single web service, Starter instance and 1 GB disk mounted at /var/data. Stop at the preview unless you approve the displayed cost.
3. In the private environment prompts enter GEMINI_API_KEY, PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET. Use only the Sandbox merchant app. GEMINI_MODEL is set to gemini-3.1-flash-lite. These variables stay server-side. No VITE variables or separate static site are needed.
4. Once approved, apply the Blueprint and wait for the health check. Build and start commands are in [render.yaml](../render.yaml). Render provides PORT and RENDER_EXTERNAL_URL. The app uses the latter for HTTPS cookies and PayPal return/cancel URLs. For a custom domain, set APP_PUBLIC_URL to the exact HTTPS origin before creating an order. Always start and finish checkout on that same hostname.
5. Verify **Disks** lists the mount, and **Environment** shows DB_PATH=/var/data/humanbridge.db and UPLOAD_DIR=/var/data/uploads. One replica and one worker use the same disk. Do not copy the local merchant ledger, original receipts or owner credentials to the service. The local completed batch remains local.
6. Open the assigned HTTPS URL in a normal browser. Confirm /api/health responds, then create a live batch, upload the synthetic sample, inspect both readings and refresh. From a private browser confirm the original batch document is inaccessible. Check desktop and phone widths.
7. Restart the service and reopen the original browser. Confirm both readings AND the preview survive. Check the owner cookie is Secure and HttpOnly. A successful health check alone cannot verify persistence or Gemini.
8. On a genuinely flagged case inspect the Sandbox approval link and return origin before buyer approval. A redirect needs server verification. Use the previously recorded local capture for financial evidence unless a separate hosted checkout is expressly desired. Record which hosted steps actually ran, URL and date in PROJECT_STATUS.md before sharing. Use the tested local instructions if the hosted smoke test fails.

Manual deploys are configured. Disk-backed services can briefly go offline during redeploy. Avoid redeploying during a judge session. Hosting, provider quota, HTTPS redirects and model availability must be tested on the actual assigned host. [Blueprint fields](https://render.com/docs/blueprint-spec)
