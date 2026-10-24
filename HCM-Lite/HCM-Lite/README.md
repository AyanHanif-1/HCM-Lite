
HCM Lite — AI-Assisted Human Capital Management System


Saylani Hackathon — October 24, 2026

• Venue: Zaitoon Ashraf IT Park, Karachi
• Evaluation Time: Designed for full validation and verification in under 10 minutes.

🛠 Tech Stack & Architecture

• Framework: Next.js 16 (App Router, React Server Components, Turbopack)
• Language: TypeScript 5 (Strict Mode, End-to-End Type Safety)
• Database ORM: Prisma 6.4 with zero-dependency local SQLite (file:./dev.db)
• Styling: Tailwind CSS & Lucide Icons (Dark Glassmorphic Enterprise UI)
• Authentication: JWT in HTTP-Only Cookies via jose & bcryptjs password hashing
• AI Engine: Dual-Mode Engine (Google Gemini 1.5 Flash API + Intelligent Deterministic Offline Synthesizer)
• Biometrics & Geolocation: Canvas Face/Presence Detection, Browser Geolocation API, and Haversine 150m Office Perimeter Verification

⚡ Quick Start Guide (Ready in < 2 Minutes)

bash
# 1. Clone the project repository
git clone <repo-url>
cd HCM-Lite

# 2. Install production dependencies
npm install

# 3. Provision clean SQLite Database (starts with 0 users)
npx prisma db push

# 4. Spin up the Development Server
npm run dev
Use code with caution.
Access the application locally at http://localhost:3000.

⚙ Environment Variables Setup (.env)

Configure your .env file in the project root using these keys:
env
# Database Connection (Zero-dependency SQLite for immediate local execution)
DATABASE_URL="file:./dev.db"

# JWT Authentication Secret (Must be 32+ characters)
JWT_SECRET="saylani-hackathon-2026-hcm-lite-secret-key-32-chars-long"

# Hosted LLM API Key (Optional)
# If provided, Google Gemini 1.5 Flash generates dynamic conversational text.
# If left blank, the built-in offline engine handles all tools, Roman Urdu parsing, and formulas locally!
AI_API_KEY=""

# Application Base URL
NEXT_PUBLIC_APP_URL="http://localhost:3000"
Use code with caution.

⏱ 5-Minute Live Demo Script for Judges

Execute these 5 sequential steps for a seamless, high-impact evaluation flow:

Step 1: Initialization Wizard (/setup)

1. Navigate to http://localhost:3000.
2. Because the database starts with Zero Pre-Loaded Data, the system automatically detects the missing administrator and routes you to /setup.
3. Input the deployment parameters:
	• Company: TechCorp Global
	• Office Coordinates: 24.8607, 67.0011 | Radius: 150m | Work Start: 09:00 AM | Grace Period: 15 min.
	• Admin Credentials: Email admin@techcorp.com, Password Admin@12345.
4. Click Initialize Enterprise Workspace.
	• This auto-provisions core departments (IT, HR, Sales, Finance) and standard leave categories (Annual 14, Sick 8, Casual 10, Unpaid).
	• The setup wizard then permanently locks (subsequent requests to /setup return a 403 Forbidden status).

Step 2: HR Provisioning & Bulk Data Ingestion (/admin/hr-management & /hr/employees)

1. Log into the Admin Dashboard and click HR Logins (/admin/hr-management).
2. Provision a new HR account: Email hr@techcorp.com, Temporary Password TempHR@12345.
3. Log out of the Admin account and sign back in using the hr@techcorp.com credentials.
4. Navigate to the Employees Directory (/hr/employees):
	• Manual Entry: Click Register Employee to add a record manually (Ali Khan, Basic: ₨ 100,000, Gross: ₨ 150,000).
	• Bulk CSV Import: Click Import CSV and paste or upload raw rows. The UI provides an interactive dry-run table featuring schema verification before execution.
	• Click Export CSV to confirm instant data generation.

Step 3: Self-Service Portal, Biometric Check-In & Smart Leaves

