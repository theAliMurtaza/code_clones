# Updated interface and Google sign-in

The UI now has a responsive two-column sign-in screen, centered feedback for
foreground requests, a centered analysis progress screen, and a numeric analysis
summary. Type-4 retains a short candidate/status label. Scores remain model scores,
not accuracy percentages. The detection thresholds and acceptance logic did not change.

## Enable Continue with Google

1. Open [Google Cloud Console](https://console.cloud.google.com/) and create or
   select a project for CloneScope.
2. Open **Google Auth Platform → Branding**. Set the app name to CloneScope and
   enter your support/contact email. Supply your actual homepage/privacy URLs
   where Google requires them.
3. Configure **Audience** for your intended users. If the app is in testing, add
   the Google accounts you will use as test users. Complete Google's publishing
   requirements before offering sign-in generally.
4. Open **Clients → Create client → Web application**.
5. Under **Authorized JavaScript origins**, add your **frontend website origin**:
   scheme and hostname, without a path or trailing slash. This is where people
   open CloneScope, not the Hugging Face model Space. For local development, also
   add `http://localhost` and `http://localhost:5173` (or your actual dev port).
6. Create the client and copy its **Client ID**, ending in
   `.apps.googleusercontent.com`. This integration uses the GIS popup callback;
   it does not require a redirect URI or client secret.
7. In **Render → backend → Environment**, add:

   ```text
   GOOGLE_CLIENT_ID=YOUR_ID.apps.googleusercontent.com
   ```

   Ensure `ALLOWED_ORIGINS` includes that same frontend origin. Preserve other
   required origins in this comma-separated setting.
8. Deploy the updated backend, including `google_login.py`, `models.py`,
   `config.py`, `main.py`, and `requirements.txt`. Startup creates the new
   `google_identities` table without altering existing users or analysis records.
9. Deploy the updated frontend. The browser obtains the public client ID from
   `/api/auth/google/config`; no `VITE_GOOGLE_CLIENT_ID` is required.
10. Refresh CloneScope, open Sign in, and choose **Continue with Google**. Check
    first-time and returning sign-in. Sign out and confirm email/password still
    works for an existing password account.

Until configured, the Google button is disabled with a short message. It does
not simulate successful login. The backend verifies Google's signature, audience,
issuer, expiry, verified email, and browser nonce. It rejects unapproved origins.
Returning Google users are identified by Google's stable subject ID.

Existing accounts can link automatically only when Google is authoritative for
the verified email (Gmail or Google Workspace). Existing accounts using other
email providers must continue signing in with their password. New Google-only
accounts have no user-known password; use Google to sign in again.

If Google reports `origin_mismatch`, check the exact frontend origin and the web
client selected in Cloud Console. Allow time for console changes to propagate.
If your host applies a strict Content Security Policy, allow the Google Identity
Services script, frame, and connection endpoints. Popup policies may also need
`Cross-Origin-Opener-Policy: same-origin-allow-popups`.

Official references:
[Google setup](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid),
[server-side verification](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token).

## Verification

Backend tests use disposable SQLite databases and locally signed test tokens:

```powershell
Set-Location D:\code_clone_detector\backend
.\.venv311\Scripts\python.exe -m unittest test_google_login test_folder_detection -q
```

The browser smoke test uses Playwright and an isolated local API. It creates a
test account and uploads the repository's example files. Never point it at
production. Start the API with `DATABASE_URL` pointing to a disposable SQLite
file, `DETECTION_ENGINE=lightweight`, `GOOGLE_CLIENT_ID` empty, and
`ALLOWED_ORIGINS=http://127.0.0.1:5174`, listening on port 8011. Start Vite on
127.0.0.1:5174 with `VITE_API_URL=http://127.0.0.1:8011`, then run
`node tests/ui-smoke.cjs` from `frontend` with Playwright on the Node module path.
It checks responsive sign-in, registration, password visibility, centered
loading/success, and numeric results. Screenshots are saved in
`frontend/.ui-checks/` (ignored by Git).

Local tests cannot validate your Google Cloud account/domain setup. Test the
real Google account picker after deploying and configuring the client ID.
