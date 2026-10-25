# HCM Lite — Hackathon Demo

A multi-role web app built with **Streamlit + SQLite**, based on the supplied Saylani HCM Lite challenge brief. It is designed as a runnable hackathon demo, not a certified production HR platform.

## Implemented modules

- **M1 Auth & access:** Admin/HR/Employee menus, salted PBKDF2 password hashes, active-account checks, temporary-password change requirement, role-based screens, self-only employee pages.
- **M2 Organization setup:** company name, office hours, grace period, weekend, office coordinates/radius, departments/designations, public holidays, configurable annual/sick/casual quotas, HR account creation, account deactivation/reactivation and password reset.
- **M3 Employees:** HR/Admin registration (creates employee login), directory, job/salary editing, active status, CSV export and CSV import dry-run validation.
- **M4 Attendance:** server timestamp, unique employee/day record, late threshold, half-day under five hours, check-out, employee correction requests, HR approval/rejection, absence reconciliation, optional camera face-detection + office geofence check.
- **M5 Leave:** employee requests, workday counting that excludes configured weekends and holidays, overlap and per-type quota checks, approval/rejection with comments, pending-request cancellation, per-type balances.
- **M6 Payroll:** monthly draft, HRA 40%, medical allowance 10%, illustrative annual tax slabs from the brief, attendance/unpaid-leave deductions, join-date proration, payslip records/PDF, Admin-only finalization/locking.
- **M7 Dashboards & analytics:** role dashboards, headcount/presence/late/on-leave/pending-leave KPIs, attendance and leave charts, payroll run summary.
- **M8 AI assistant:** read-only data tools with role checks when `AI_API_KEY` is configured, policy guidance, built-in fallback answers, no AI write actions.
- **M9 Communications & audit:** announcements, in-app notifications, password changes, and audit events for important UI actions.

## Run locally (Windows PowerShell)

Python **3.11 or 3.12** is recommended. Python 3.14 may not yet have wheels for all optional computer-vision dependencies.

```powershell
py -3.11 -m venv hcm_env
.\hcm_env\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
$env:ADMIN_EMAIL="admin@hcm.local"
$env:ADMIN_PASSWORD="ChangeThisStrongPassword123!"
# Optional: set an AI provider key for the hosted AI assistant
$env:AI_API_KEY=""
$env:AI_MODEL="gpt-4o-mini"
streamlit run app.py
```

If `ADMIN_EMAIL` and `ADMIN_PASSWORD` are omitted, the local demo fallback is `admin@hcm.local` / `Admin123!`. Change it immediately. If the database has already been initialized, changing environment variables does not replace the existing Admin account.

## Recommended demo order

1. Log in as Admin; set company settings and office coordinates/radius; create departments, holidays and leave quotas.
2. Create an HR login from **User Accounts**. This is a temporary password, so HR changes it after first sign-in.
3. Sign in as HR; register employees. Registration creates each Employee login with a temporary password.
4. Sign in as an Employee; change the password, update phone/address, check in/out, request leave, and view announcements/payslips.
5. Sign in as HR; approve/reject leave and attendance corrections, reconcile absences, preview/create payroll, and post announcements.
6. Sign in as Admin; review analytics/audit events and finalize/lock the payroll run.

## Optional camera attendance notes

The camera flow uses OpenCV Haar-cascade **face detection**, checks that exactly one face is in the captured image, and checks the submitted coordinates against the configured office radius with a Haversine distance calculation. The current Streamlit demo asks the user to enter coordinates manually; it does not use the browser's trusted geolocation API. It also does **not** match a detected face to an enrolled employee identity or provide liveness detection. Therefore it is not secure biometric verification and must not be used to decide pay or discipline. A production version needs employee consent, actual browser/mobile geolocation, face-embedding matching, liveness/anti-spoofing, secure biometric storage, fallback correction, and independent security/privacy review.

## Known limitations before production

This is a substantial hackathon demo, but not a production-ready system. The brief describes a JWT REST API and database-backed permission guard on every request; this project is a Streamlit monolith with UI-level role routing and SQLite service functions, not a separate JWT API. Before public/real-employee use, add a dedicated backend API and enforce authorization in every service; use a managed database, HTTPS, secret management, CSRF/session hardening, rate limiting, backups, complete before/after audit JSON, data retention controls, automated authorization tests, robust CSV import rollback/duplicate detection, true browser GPS, face identity matching/liveness, and end-date proration for leavers. The tax slabs are illustrative and must be reviewed by a qualified payroll professional before real payroll use.

## AI configuration

Set `AI_API_KEY` as an environment variable or hosting secret. The app sends the role and question to the configured OpenAI-compatible model and offers read-only tools. Never commit a real key. Without a key, simple policy/summary answers still work locally; other questions show a friendly fallback.

## Deployment

For a quick demo, push the project to a private/public Git repository and deploy with Streamlit Community Cloud, adding `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `AI_API_KEY`, and `AI_MODEL` under app secrets. SQLite on an ephemeral host may be lost during redeploy/restart, so use a persistent managed database for anything beyond a short demo. Never deploy with default credentials or real employee data before a security review.