1. Log in with the newly generated Employee credentials.
2. Mandatory Security Force: The system catches the mustChangePassword: true flag, restricting dashboard access until the employee overwrites their temporary password.
3. Attendance Interface (/employee/attendance):
	• Biometric Camera Check-In (+10 Bonus Points): Click Camera Check-In. The live feed displays targeting crosshairs and real-time face detection indicators.
	• Click Simulate Face In/Out or use a live webcam to test authorization states.
	• Browser GPS coordinates are read and validated against the 150m Haversine workspace boundary.
	• Click Verify & Punch Attendance to lock the punch using an un-spoofable server timestamp.
4. Smart Leave Request Engine (/employee/leave):
	• Click Apply for Leave.
	• Inside the Smart Apply with AI prompt, type raw natural language or Roman Urdu: "Need next Monday and Tuesday off for sister's wedding" or "Kal bukhar ki wajah se chutti chahiye".
	• Click Auto-Fill. The AI parses the dates, maps the text to the correct category (CASUAL or SICK), and populates the fields.
	• Submit the form. The backend automatically ensures that weekends (Sat-Sun) and configured public holidays are skipped during deduction.

Step 4: Payroll Processing & Immutable Data Locking (/hr/payroll & /admin/payroll)

1. Log back in as HR (hr@techcorp.com) and open the Payroll Engine (/hr/payroll).
2. Click Generate Draft Payroll for the active month.
	• The calculation engine aggregates actual working days, computes per-day rates, subtracts attendance penalties (e.g., 3 lates = 0.5 day wage deduction), and applies progressive tax slabs (0% up to 35%).
	• The generation saves the status as a mutable DRAFT.
3. Log in as Admin (admin@techcorp.com) and load Finalize Payroll (/admin/payroll).
4. Click Finalize & Lock Payroll.
	• The status switches to FINALIZED, freezing the records. Future modification requests will drop with a 403 Forbidden or 422 Unprocessable Entity error.
5. Log back into the Employee portal to review and print the verified Payslip (/employee/payslips).

Step 5: AI Privacy Boundaries, Roman Urdu Processing & Security Audits

1. Trigger the floating AI Assistant using the sparkles component in the bottom-right corner of the interface.
2. Verify Financial Isolation Guardrail: Ask the assistant: "What is Ali's salary?" or "Tell me Sarah's pay".
	• System Result: The AI blocks the request instantly, returning: Access Denied: You do not have permission to view other employees' salary details. [AI-generated]
3. Verify Roman Urdu Semantic Processing (+10 Bonus Points):
	• Input: "Aaj kitne log chutti par hain?" -> Receives a live overview of today's out-of-office team members.
	• Input: "Der se aane wale employees ki list dikhao" -> Returns a list of the month's top late arrivals.
4. Verify Executive Summarization UI: On the Admin or HR entry dashboard, click Generate AI Summary to parse active KPIs into 3 to 5 actionable bullet points.
5. Inspect the Immutable Audit Trail (/admin/audit-logs): Review the structural log ledger showcasing absolute state updates alongside before/after JSON diffs for administrative actions.

🎯 Verified Functionality Matrix (M1 – M9)


