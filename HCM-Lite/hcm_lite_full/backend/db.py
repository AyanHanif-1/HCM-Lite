import os
import sqlite3
import hashlib
import hmac
import secrets
from pathlib import Path
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
DB_PATH = DATA / "hcm.db"
TZ = ZoneInfo("Asia/Karachi")

def now():
    return datetime.now(TZ).isoformat(timespec="seconds")

def conn():
    c = sqlite3.connect(DB_PATH, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def hash_password(password, salt=None):
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return salt.hex() + "$" + digest.hex()

def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 200_000).hex()
        return hmac.compare_digest(actual, digest_hex)
    except Exception:
        return False

def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('Admin','HR','Employee')),
          active INTEGER NOT NULL DEFAULT 1, must_change_password INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS departments(
          id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, designation TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS employees(
          id INTEGER PRIMARY KEY, employee_code TEXT UNIQUE NOT NULL, user_id INTEGER UNIQUE NOT NULL,
          name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, department TEXT DEFAULT '',
          designation TEXT DEFAULT '', join_date TEXT NOT NULL, basic_salary REAL NOT NULL,
          active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL,
          FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS attendance(
          id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL, attendance_date TEXT NOT NULL,
          check_in TEXT, check_out TEXT, status TEXT NOT NULL, source TEXT DEFAULT 'web',
          UNIQUE(employee_id, attendance_date),
          FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        CREATE TABLE IF NOT EXISTS leaves(
          id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL, leave_type TEXT NOT NULL,
          start_date TEXT NOT NULL, end_date TEXT NOT NULL, days INTEGER NOT NULL,
          reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
          decision_comment TEXT DEFAULT '', decided_by INTEGER, created_at TEXT NOT NULL,
          FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        CREATE TABLE IF NOT EXISTS payroll_runs(
          id INTEGER PRIMARY KEY, month TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
          created_by INTEGER NOT NULL, created_at TEXT NOT NULL, finalized_at TEXT
        );
        CREATE TABLE IF NOT EXISTS payslips(
          id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL, employee_id INTEGER NOT NULL,
          basic REAL NOT NULL, hra REAL NOT NULL, medical REAL NOT NULL,
          gross REAL NOT NULL, deductions REAL NOT NULL, net REAL NOT NULL,
          FOREIGN KEY(run_id) REFERENCES payroll_runs(id),
          FOREIGN KEY(employee_id) REFERENCES employees(id),
          UNIQUE(run_id, employee_id)
        );
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS announcements(
          id INTEGER PRIMARY KEY, author_id INTEGER NOT NULL, title TEXT NOT NULL,
          body TEXT NOT NULL, created_at TEXT NOT NULL,
          FOREIGN KEY(author_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS holidays(
          id INTEGER PRIMARY KEY, holiday_date TEXT UNIQUE NOT NULL, name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS correction_requests(
          id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL, attendance_date TEXT NOT NULL,
          requested_check_in TEXT DEFAULT '', requested_check_out TEXT DEFAULT '', reason TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending', decision_comment TEXT DEFAULT '', decided_by INTEGER,
          created_at TEXT NOT NULL, FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        CREATE TABLE IF NOT EXISTS notifications(
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
          read_at TEXT DEFAULT '', created_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS ai_logs(
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, question TEXT NOT NULL,
          answer_preview TEXT DEFAULT '', created_at TEXT NOT NULL,
          FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS audit_log(
          id INTEGER PRIMARY KEY, actor_id INTEGER, action TEXT NOT NULL,
          entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, created_at TEXT NOT NULL
        );
        """)
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('company_name','My Company')")
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('office_start','09:00')")
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('grace_minutes','15')")
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('weekend','Saturday,Sunday')")
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('leave_quota_annual','14')")
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('leave_quota_sick','8')")
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('leave_quota_casual','10')")
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('office_lat','')")
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('office_lon','')")
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('office_radius','150')")
        # Safe forward migrations for existing local demo databases.
        employee_cols = {r[1] for r in c.execute("PRAGMA table_info(employees)").fetchall()}
        if "phone" not in employee_cols: c.execute("ALTER TABLE employees ADD COLUMN phone TEXT DEFAULT ''")
        if "address" not in employee_cols: c.execute("ALTER TABLE employees ADD COLUMN address TEXT DEFAULT ''")

def create_admin_if_needed():
    email = os.getenv("ADMIN_EMAIL", "admin@hcm.local").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "Admin123!")
    with conn() as c:
        row = c.execute("SELECT id FROM users WHERE role='Admin' LIMIT 1").fetchone()
        if not row:
            c.execute("INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                      ("System Admin", email, hash_password(password), "Admin", now()))

def authenticate(email, password):
    with conn() as c:
        row = c.execute("SELECT * FROM users WHERE email=? AND active=1", (email,)).fetchone()
    if row and verify_password(password, row["password_hash"]):
        return row
    return None

def log_action(actor_id, action, entity_type, entity_id):
    with conn() as c:
        c.execute("INSERT INTO audit_log(actor_id,action,entity_type,entity_id,created_at) VALUES(?,?,?,?,?)",
                  (actor_id, action, entity_type, str(entity_id), now()))

def audit_logs():
    with conn() as c:
        return c.execute("""SELECT a.id,u.name AS actor,a.action,a.entity_type,a.entity_id,a.created_at
                            FROM audit_log a LEFT JOIN users u ON u.id=a.actor_id ORDER BY a.id DESC LIMIT 500""").fetchall()

def get_setting(key, default=""):
    with conn() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default

def set_setting(key, value):
    with conn() as c:
        c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (key, str(value)))

def list_departments():
    with conn() as c:
        return c.execute("SELECT * FROM departments ORDER BY name").fetchall()

def add_department(name, designation=""):
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO departments(name,designation) VALUES(?,?)", (name, designation))

def create_user(name, email, password, role):
    if not name or not email or role not in ("HR","Employee"):
        raise ValueError("Name, email and valid role are required.")
    try:
        with conn() as c:
            c.execute("INSERT INTO users(name,email,password_hash,role,must_change_password,created_at) VALUES(?,?,?,?,1,?)",
                      (name, email, hash_password(password), role, now()))
    except sqlite3.IntegrityError:
        raise ValueError("Email already exists.")

def list_users():
    with conn() as c:
        return c.execute("SELECT id,name,email,role,active,created_at FROM users ORDER BY id DESC").fetchall()

def user_by_id(user_id):
    with conn() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

def create_employee(code, name, email, dept, designation, join_date, basic, password):
    if not code or not name or not email or basic <= 0:
        raise ValueError("Employee code, name, email and positive salary are required.")
    try:
        with conn() as c:
            c.execute("INSERT INTO users(name,email,password_hash,role,must_change_password,created_at) VALUES(?,?,?,?,1,?)",
                      (name, email, hash_password(password), "Employee", now()))
            user_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            c.execute("""INSERT INTO employees(employee_code,user_id,name,email,department,designation,join_date,basic_salary,created_at)
                         VALUES(?,?,?,?,?,?,?,?,?)""",
                      (code, user_id, name, email, dept, designation, join_date, basic, now()))
    except sqlite3.IntegrityError:
        raise ValueError("Employee code or email already exists.")

def list_employees():
    with conn() as c:
        return c.execute("""SELECT id,employee_code,name,email,department,designation,join_date,basic_salary,active
                            FROM employees ORDER BY id DESC""").fetchall()

def get_employee_by_user(user_id):
    with conn() as c:
        return c.execute("SELECT * FROM employees WHERE user_id=? AND active=1", (user_id,)).fetchone()

def check_in(employee_id, source="web"):
    t = datetime.now(TZ)
    today = t.date().isoformat()
    start = datetime.strptime(get_setting("office_start", "09:00"), "%H:%M").time()
    grace = int(get_setting("grace_minutes", "15"))
    cutoff = (datetime.combine(t.date(), start) + timedelta(minutes=grace)).time()
    status = "present" if t.time().replace(tzinfo=None) <= cutoff else "late"
    with conn() as c:
        try:
            c.execute("INSERT INTO attendance(employee_id,attendance_date,check_in,status,source) VALUES(?,?,?,?,?)",
                      (employee_id, today, t.isoformat(timespec="seconds"), status, source))
        except sqlite3.IntegrityError:
            return False, "Attendance already exists for today."
    return True, f"Check-in saved at {t.strftime('%H:%M:%S')} ({status})."

def haversine_m(lat1, lon1, lat2, lon2):
    import math
    radius=6371000
    p1,p2=math.radians(float(lat1)),math.radians(float(lat2))
    dp=math.radians(float(lat2)-float(lat1)); dl=math.radians(float(lon2)-float(lon1))
    a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return radius*2*math.atan2(math.sqrt(a),math.sqrt(1-a))

def check_in_verified(employee_id, latitude, longitude, accuracy_m, face_count):
    if face_count != 1: return False, "Camera check rejected: exactly one face must be detected."
    try:
        if float(accuracy_m) > 100: return False, "Location accuracy is too low; try again outdoors."
        office_lat=get_setting("office_lat",""); office_lon=get_setting("office_lon","")
        if not office_lat or not office_lon: return False, "Admin must configure office latitude and longitude first."
        distance=haversine_m(latitude,longitude,office_lat,office_lon); radius=float(get_setting("office_radius","150"))
        if distance > radius: return False, f"Outside office geofence ({distance:.0f}m away; allowed {radius:.0f}m)."
    except Exception: return False, "Invalid location coordinates or accuracy."
    ok,msg=check_in(employee_id,source="camera_location_face_detected")
    if ok: return True, msg+" Location and face-detection checks passed; identity matching is not enabled in this demo."
    return ok,msg

def check_out(employee_id):
    t = datetime.now(TZ)
    with conn() as c:
        row = c.execute("SELECT id,check_out FROM attendance WHERE employee_id=? AND attendance_date=?",
                        (employee_id, t.date().isoformat())).fetchone()
        if not row:
            return False, "Check in first before checking out."
        if row["check_out"]:
            return False, "Check-out is already recorded."
        rec = c.execute("SELECT check_in FROM attendance WHERE id=?", (row["id"],)).fetchone()
        status = "present"
        if rec and rec["check_in"]:
            try:
                start_dt = datetime.fromisoformat(rec["check_in"])
                if (t - start_dt).total_seconds() < 5 * 3600: status = "half_day"
            except Exception: pass
        c.execute("UPDATE attendance SET check_out=?,status=CASE WHEN status='late' THEN 'late' WHEN ?='half_day' THEN 'half_day' ELSE status END WHERE id=?", (t.isoformat(timespec="seconds"), status, row["id"]))
    return True, f"Check-out saved at {t.strftime('%H:%M:%S')} ({status})."

def attendance_for_user(employee_id):
    with conn() as c:
        return c.execute("SELECT attendance_date,check_in,check_out,status,source FROM attendance WHERE employee_id=? ORDER BY attendance_date DESC LIMIT 90",
                         (employee_id,)).fetchall()

def attendance_all(limit=500):
    with conn() as c:
        return c.execute("""SELECT a.attendance_date,e.employee_code,e.name,e.department,a.check_in,a.check_out,a.status,a.source
                            FROM attendance a JOIN employees e ON e.id=a.employee_id
                            ORDER BY a.attendance_date DESC,a.check_in DESC LIMIT ?""", (limit,)).fetchall()

def workdays(start, end):
    d1, d2 = date.fromisoformat(start), date.fromisoformat(end)
    if d2 < d1:
        return 0
    weekend = set(x.strip() for x in get_setting("weekend", "Saturday,Sunday").split(",") if x.strip())
    count = 0
    d = d1
    while d <= d2:
        with conn() as c:
            holiday = c.execute("SELECT 1 FROM holidays WHERE holiday_date=?", (d.isoformat(),)).fetchone()
        if d.strftime("%A") not in weekend and not holiday:
            count += 1
        d += timedelta(days=1)
    return count

def submit_leave(employee_id, leave_type, start, end, reason):
    days = workdays(start, end)
    if date.fromisoformat(end) < date.fromisoformat(start):
        return False, "End date cannot be before start date."
    if days <= 0:
        return False, "The selected dates contain no working days."
    if not reason.strip():
        return False, "Please provide a reason."
    if leave_type not in ("annual", "sick", "casual", "unpaid"):
        return False, "Invalid leave type."
    quotas = {"annual": int(get_setting("leave_quota_annual", "14")), "sick": int(get_setting("leave_quota_sick", "8")), "casual": int(get_setting("leave_quota_casual", "10"))}
    if leave_type != "unpaid":
        with conn() as c:
            used = c.execute("SELECT COALESCE(SUM(days),0) n FROM leaves WHERE employee_id=? AND leave_type=? AND status IN ('pending','approved')", (employee_id, leave_type)).fetchone()["n"]
        if int(used) + days > quotas[leave_type]:
            return False, f"This request exceeds your {leave_type} leave balance ({max(0, quotas[leave_type]-int(used))} day(s) available)."
    with conn() as c:
        overlap = c.execute("""SELECT id FROM leaves WHERE employee_id=? AND status IN ('pending','approved')
          AND NOT(end_date < ? OR start_date > ?)""", (employee_id, start, end)).fetchone()
        if overlap:
            return False, "This request overlaps another pending or approved leave."
        c.execute("""INSERT INTO leaves(employee_id,leave_type,start_date,end_date,days,reason,status,created_at)
                     VALUES(?,?,?,?,?,?, 'pending', ?)""",
                  (employee_id, leave_type, start, end, days, reason.strip(), now()))
    return True, f"Leave request submitted for {days} working day(s)."

def list_leaves(status=None, employee_id=None, limit=500):
    sql = """SELECT l.*,e.name AS employee_name,e.employee_code,e.department
             FROM leaves l JOIN employees e ON e.id=l.employee_id WHERE 1=1"""
    args = []
    if status:
        sql += " AND l.status=?"; args.append(status)
    if employee_id:
        sql += " AND l.employee_id=?"; args.append(employee_id)
    sql += " ORDER BY l.id DESC LIMIT ?"; args.append(limit)
    with conn() as c:
        return c.execute(sql, args).fetchall()

def decide_leave(leave_id, actor_id, status, comment):
    if status not in ("approved","rejected"):
        return False, "Invalid decision."
    with conn() as c:
        row = c.execute("SELECT status,employee_id FROM leaves WHERE id=?", (leave_id,)).fetchone()
        if not row or row["status"] != "pending":
            return False, "Request not found or already decided."
        c.execute("UPDATE leaves SET status=?,decision_comment=?,decided_by=? WHERE id=?",
                  (status, comment, actor_id, leave_id))
        target=c.execute("SELECT user_id FROM employees WHERE id=?",(row["employee_id"],)).fetchone()
        if target:
            c.execute("INSERT INTO notifications(user_id,title,body,created_at) VALUES(?,?,?,?)",(target["user_id"],"Leave request update",f"Your leave request #{leave_id} was {status}. {comment}",now()))
    return True, f"Leave request {status}."

def leave_balances(employee_id):
    quotas = {
        "annual": int(get_setting("leave_quota_annual", "14")),
        "sick": int(get_setting("leave_quota_sick", "8")),
        "casual": int(get_setting("leave_quota_casual", "10")),
        "unpaid": 999999,
    }
    with conn() as c:
        rows = c.execute("SELECT leave_type,COALESCE(SUM(days),0) used FROM leaves WHERE employee_id=? AND status='approved' GROUP BY leave_type", (employee_id,)).fetchall()
    used = {r["leave_type"]: int(r["used"]) for r in rows}
    return {kind: {"quota": quota, "used": used.get(kind, 0), "remaining": max(0, quota-used.get(kind, 0)) if kind != "unpaid" else quota}
            for kind, quota in quotas.items()}

def leave_balance(employee_id):
    return sum(v["remaining"] for k,v in leave_balances(employee_id).items() if k != "unpaid")

def list_announcements():
    with conn() as c:
        return c.execute("""SELECT a.*,u.name AS author_name FROM announcements a
                            JOIN users u ON u.id=a.author_id ORDER BY a.id DESC LIMIT 100""").fetchall()

def add_announcement(author_id, title, body):
    with conn() as c:
        c.execute("INSERT INTO announcements(author_id,title,body,created_at) VALUES(?,?,?,?)", (author_id, title, body, now()))
        c.execute("INSERT INTO notifications(user_id,title,body,created_at) SELECT id,?, ?, ? FROM users WHERE active=1", ("Announcement: "+title, body, now()))

def tax_annual(annual_gross):
    # Illustrative tax slabs supplied by the challenge brief; not tax advice.
    x = max(0.0, float(annual_gross))
    if x <= 600000: return 0.0
    if x <= 1200000: return (x-600000)*0.05
    if x <= 2400000: return 30000+(x-1200000)*0.15
    if x <= 3600000: return 210000+(x-2400000)*0.25
    return 510000+(x-3600000)*0.35

def payroll_preview(month):
    try:
        year, mon = map(int, month.split("-"))
        if mon < 1 or mon > 12: raise ValueError()
        first = date(year, mon, 1)
        last = date(year + (mon == 12), (mon % 12) + 1, 1) - timedelta(days=1)
    except Exception:
        raise ValueError("Month must be in YYYY-MM format.")
    days_total = workdays(first.isoformat(), last.isoformat())
    if days_total <= 0: days_total = 1
    with conn() as c:
        emps = c.execute("SELECT * FROM employees WHERE active=1").fetchall()
        result = []
        for e in emps:
            join_date = date.fromisoformat(e["join_date"])
            effective_start = max(first, join_date)
            effective_days = workdays(effective_start.isoformat(), last.isoformat()) if effective_start <= last else 0
            basic = float(e["basic_salary"])
            hra, medical = basic * .4, basic * .1
            full_gross = basic + hra + medical
            prorate = min(1.0, effective_days / days_total) if effective_days else 0.0
            gross = full_gross * prorate
            per_day = full_gross / days_total
            att = c.execute("SELECT attendance_date,status,check_in,check_out FROM attendance WHERE employee_id=? AND attendance_date BETWEEN ? AND ?", (e["id"], max(first, join_date).isoformat(), last.isoformat())).fetchall()
            att_by_day = {r["attendance_date"]: r for r in att}
            unpaid_rows = c.execute("SELECT start_date,end_date,days FROM leaves WHERE employee_id=? AND status='approved' AND leave_type='unpaid' AND NOT(end_date<? OR start_date>?)", (e["id"], max(first, join_date).isoformat(), last.isoformat())).fetchall()
            unpaid_dates = set()
            for lr in unpaid_rows:
                d = max(date.fromisoformat(lr["start_date"]), max(first, join_date)); en = min(date.fromisoformat(lr["end_date"]), last)
                while d <= en:
                    if workdays(d.isoformat(), d.isoformat()): unpaid_dates.add(d.isoformat())
                    d += timedelta(days=1)
            absent_days = half_days = missing_checkout = 0
            d = max(first, join_date)
            while d <= last:
                if workdays(d.isoformat(), d.isoformat()):
                    ds = d.isoformat(); rec = att_by_day.get(ds)
                    if ds in unpaid_dates:
                        pass
                    elif rec is None:
                        # Approved paid leave covers the day; otherwise absence is deducted.
                        approved = c.execute("SELECT 1 FROM leaves WHERE employee_id=? AND status='approved' AND leave_type!='unpaid' AND start_date<=? AND end_date>=?", (e["id"], ds, ds)).fetchone()
                        if not approved: absent_days += 1
                    else:
                        if rec["status"] == "absent":
                            approved = c.execute("SELECT 1 FROM leaves WHERE employee_id=? AND status='approved' AND leave_type!='unpaid' AND start_date<=? AND end_date>=?", (e["id"], ds, ds)).fetchone()
                            if not approved: absent_days += 1
                        elif rec["status"] == "half_day": half_days += 1
                        if rec["check_in"] and not rec["check_out"]: missing_checkout += 1
                d += timedelta(days=1)
            unpaid_days = len(unpaid_dates)
            attendance_deduction = per_day * (absent_days + unpaid_days + 0.5*half_days)
            monthly_tax = tax_annual(full_gross*12)/12 * prorate
            deductions = min(gross, attendance_deduction + monthly_tax)
            result.append({"employee_id":e["id"],"employee_code":e["employee_code"],"name":e["name"],"department":e["department"],
                           "basic":basic*prorate,"hra":hra*prorate,"medical":medical*prorate,"gross":gross,
                           "absent_days":absent_days,"unpaid_days":unpaid_days,"half_days":half_days,"tax":monthly_tax,
                           "deductions":deductions,"net":max(0,gross-deductions)})
        return result

def create_payroll_run(month, actor_id):
    preview = payroll_preview(month)
    with conn() as c:
        existing = c.execute("SELECT id FROM payroll_runs WHERE month=?", (month,)).fetchone()
        if existing:
            raise ValueError("A payroll run already exists for this month. It cannot be duplicated.")
        c.execute("INSERT INTO payroll_runs(month,status,created_by,created_at) VALUES(?, 'draft', ?, ?)", (month, actor_id, now()))
        run_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        for r in preview:
            c.execute("INSERT INTO payslips(run_id,employee_id,basic,hra,medical,gross,deductions,net) VALUES(?,?,?,?,?,?,?,?)",
                      (run_id,r["employee_id"],r["basic"],r["hra"],r["medical"],r["gross"],r["deductions"],r["net"]))
        return run_id

def list_payroll(employee_id=None):
    with conn() as c:
        if employee_id:
            return c.execute("""SELECT r.month,r.status,p.basic,p.hra,p.medical,p.gross,p.deductions,p.net
                FROM payslips p JOIN payroll_runs r ON r.id=p.run_id
                WHERE p.employee_id=? ORDER BY r.month DESC""", (employee_id,)).fetchall()
        return c.execute("SELECT id,month,status,created_at,finalized_at FROM payroll_runs ORDER BY id DESC").fetchall()

def finalize_payroll(run_id, actor_id):
    with conn() as c:
        row = c.execute("SELECT status FROM payroll_runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            return False, "Payroll run not found."
        if row["status"] != "draft":
            return False, "Only draft payroll can be finalized."
        c.execute("UPDATE payroll_runs SET status='finalized',finalized_at=? WHERE id=?", (now(), run_id))
    return True, "Payroll finalized and locked."

def get_dashboard_stats():
    today = date.today().isoformat()
    with conn() as c:
        active = c.execute("SELECT COUNT(*) n FROM employees WHERE active=1").fetchone()["n"]
        present = c.execute("SELECT COUNT(*) n FROM attendance WHERE attendance_date=? AND status='present'", (today,)).fetchone()["n"]
        late = c.execute("SELECT COUNT(*) n FROM attendance WHERE attendance_date=? AND status='late'", (today,)).fetchone()["n"]
        on_leave = c.execute("SELECT COUNT(DISTINCT employee_id) n FROM leaves WHERE status='approved' AND start_date<=? AND end_date>=?", (today,today)).fetchone()["n"]
        pending = c.execute("SELECT COUNT(*) n FROM leaves WHERE status='pending'").fetchone()["n"]
    return {"Active employees":active, "Present today":present, "On leave":on_leave, "Late today":late, "Pending leave":pending}

def change_password(user_id, old, new):
    if len(new) < 8:
        return False, "New password must be at least 8 characters."
    with conn() as c:
        row = c.execute("SELECT password_hash FROM users WHERE id=?", (user_id,)).fetchone()
        if not row or not verify_password(old, row["password_hash"]):
            return False, "Current password is incorrect."
        c.execute("UPDATE users SET password_hash=?,must_change_password=0 WHERE id=?", (hash_password(new), user_id))
    return True, "Password changed."


def list_holidays():
    with conn() as c:
        return c.execute("SELECT * FROM holidays ORDER BY holiday_date").fetchall()

def add_holiday(holiday_date, name):
    if not name.strip(): raise ValueError("Holiday name is required.")
    try:
        with conn() as c: c.execute("INSERT INTO holidays(holiday_date,name) VALUES(?,?)", (holiday_date,name.strip()))
    except sqlite3.IntegrityError: raise ValueError("A holiday already exists on that date.")

def remove_holiday(holiday_id):
    with conn() as c: c.execute("DELETE FROM holidays WHERE id=?", (holiday_id,))

def update_employee_profile(employee_id, department, designation, phone, address):
    with conn() as c:
        c.execute("UPDATE employees SET department=?,designation=?,phone=?,address=? WHERE id=?", (department,designation,phone,address,employee_id))

def request_attendance_correction(employee_id, attendance_date, requested_check_in, requested_check_out, reason):
    if not reason.strip(): return False,"Please explain why a correction is needed."
    with conn() as c:
        c.execute("INSERT INTO correction_requests(employee_id,attendance_date,requested_check_in,requested_check_out,reason,status,created_at) VALUES(?,?,?,?,?,'pending',?)",
                  (employee_id,attendance_date,requested_check_in,requested_check_out,reason.strip(),now()))
    return True,"Correction request submitted to HR."

def list_corrections(status=None, employee_id=None):
    sql="SELECT cr.*,e.name employee_name,e.employee_code FROM correction_requests cr JOIN employees e ON e.id=cr.employee_id WHERE 1=1"; args=[]
    if status: sql+=" AND cr.status=?"; args.append(status)
    if employee_id: sql+=" AND cr.employee_id=?"; args.append(employee_id)
    sql+=" ORDER BY cr.id DESC"
    with conn() as c: return c.execute(sql,args).fetchall()

def decide_correction(correction_id, actor_id, approve, comment=''):
    with conn() as c:
        row=c.execute("SELECT * FROM correction_requests WHERE id=? AND status='pending'",(correction_id,)).fetchone()
        if not row: return False,"Correction request not found or already decided."
        status='approved' if approve else 'rejected'
        if approve:
            d=row['attendance_date']; existing=c.execute("SELECT id FROM attendance WHERE employee_id=? AND attendance_date=?",(row['employee_id'],d)).fetchone()
            if existing:
                c.execute("UPDATE attendance SET check_in=COALESCE(NULLIF(?,''),check_in),check_out=COALESCE(NULLIF(?,''),check_out),source='hr_correction' WHERE id=?",(row['requested_check_in'],row['requested_check_out'],existing['id']))
            else:
                cin=row['requested_check_in'] or None
                c.execute("INSERT INTO attendance(employee_id,attendance_date,check_in,check_out,status,source) VALUES(?,?,?,?,?,?)",(row['employee_id'],d,cin,row['requested_check_out'] or None,'present','hr_correction'))
        c.execute("UPDATE correction_requests SET status=?,decision_comment=?,decided_by=? WHERE id=?",(status,comment,actor_id,correction_id))
    return True, f"Correction {status}."

def employee_by_id(employee_id):
    with conn() as c: return c.execute("SELECT * FROM employees WHERE id=?",(employee_id,)).fetchone()

def get_payslip_details(employee_id, month):
    with conn() as c:
        return c.execute("SELECT e.employee_code,e.name,e.department,e.designation,e.email,r.month,r.status,p.* FROM payslips p JOIN payroll_runs r ON r.id=p.run_id JOIN employees e ON e.id=p.employee_id WHERE p.employee_id=? AND r.month=?",(employee_id,month)).fetchone()

def mark_absent_for_date(day_iso):
    # Materializes absent rows for active employees who were employed, on a working day, and not on approved leave.
    if not workdays(day_iso,day_iso): return 0
    added=0
    with conn() as c:
        employees=c.execute("SELECT id,join_date FROM employees WHERE active=1").fetchall()
        for e in employees:
            if e['join_date'] > day_iso: continue
            exists=c.execute("SELECT 1 FROM attendance WHERE employee_id=? AND attendance_date=?",(e['id'],day_iso)).fetchone()
            leave=c.execute("SELECT 1 FROM leaves WHERE employee_id=? AND status='approved' AND start_date<=? AND end_date>=?",(e['id'],day_iso,day_iso)).fetchone()
            if not exists and not leave:
                c.execute("INSERT INTO attendance(employee_id,attendance_date,status,source) VALUES(?,?, 'absent','system')",(e['id'],day_iso)); added+=1
    return added

def all_employees_export_rows():
    with conn() as c: return c.execute("SELECT employee_code,name,email,department,designation,join_date,basic_salary,active FROM employees ORDER BY employee_code").fetchall()

def employee_email_exists(email):
    with conn() as c: return c.execute("SELECT 1 FROM users WHERE email=?",(email.strip().lower(),)).fetchone() is not None

def set_user_active(user_id, active):
    with conn() as c:
        row=c.execute("SELECT role FROM users WHERE id=?",(user_id,)).fetchone()
        if not row or row["role"]=="Admin": return False,"Admin account cannot be deactivated here."
        c.execute("UPDATE users SET active=? WHERE id=?",(1 if active else 0,user_id))
        if row["role"]=="Employee": c.execute("UPDATE employees SET active=? WHERE user_id=?",(1 if active else 0,user_id))
    return True,"Account status updated."

def reset_user_password(user_id, temporary_password):
    if len(temporary_password)<8: return False,"Temporary password must be at least 8 characters."
    with conn() as c:
        row=c.execute("SELECT role FROM users WHERE id=?",(user_id,)).fetchone()
        if not row or row["role"]=="Admin": return False,"Cannot reset this account here."
        c.execute("UPDATE users SET password_hash=?,must_change_password=1 WHERE id=?",(hash_password(temporary_password),user_id))
    return True,"Temporary password set. The user must change it after signing in."

def update_employee_details(employee_id, department, designation, basic_salary, active=1):
    if float(basic_salary) <= 0: return False,"Salary must be greater than zero."
    with conn() as c:
        c.execute("UPDATE employees SET department=?,designation=?,basic_salary=?,active=? WHERE id=?",(department,designation,float(basic_salary),1 if active else 0,employee_id))
        c.execute("UPDATE users SET active=? WHERE id=(SELECT user_id FROM employees WHERE id=?)",(1 if active else 0,employee_id))
    return True,"Employee details updated."

def cancel_leave(leave_id, employee_id):
    with conn() as c:
        row=c.execute("SELECT status FROM leaves WHERE id=? AND employee_id=?",(leave_id,employee_id)).fetchone()
        if not row: return False,"Leave request not found."
        if row["status"]!="pending": return False,"Only pending leave requests can be cancelled."
        c.execute("UPDATE leaves SET status='cancelled' WHERE id=?",(leave_id,))
    return True,"Leave request cancelled."


def list_notifications(user_id):
    with conn() as c:
        return c.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 100",(user_id,)).fetchall()

def mark_notification_read(notification_id, user_id):
    with conn() as c:
        c.execute("UPDATE notifications SET read_at=? WHERE id=? AND user_id=?",(now(),notification_id,user_id))


def log_ai_call(user_id, question, answer):
    with conn() as c:
        c.execute("INSERT INTO ai_logs(user_id,question,answer_preview,created_at) VALUES(?,?,?,?)",(user_id,question[:1000],answer[:500],now()))

def list_ai_logs(limit=500):
    with conn() as c:
        return c.execute("SELECT a.id,u.name AS user_name,u.role,a.question,a.answer_preview,a.created_at FROM ai_logs a JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT ?",(limit,)).fetchall()

def payroll_summary_data(employee_id=None):
    with conn() as c:
        if employee_id:
            return c.execute("SELECT r.month,r.status,COUNT(p.id) employee_count,COALESCE(SUM(p.gross),0) gross_total,COALESCE(SUM(p.deductions),0) deductions_total,COALESCE(SUM(p.net),0) net_total FROM payroll_runs r JOIN payslips p ON p.run_id=r.id WHERE p.employee_id=? GROUP BY r.id ORDER BY r.month DESC",(employee_id,)).fetchall()
        return c.execute("SELECT r.month,r.status,COUNT(p.id) employee_count,COALESCE(SUM(p.gross),0) gross_total,COALESCE(SUM(p.deductions),0) deductions_total,COALESCE(SUM(p.net),0) net_total FROM payroll_runs r LEFT JOIN payslips p ON p.run_id=r.id GROUP BY r.id ORDER BY r.month DESC").fetchall()