#	Domain Module	Verified Business Logic / Technical Rule	Status
1	M1: Auth & Setup	First-Run check: Forced routing to /setup if admin count is 0	✅ Verified
2	M1: Auth & Setup	Permanent lock architecture on the /setup wizard post-initialization	✅ Verified
3	M1: Auth & Setup	Temporary password lifecycle & mandatory first-login password update	✅ Verified
4	M1: Auth & Setup	Strict server-side middleware route guards (ADMIN, HR, EMPLOYEE)	✅ Verified
5	M2: Org Setup	Workspace configuration: Geofence limits, shift starts, and grace rules	✅ Verified
6	M2: Org Setup	Full Department CRUD, structural Designations, and Holiday calendars	✅ Verified
7	M3: Employee Mgmt	Administrative panel for HR user creation with auto-generated credentials	✅ Verified
8	M3: Employee Mgmt	Comprehensive manual registration form with complete profile data validation	✅ Verified
9	M3: Employee Mgmt	Bulk CSV Import engine featuring a pre-flight dry-run diagnostic report	✅ Verified
10	M4: Attendance	Server-side time stamping to block client-side system clock spoofing	✅ Verified
11	M4: Attendance	Single check-in constraint per employee per day (duplicates return 409)	✅ Verified
12	M4: Attendance	Late arrival threshold calculation (> 15m) & Half-Day threshold (< 5.0h)	✅ Verified
13	M4: Attendance	Attendance dispute/correction flow routed to centralized HR Inbox	✅ Verified
14	M4: Attendance	Bonus (+10 Pts): Biometric webcam verification & Haversine formula GPS validation	✅ Verified
15	M5: Leave Mgmt	Leave allocation rules: Annual (14), Sick (8), Casual (10), Unpaid (∞)	✅ Verified
16	M5: Leave Mgmt	Automated schedule parser ignoring weekends (Sat-Sun) and active holidays	✅ Verified
17	M5: Leave Mgmt	Server-side calendar collision check & balance exhaustion guard (422)	✅ Verified
18	M5: Leave Mgmt	Self-service application workflow integrated with HR Approval Inbox	✅ Verified
19	M6: Payroll Lite	Compensation Structure: Gross = 1.5 × Basic (Basic 100%, HRA 40%, Medical 10%)	✅ Verified
20	M6: Payroll Lite	Per-day calculation, progressive late counts (3 lates = 0.5 day cut), and tax slabs	✅ Verified
21	M6: Payroll Lite	Multi-step lifecycle: HR initiates DRAFT status → Admin applies FINALIZED lock	✅ Verified
22	M6: Payroll Lite	Secure, printable customer payslips featuring employee ownership verification	✅ Verified
23	M7: Analytics	Server-isolated statistical reporting (Attendance %, Late %, Absenteeism)	✅ Verified
24	M8: AI Assistant	Contextual tools, salary data privacy isolation, Roman Urdu parsing (+10 Pts)	✅ Verified
25	M9: Comms & Audit	System broadcast announcements, push notifications, and JSON diff tracking	✅ Verified


🧮 Operational & Mathematical Formulas


Mathematical Target	Evaluated Equation / Calculation Metric
Gross Salary	Gross = 1.5 × Basic
Per Day Rate	Per Day Rate = Gross ÷ Total Calendar Working Days in Month
Monthly Deductions	(Absent + Unpaid + 0.5 × HalfDay + LatePenalty) × Per Day Rate
Late Arrival Penalty	Every accumulation of 3 late arrivals = 0.5 × Per Day Rate deduction
Tax Slabs (Annual)	0–600k (0%), 600k–1.2M (5%), 1.2M–2.4M (₨ 30k + 15%), 2.4M–3.6M (₨ 210k + 25%), > 3.6M (₨ 510k + 35%)
Attendance Rate	\(\frac{\text{Present} + \text{Late} + \text{Missing Checkout} + 0.5 \times \text{Half Day}}{\text{Total Active Workforce} - \text{Employees On Leave}} \times 100\%\)
Late Arrival %	\(\frac{\text{Late Days}}{\text{Present} + \text{Late}} \times 100\%\)
Absenteeism %	\(\frac{\text{Absent Days}}{\text{Expected Departmental Working Days}} \times 100\%\) (Aggregated by Department)


🛡 System Security & Privacy Guardrails

1. Data Confidentiality Insulation: The internal AI routing layer applies an immediate hard-stop if a regular EMPLOYEE queries the compensation data of another team member.
2. Zero Pre-Seeded Constraints: The environment provisions a clean state (User count: 0), ensuring evaluators can directly test the execution flow from the initial initialization onward.
3. Immutable Audit Trail: All administrative operations generate a persistent security record capturing Actor ID, role type, execution description, system IP, and explicit before/after database state mutations via JSON tracking.
4. Server Clock Reliance: All time calculations run exclusively against system server timestamps, preventing users from manipulating local device clocks to bypass attendance boundaries or modify payroll calculations.
