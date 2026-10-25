import streamlit as st
import pandas as pd
from datetime import date, datetime, time
from pathlib import Path
from backend.db import (
    init_db, create_admin_if_needed, authenticate, log_action, get_setting,
    set_setting, list_departments, add_department, list_employees, create_employee,
    get_employee_by_user, check_in, check_out, attendance_for_user, attendance_all,
    submit_leave, list_leaves, decide_leave, leave_balance, list_users,
    create_user, list_announcements, add_announcement, payroll_preview,
    create_payroll_run, finalize_payroll, list_payroll, get_dashboard_stats,
    change_password, user_by_id, leave_balances, list_holidays, add_holiday, remove_holiday,
    request_attendance_correction, list_corrections, decide_correction, update_employee_profile,
    employee_by_id, get_payslip_details, all_employees_export_rows, mark_absent_for_date,
    audit_logs, get_dashboard_stats, check_in_verified, set_user_active, reset_user_password,
    update_employee_details, cancel_leave, list_notifications, mark_notification_read, log_ai_call, list_ai_logs,
    payroll_summary_data
)

st.set_page_config(page_title="HCM Lite", page_icon="🏢", layout="wide")
init_db()
create_admin_if_needed()

def rerun():
    st.rerun()

def login_screen():
    st.title("HCM Lite")
    st.caption("AI-assisted Human Capital Management · Admin / HR / Employee")
    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")
    if submitted:
        user = authenticate(email.strip().lower(), password)
        if user:
            st.session_state.user = dict(user)
            st.success("Login successful.")
            rerun()
        else:
            st.error("Invalid email or password.")
    st.info("First run: configure ADMIN_EMAIL and ADMIN_PASSWORD environment variables, then sign in. If unset, local demo admin is admin@hcm.local / Admin123! — change it immediately.")
    st.caption("This starter is intended for local demo/testing. Configure secrets and persistent storage before public deployment.")

if "user" not in st.session_state:
    login_screen()
    st.stop()

user = st.session_state.user
role = user["role"]
st.sidebar.title("HCM Lite")
st.sidebar.write(f"**{user['name']}**")
st.sidebar.caption(f"Role: {role}")
normal_menu = (
    ["Dashboard", "Company Setup", "Departments & Holidays", "User Accounts", "Employees", "Attendance", "Attendance Corrections", "Leave Management", "Payroll", "Analytics", "AI Assistant", "Announcements", "Audit Log", "Change Password"]
    if role == "Admin" else
    ["Dashboard", "Employees", "Attendance", "Attendance Corrections", "Leave Management", "Payroll", "Analytics", "AI Assistant", "Announcements", "Change Password"]
    if role == "HR" else
    ["My Dashboard", "My Attendance", "My Leave", "My Payslips", "My Profile", "AI Assistant", "Announcements", "Change Password"]
)
if user.get("must_change_password", 0):
    st.warning("Your account has a temporary password. Change it before accessing the system.")
    menu_options=["Change Password"]
else:
    menu_options=normal_menu
page = st.sidebar.radio("Menu", menu_options)
if st.sidebar.button("Log out"):
    log_action(user["id"], "logout", "user", str(user["id"]))
    del st.session_state.user
    rerun()

def can_admin():
    return role == "Admin"

def can_hr():
    return role in ("Admin", "HR")

def show_table(rows):
    if rows:
        st.dataframe(pd.DataFrame([dict(r) for r in rows]), use_container_width=True, hide_index=True)
    else:
        st.info("No records yet.")

if page in ("Dashboard", "My Dashboard"):
    st.title("Dashboard")
    if role == "Employee":
        emp = get_employee_by_user(user["id"])
        if emp:
            a, b, c = st.columns(3)
            a.metric("Employee ID", emp["employee_code"])
            b.metric("Department", emp["department"] or "—")
            c.metric("Leave balance", leave_balance(emp["id"]))
            st.subheader("My recent attendance")
            show_table(attendance_for_user(emp["id"]))
        else:
            st.warning("Your employee profile has not been linked yet. Contact HR.")
    else:
        stats = get_dashboard_stats()
        cols = st.columns(5)
        for col, (label, value) in zip(cols, stats.items()):
            col.metric(label, value)
        st.subheader("Recent attendance")
        show_table(attendance_all(limit=20))
        st.subheader("Recent leave requests")
        show_table(list_leaves(limit=10))

elif page == "Company Setup" and can_admin():
    st.title("Company Setup")
    with st.form("company"):
        name = st.text_input("Company name", get_setting("company_name", "My Company"))
        start = st.time_input("Office start time", time(9, 0))
        grace = st.number_input("Grace period (minutes)", 0, 120, int(get_setting("grace_minutes", "15")))
        weekend = st.multiselect("Weekend", ["Saturday", "Sunday"], default=["Saturday", "Sunday"])
        lat = st.text_input("Office latitude (optional)", get_setting("office_lat", ""))
        lon = st.text_input("Office longitude (optional)", get_setting("office_lon", ""))
        radius = st.number_input("Office radius (metres)", 50, 5000, int(get_setting("office_radius", "150")))
        if st.form_submit_button("Save company settings"):
            set_setting("company_name", name)
            set_setting("office_start", start.strftime("%H:%M"))
            set_setting("grace_minutes", str(grace))
            set_setting("weekend", ",".join(weekend))
            set_setting("office_lat", lat)
            set_setting("office_lon", lon)
            set_setting("office_radius", str(radius))
            log_action(user["id"], "update_company_settings", "settings", "company")
            st.success("Settings saved.")

elif page in ("Departments", "Departments & Holidays") and can_admin():
    st.title("Departments, designations & holidays")
    with st.form("add_dept"):
        dept = st.text_input("Department name")
        designation = st.text_input("Designation")
        if st.form_submit_button("Add"):
            if dept.strip():
                add_department(dept.strip(), designation.strip())
                log_action(user["id"], "create_department", "department", dept)
                st.success("Department added.")
    show_table(list_departments())
    st.subheader("Public holidays")
    with st.form("add_holiday"):
        holiday_date = st.date_input("Holiday date", value=date.today())
        holiday_name = st.text_input("Holiday name")
        if st.form_submit_button("Add holiday"):
            try:
                add_holiday(holiday_date.isoformat(), holiday_name)
                log_action(user["id"], "add_holiday", "holiday", holiday_date.isoformat())
                st.success("Holiday added.")
            except ValueError as e: st.error(str(e))
    holidays = list_holidays()
    show_table(holidays)
    if holidays:
        holiday_options = {f"{h['holiday_date']} — {h['name']}": h for h in holidays}
        selected_holiday = st.selectbox("Remove holiday", list(holiday_options))
        if st.button("Remove selected holiday"):
            remove_holiday(holiday_options[selected_holiday]["id"]); st.success("Holiday removed."); rerun()
    st.subheader("Leave quota rules")
    with st.form("quota_rules"):
        annual_q = st.number_input("Annual leave quota", min_value=0, max_value=365, value=int(get_setting("leave_quota_annual", "14")))
        sick_q = st.number_input("Sick leave quota", min_value=0, max_value=365, value=int(get_setting("leave_quota_sick", "8")))
        casual_q = st.number_input("Casual leave quota", min_value=0, max_value=365, value=int(get_setting("leave_quota_casual", "10")))
        if st.form_submit_button("Save quotas"):
            set_setting("leave_quota_annual", annual_q); set_setting("leave_quota_sick", sick_q); set_setting("leave_quota_casual", casual_q)
            log_action(user["id"], "update_leave_quotas", "settings", "leave_quotas"); st.success("Leave quotas saved.")

elif page == "User Accounts" and can_admin():
    st.title("Create HR or Employee login")
    with st.form("create_user"):
        name = st.text_input("Full name")
        email = st.text_input("Email")
        new_role = st.selectbox("Role", ["HR"])
        password = st.text_input("Temporary password", type="password")
        if st.form_submit_button("Create account"):
            try:
                create_user(name.strip(), email.strip().lower(), password, new_role)
                log_action(user["id"], "create_user", "user", email)
                st.success("Account created.")
            except ValueError as e:
                st.error(str(e))
    users_rows=list_users()
    show_table(users_rows)
    manageable=[r for r in users_rows if r["role"]!="Admin"]
    if manageable:
        account_map={f"#{r['id']} · {r['name']} · {r['email']} · {r['role']} · {'active' if r['active'] else 'inactive'}":r for r in manageable}
        selected_account=st.selectbox("Manage account",list(account_map))
        target=account_map[selected_account]
        if st.button("Deactivate account" if target["active"] else "Reactivate account"):
            ok,msg=set_user_active(target["id"],not bool(target["active"]))
            log_action(user["id"],"change_account_status","user",target["id"]); (st.success if ok else st.error)(msg); rerun()
        with st.form("reset_password_form"):
            temp_pw=st.text_input("New temporary password (8+ chars)",type="password")
            if st.form_submit_button("Reset password"):
                ok,msg=reset_user_password(target["id"],temp_pw)
                log_action(user["id"],"reset_password","user",target["id"]); (st.success if ok else st.error)(msg)

elif page == "Employees":
    st.title("Employee Directory")
    if can_hr():
        departments = [r["name"] for r in list_departments()]
        with st.form("employee"):
            code = st.text_input("Employee code")
            name = st.text_input("Full name")
            email = st.text_input("Work email")
            dept = st.selectbox("Department", [""] + departments)
            designation = st.text_input("Designation")
            join_date = st.date_input("Joining date", value=date.today())
            basic = st.number_input("Monthly basic salary (PKR)", min_value=0.0, value=50000.0, step=5000.0)
            temp_password = st.text_input("Temporary login password", type="password")
            if st.form_submit_button("Register employee"):
                try:
                    create_employee(code.strip(), name.strip(), email.strip().lower(), dept, designation, join_date.isoformat(), basic, temp_password)
                    log_action(user["id"], "create_employee", "employee", code)
                    st.success("Employee and login created. Employee should change the password.")
                except ValueError as e:
                    st.error(str(e))
    employee_rows = list_employees()
    show_table(employee_rows)
    if can_hr():
        st.subheader("Edit employee job details")
        all_emp=list_employees()
        if all_emp:
            emp_opts={f"{r['employee_code']} · {r['name']} · {r['email']}":r for r in all_emp}
            chosen_emp=st.selectbox("Employee to edit",list(emp_opts))
            selected_emp=emp_opts[chosen_emp]
            dept_names=[r["name"] for r in list_departments()]
            with st.form("edit_employee_form"):
                edit_dept=st.selectbox("Department",[""]+dept_names,index=([""]+dept_names).index(selected_emp["department"] or "") if (selected_emp["department"] or "") in [""]+dept_names else 0)
                edit_designation=st.text_input("Designation",selected_emp["designation"] or "")
                edit_salary=st.number_input("Basic salary (PKR)",min_value=1.0,value=float(selected_emp["basic_salary"]),step=1000.0)
                edit_active=st.checkbox("Employee active",value=bool(selected_emp["active"]))
                if st.form_submit_button("Save employee details"):
                    ok,msg=update_employee_details(selected_emp["id"],edit_dept,edit_designation,edit_salary,edit_active)
                    log_action(user["id"],"update_employee_details","employee",selected_emp["id"]); (st.success if ok else st.error)(msg)
        st.subheader("CSV export / import")
        export_rows = [dict(r) for r in all_employees_export_rows()]
        csv_bytes = pd.DataFrame(export_rows).to_csv(index=False).encode("utf-8") if export_rows else b"employee_code,name,email,department,designation,join_date,basic_salary,active\n"
        st.download_button("Download employee CSV", csv_bytes, "employees.csv", "text/csv")
        upload = st.file_uploader("Import employees CSV (dry run first)", type=["csv"])
        if upload:
            try:
                incoming = pd.read_csv(upload).fillna("")
                required = ["employee_code","name","email","department","designation","join_date","basic_salary","temporary_password"]
                issues=[]
                seen_codes=set(); seen_emails=set()
                known_depts={r["name"] for r in list_departments()}
                for ix, row in incoming.iterrows():
                    row_no=ix+2
                    for field in required:
                        if field not in incoming.columns or not str(row.get(field, "")).strip(): issues.append({"row":row_no,"field":field,"reason":"Required field missing"})
                    email=str(row.get("email","")).strip().lower(); code=str(row.get("employee_code","")).strip()
                    if "email" in incoming.columns and ("@" not in email or "." not in email.split("@")[-1]): issues.append({"row":row_no,"field":"email","reason":"Invalid email"})
                    if code in seen_codes: issues.append({"row":row_no,"field":"employee_code","reason":"Duplicate code in CSV"})
                    if email in seen_emails: issues.append({"row":row_no,"field":"email","reason":"Duplicate email in CSV"})
                    seen_codes.add(code); seen_emails.add(email)
                    existing_codes={str(r["employee_code"]) for r in list_employees()}
                    existing_emails={str(r["email"]).lower() for r in list_employees()}
                    if code in existing_codes: issues.append({"row":row_no,"field":"employee_code","reason":"Code already exists in database"})
                    if email in existing_emails: issues.append({"row":row_no,"field":"email","reason":"Email already exists in database"})
                    dept=str(row.get("department","")).strip()
                    if dept and dept not in known_depts: issues.append({"row":row_no,"field":"department","reason":"Unknown department; create it first"})
                    try:
                        if float(row.get("basic_salary",0)) <= 0: issues.append({"row":row_no,"field":"basic_salary","reason":"Must be > 0"})
                    except Exception: issues.append({"row":row_no,"field":"basic_salary","reason":"Must be numeric"})
                    try: date.fromisoformat(str(row.get("join_date","")))
                    except Exception: issues.append({"row":row_no,"field":"join_date","reason":"Use YYYY-MM-DD"})
                if issues: st.warning(f"Dry run found {len(issues)} issue(s); no records imported."); show_table(issues)
                elif st.button("Import validated rows", type="primary"):
                    created=0
                    for _, row in incoming.iterrows():
                        create_employee(str(row.employee_code).strip(),str(row.name).strip(),str(row.email).strip().lower(),str(row.department).strip(),str(row.designation).strip(),str(row.join_date).strip(),float(row.basic_salary),str(row.temporary_password))
                        created+=1
                    log_action(user["id"],"csv_import_employees","employee",str(created)); st.success(f"Imported {created} employee(s).")
            except Exception as e: st.error(f"CSV could not be read: {e}")

elif page in ("Attendance", "My Attendance"):
    st.title("Attendance")
    if role == "Employee":
        emp = get_employee_by_user(user["id"])
        if not emp:
            st.warning("Employee profile missing.")
        else:
            a, b = st.columns(2)
            if a.button("Check in", type="primary"):
                ok, msg = check_in(emp["id"])
                (st.success if ok else st.error)(msg)
            if b.button("Check out"):
                ok, msg = check_out(emp["id"])
                (st.success if ok else st.error)(msg)
            with st.expander("Optional camera + office-location check-in"):
                st.warning("This demo detects a face in the captured image and checks the submitted GPS coordinates. It does not identify the face as you, and manual coordinates can be spoofed; use only as a hackathon demo.")
                camera_image = st.camera_input("Capture a live camera image", key="attendance_camera")
                c1,c2,c3=st.columns(3)
                gps_lat=c1.number_input("Your latitude", min_value=-90.0, max_value=90.0, value=0.0, format="%.6f", key="gps_lat")
                gps_lon=c2.number_input("Your longitude", min_value=-180.0, max_value=180.0, value=0.0, format="%.6f", key="gps_lon")
                gps_accuracy=c3.number_input("GPS accuracy (metres)", min_value=1.0, max_value=1000.0, value=30.0, key="gps_accuracy")
                if st.button("Validate face and location & check in", key="camera_checkin", type="primary"):
                    if not camera_image:
                        st.error("Capture an image first.")
                    else:
                        try:
                            import cv2
                            import numpy as np
                            image_array=cv2.imdecode(np.frombuffer(camera_image.getvalue(),np.uint8),cv2.IMREAD_COLOR)
                            cascade=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
                            gray=cv2.cvtColor(image_array,cv2.COLOR_BGR2GRAY)
                            faces=cascade.detectMultiScale(gray,scaleFactor=1.1,minNeighbors=5,minSize=(50,50))
                            ok,msg=check_in_verified(emp["id"],gps_lat,gps_lon,gps_accuracy,len(faces))
                            log_action(user["id"],"camera_location_checkin_attempt","attendance",date.today().isoformat())
                            (st.success if ok else st.error)(msg)
                        except ImportError:
                            st.error("OpenCV is not installed. Run: pip install opencv-python-headless")
                        except Exception as e:
                            st.error(f"Camera validation failed: {e}")
            show_table(attendance_for_user(emp["id"]))
    else:
        st.caption("HR/Admin attendance board")
        show_table(attendance_all(limit=500))

elif page == "Attendance Corrections":
    st.title("Attendance correction requests")
    if role == "Employee":
        emp = get_employee_by_user(user["id"])
        if emp:
            with st.form("correction_request"):
                d = st.date_input("Attendance date", value=date.today())
                cin = st.text_input("Requested check-in (HH:MM, optional)")
                cout = st.text_input("Requested check-out (HH:MM, optional)")
                reason = st.text_area("Reason for correction")
                if st.form_submit_button("Submit correction request"):
                    ok,msg=request_attendance_correction(emp["id"],d.isoformat(),cin,cout,reason)
                    log_action(user["id"],"request_attendance_correction","attendance",d.isoformat())
                    (st.success if ok else st.error)(msg)
            show_table(list_corrections(employee_id=emp["id"]))
    elif can_hr():
        rows=list_corrections(status="pending")
        show_table(rows)
        if rows:
            opts={f"#{r['id']} · {r['employee_name']} · {r['attendance_date']}":r for r in rows}
            choice=st.selectbox("Pending correction",list(opts)); comment=st.text_input("Decision comment")
            c1,c2=st.columns(2)
            if c1.button("Approve correction"):
                r=opts[choice]; ok,msg=decide_correction(r["id"],user["id"],True,comment); log_action(user["id"],"approve_attendance_correction","correction",r["id"]); (st.success if ok else st.error)(msg)
            if c2.button("Reject correction"):
                r=opts[choice]; ok,msg=decide_correction(r["id"],user["id"],False,comment); log_action(user["id"],"reject_attendance_correction","correction",r["id"]); (st.success if ok else st.error)(msg)
        st.subheader("Mark absent for a past working date")
        d=st.date_input("Date to reconcile",value=date.today(),key="absent_date")
        if st.button("Create absent records"):
            n=mark_absent_for_date(d.isoformat()); log_action(user["id"],"reconcile_absence","attendance",d.isoformat()); st.success(f"Created {n} absent record(s).")

elif page in ("Leave Management", "My Leave"):
    st.title("Leave Management")
    if role == "Employee":
        emp = get_employee_by_user(user["id"])
        if emp:
            st.metric("Remaining approved leave days", leave_balance(emp["id"]))
            st.caption("Balance by leave type")
            show_table([{"Leave type": k.title(), **v} for k,v in leave_balances(emp["id"]).items()])
            st.subheader("Smart leave (plain language)")
            smart_text=st.text_input("Describe your leave",placeholder="e.g. Next Monday and Tuesday off for a wedding",key="smart_leave_text")
            if st.button("Suggest leave dates"):
                import re
                q=smart_text.lower(); today=date.today(); start_date=None; end_date=None
                weekday_names={"monday":0,"tuesday":1,"wednesday":2,"thursday":3,"friday":4,"saturday":5,"sunday":6}
                found=[(name,idx) for name,idx in weekday_names.items() if re.search(r"\b"+name+r"\b",q)]
                if "next" in q and found:
                    first_idx=found[0][1]; delta=(first_idx-today.weekday())%7
                    if delta==0: delta=7
                    start_date=today+pd.Timedelta(days=delta).to_pytimedelta()
                    if len(found)>1:
                        second_idx=found[1][1]; d2=(second_idx-first_idx)%7
                        end_date=start_date+pd.Timedelta(days=d2).to_pytimedelta()
                    else: end_date=start_date
                else:
                    st.warning("For this demo, include 'next' and a weekday name, such as 'next Monday and Tuesday'.")
                if start_date:
                    st.session_state["leave_start"]=start_date
                    st.session_state["leave_end"]=end_date
                    st.session_state["leave_type"]="casual"
                    reason_text=smart_text.split(" for ",1)[1] if " for " in q else smart_text
                    st.session_state["leave_reason"]=reason_text
                    st.success(f"Suggested: casual leave from {start_date.isoformat()} to {end_date.isoformat()}. Review the form and submit to confirm.")
            with st.form("leave_request"):
                leave_type = st.selectbox("Leave type", ["casual", "sick", "annual", "unpaid"], key="leave_type")
                start = st.date_input("Start date", value=date.today(), key="leave_start")
                end = st.date_input("End date", value=date.today(), key="leave_end")
                reason = st.text_area("Reason", key="leave_reason")
                if st.form_submit_button("Submit request"):
                    ok, msg = submit_leave(emp["id"], leave_type, start.isoformat(), end.isoformat(), reason)
                    log_action(user["id"], "submit_leave", "leave", str(emp["id"]))
                    (st.success if ok else st.error)(msg)
            employee_leaves=list_leaves(employee_id=emp["id"])
            show_table(employee_leaves)
            pending=[r for r in employee_leaves if r["status"]=="pending"]
            if pending:
                leave_options={f"#{r['id']} · {r['leave_type']} · {r['start_date']} to {r['end_date']}":r for r in pending}
                cancel_choice=st.selectbox("Cancel pending request",list(leave_options))
                if st.button("Cancel selected request"):
                    r=leave_options[cancel_choice]; ok,msg=cancel_leave(r["id"],emp["id"]); log_action(user["id"],"cancel_leave","leave",r["id"]); (st.success if ok else st.error)(msg)
    else:
        st.subheader("Approval inbox")
        rows = list_leaves(status="pending")
        show_table(rows)
        if rows:
            options = {f"#{r['id']} · {r['employee_name']} · {r['leave_type']} · {r['start_date']} to {r['end_date']}": r for r in rows}
            choice = st.selectbox("Choose request", list(options))
            comment = st.text_input("Decision comment")
            c1, c2 = st.columns(2)
            if c1.button("Approve"):
                r = options[choice]
                ok, msg = decide_leave(r["id"], user["id"], "approved", comment)
                log_action(user["id"], "approve_leave", "leave", str(r["id"]))
                (st.success if ok else st.error)(msg)
            if c2.button("Reject"):
                r = options[choice]
                ok, msg = decide_leave(r["id"], user["id"], "rejected", comment)
                log_action(user["id"], "reject_leave", "leave", str(r["id"]))
                (st.success if ok else st.error)(msg)
        st.subheader("All requests")
        show_table(list_leaves())

elif page in ("Payroll", "My Payslips"):
    st.title("Payroll")
    if role == "Employee":
        emp = get_employee_by_user(user["id"])
        if emp:
            payslips=list_payroll(employee_id=emp["id"])
            show_table(payslips)
            months=[r["month"] for r in payslips]
            if months:
                selected_month=st.selectbox("Download payslip PDF",months)
                if st.button("Generate PDF"):
                    try:
                        from reportlab.lib.pagesizes import A4
                        from reportlab.pdfgen import canvas
                        from io import BytesIO
                        details=get_payslip_details(emp["id"],selected_month)
                        buf=BytesIO(); pdf=canvas.Canvas(buf,pagesize=A4)
                        pdf.setFont("Helvetica-Bold",18); pdf.drawString(60,790,"HCM Lite - Payslip")
                        pdf.setFont("Helvetica",11)
                        lines=[f"Employee: {details['name']}",f"Employee code: {details['employee_code']}",f"Department: {details['department'] or '-'}",f"Month: {details['month']}",f"Status: {details['status']}","",f"Basic salary: PKR {details['basic']:,.2f}",f"HRA: PKR {details['hra']:,.2f}",f"Medical allowance: PKR {details['medical']:,.2f}",f"Gross: PKR {details['gross']:,.2f}",f"Deductions: PKR {details['deductions']:,.2f}",f"Net pay: PKR {details['net']:,.2f}"]
                        y=750
                        for line in lines: pdf.drawString(60,y,line); y-=25
                        pdf.save(); st.download_button("Download payslip",buf.getvalue(),f"payslip_{selected_month}.pdf","application/pdf")
                    except Exception as e: st.error(f"PDF generation failed: {e}. Install reportlab with pip.")
    else:
        month = st.text_input("Payroll month (YYYY-MM)", date.today().strftime("%Y-%m"))
        if st.button("Preview payroll"):
            show_table(payroll_preview(month))
        if st.button("Create payroll draft"):
            try:
                run_id = create_payroll_run(month, user["id"])
                log_action(user["id"], "create_payroll", "payroll_run", str(run_id))
                st.success(f"Payroll draft created (run #{run_id}).")
            except ValueError as e:
                st.error(str(e))
        runs = list_payroll()
        show_table(runs)
        if can_admin() and runs:
            run_map = {f"Run #{r['id']} · {r['month']} · {r['status']}": r for r in runs}
            selected = st.selectbox("Select payroll run to finalize", list(run_map))
            if st.button("Finalize and lock run"):
                r = run_map[selected]
                ok, msg = finalize_payroll(r["id"], user["id"])
                log_action(user["id"], "finalize_payroll", "payroll_run", str(r["id"]))
                (st.success if ok else st.error)(msg)

elif page == "Analytics":
    st.title("Analytics & insights")
    if role == "Employee":
        st.info("Your personal analytics are available on My Dashboard and My Attendance.")
    else:
        stats=get_dashboard_stats(); cols=st.columns(len(stats))
        for col,(label,value) in zip(cols,stats.items()): col.metric(label,value)
        attendance_rows=[dict(r) for r in attendance_all(limit=1000)]
        if attendance_rows:
            adf=pd.DataFrame(attendance_rows)
            st.subheader("Attendance status distribution")
            if "status" in adf: st.bar_chart(adf["status"].value_counts())
            if "department" in adf:
                st.subheader("Attendance records by department")
                st.bar_chart(adf.groupby("department").size())
        st.subheader("Leave usage by type")
        leaves=[dict(r) for r in list_leaves()]
        if leaves:
            ldf=pd.DataFrame(leaves)
            approved=ldf[ldf["status"]=="approved"]
            if not approved.empty: st.bar_chart(approved.groupby("leave_type")["days"].sum())
        st.subheader("Payroll cost")
        runs=[dict(r) for r in list_payroll()]
        if runs: show_table(runs)

elif page == "AI Assistant":
    st.title("AI Assistant")
    st.caption("AI-generated · answers are based on the data available to your role. Do not use it as the final authority for payroll or HR decisions.")
    question=st.text_input("Ask about attendance, leave, payroll or HR policy",key="ai_question")
    if st.button("Ask assistant",type="primary") and question.strip():
        q=question.lower(); answer=None
        if any(w in q for w in ["headcount","how many employees","employees count"]):
            answer=f"There are {len(list_employees())} employee profile(s) in the current system." if role in ("Admin","HR") else "I can only provide information about your own records."
        elif "leave" in q and ("balance" in q or "left" in q or "remaining" in q):
            emp=get_employee_by_user(user["id"]) if role=="Employee" else None
            if emp:
                b=leave_balances(emp["id"]); answer="Your remaining leave balances: "+", ".join(f"{k}: {v['remaining']}" for k,v in b.items())
            elif role in ("Admin","HR"): answer="Use the Leave Management page to inspect individual requests and approvals. Employee-specific balances are shown to the employee after login."
        elif "late" in q:
            rows=[dict(r) for r in attendance_all(limit=1000)]
            late=[r for r in rows if r.get("status")=="late"]
            answer=f"There are {len(late)} late attendance record(s) in the latest attendance records." if role in ("Admin","HR") else "I can only summarize your own attendance records."
        elif any(w in q for w in ["policy","quota","annual leave","sick leave"]):
            answer=f"Current configured quotas: annual {get_setting('leave_quota_annual','14')} days, sick {get_setting('leave_quota_sick','8')} days, casual {get_setting('leave_quota_casual','10')} days. Working days exclude configured weekends and public holidays."
        elif "salary" in q or "payslip" in q:
            answer="For privacy, I cannot reveal another employee's salary. Employees can view their own payslips in My Payslips; HR/Admin can use the Payroll module according to their role."
        if answer is None:
            import os
            key=os.getenv("AI_API_KEY","")
            if key:
                try:
                    from openai import OpenAI
                    client=OpenAI(api_key=key,timeout=15)
                    system_prompt="You are HCM Lite's assistant. The database is the source of truth. Follow role scope. An Employee may only see their own data; never reveal a colleague's salary, leave or attendance. Do not invent data. Policies: late after office start + grace; annual/sick/casual quotas are configurable; workdays exclude configured weekends and public holidays; gross salary is basic + 40% HRA + 10% medical; only Admin finalizes payroll. Tools are read-only. Never save or change records."
                    tools=[
                      {"type":"function","function":{"name":"get_headcount","description":"Get active employee count; Admin/HR only.","parameters":{"type":"object","properties":{},"required":[]}}},
                      {"type":"function","function":{"name":"get_attendance_summary","description":"Get recent attendance status counts; Admin/HR only, employee may get own count.","parameters":{"type":"object","properties":{},"required":[]}}},
                      {"type":"function","function":{"name":"get_late_comers","description":"List employees marked late in latest attendance records; Admin/HR only.","parameters":{"type":"object","properties":{},"required":[]}}},
                      {"type":"function","function":{"name":"get_leave_summary","description":"Summarize leave requests by status and type; Admin/HR only.","parameters":{"type":"object","properties":{},"required":[]}}},
                      {"type":"function","function":{"name":"get_my_leave_balance","description":"Get the signed-in employee's leave balance.","parameters":{"type":"object","properties":{},"required":[]}}},
                      {"type":"function","function":{"name":"get_payroll_summary","description":"Get payroll runs for Admin/HR, or only own payslips for Employee.","parameters":{"type":"object","properties":{},"required":[]}}},
                      {"type":"function","function":{"name":"search_employees","description":"Search employee directory by name or department. Admin/HR only.","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}}
                    ]
                    messages=[{"role":"system","content":system_prompt},{"role":"user","content":f"Role: {role}. Signed-in user: {user['name']}. Question: {question}"}]
                    response=client.chat.completions.create(model=os.getenv("AI_MODEL","gpt-4o-mini"),messages=messages,tools=tools,tool_choice="auto")
                    msg=response.choices[0].message
                    if msg.tool_calls:
                        import json
                        messages.append(msg.model_dump(exclude_none=True))
                        for call in msg.tool_calls:
                            args=json.loads(call.function.arguments or "{}")
                            result={"error":"Tool unavailable"}
                            if call.function.name=="get_headcount":
                                result={"active_employee_count":get_dashboard_stats()["Active employees"]} if role in ("Admin","HR") else {"error":"Not authorized"}
                            elif call.function.name=="get_attendance_summary":
                                if role in ("Admin","HR"):
                                    rows=[dict(r) for r in attendance_all(limit=1000)]; result={"record_count":len(rows),"status_counts":pd.Series([r.get('status','unknown') for r in rows]).value_counts().to_dict()}
                                else:
                                    emp=get_employee_by_user(user['id']); rows=[dict(r) for r in attendance_for_user(emp['id'])] if emp else []; result={"my_record_count":len(rows),"my_status_counts":pd.Series([r.get('status','unknown') for r in rows]).value_counts().to_dict()}
                            elif call.function.name=="get_late_comers":
                                if role in ("Admin","HR"):
                                    rows=[dict(r) for r in attendance_all(limit=1000) if r.get('status')=='late']; result={"late_record_count":len(rows),"recent_late_records":rows[:20]}
                                else: result={"error":"Not authorized to view other employees' attendance"}
                            elif call.function.name=="get_leave_summary":
                                if role in ("Admin","HR"):
                                    rows=[dict(r) for r in list_leaves()]; result={"total_requests":len(rows),"status_counts":pd.Series([r['status'] for r in rows]).value_counts().to_dict(),"type_counts":pd.Series([r['leave_type'] for r in rows]).value_counts().to_dict()}
                                else: result={"error":"Not authorized"}
                            elif call.function.name=="get_my_leave_balance":
                                emp=get_employee_by_user(user['id']); result=leave_balances(emp['id']) if emp else {"error":"Employee profile not linked"}
                            elif call.function.name=="get_payroll_summary":
                                if role in ("Admin","HR"): result=[dict(r) for r in payroll_summary_data()]
                                else:
                                    emp=get_employee_by_user(user['id']); result=[dict(r) for r in payroll_summary_data(employee_id=emp['id'])] if emp else []
                            elif call.function.name=="search_employees":
                                if role in ("Admin","HR"):
                                    term=str(args.get('query','')).lower(); result=[{k:r[k] for k in ('employee_code','name','department','designation','email')} for r in list_employees() if term in str(r['name']).lower() or term in str(r['department']).lower()][:20]
                                else: result={"error":"Not authorized to search the employee directory"}
                            messages.append({"role":"tool","tool_call_id":call.id,"content":json.dumps(result,default=str)})
                        final=client.chat.completions.create(model=os.getenv("AI_MODEL","gpt-4o-mini"),messages=messages,timeout=15)
                        answer=final.choices[0].message.content
                    else:
                        answer=msg.content
                except Exception: answer="AI service is unavailable right now. Try a question about configured leave quotas or ask HR."
            else: answer="The optional hosted AI service is not configured. Set AI_API_KEY to enable general policy Q&A; built-in data answers work without a key."
        st.info(answer)
        log_action(user["id"],"ai_assistant_question","ai",question[:120])
        log_ai_call(user["id"],question,answer)

elif page == "My Profile":
    st.title("My Profile")
    emp=get_employee_by_user(user["id"])
    if emp:
        with st.form("profile_form"):
            st.text_input("Employee code",emp["employee_code"],disabled=True)
            st.text_input("Name",emp["name"],disabled=True)
            st.text_input("Email",emp["email"],disabled=True)
            phone=st.text_input("Phone",emp["phone"] or "")
            address=st.text_area("Address",emp["address"] or "")
            if st.form_submit_button("Save profile"):
                update_employee_profile(emp["id"],emp["department"],emp["designation"],phone,address)
                log_action(user["id"],"update_own_profile","employee",emp["id"]); st.success("Profile updated.")

elif page == "Announcements":
    st.title("Announcements")
    if role in ("Admin", "HR"):
        with st.form("announcement"):
            title = st.text_input("Title")
            body = st.text_area("Message")
            if st.form_submit_button("Post announcement"):
                if title.strip() and body.strip():
                    add_announcement(user["id"], title.strip(), body.strip())
                    log_action(user["id"], "post_announcement", "announcement", title)
                    st.success("Announcement posted.")
    st.subheader("My notifications")
    notifications=list_notifications(user["id"])
    show_table(notifications)
    unread=[n for n in notifications if not n["read_at"]]
    if unread:
        notification_map={f"#{n['id']} · {n['title']}":n for n in unread}
        selected_notification=st.selectbox("Mark notification as read",list(notification_map))
        if st.button("Mark read"):
            mark_notification_read(notification_map[selected_notification]["id"],user["id"]); rerun()
    for item in list_announcements():
        with st.container(border=True):
            st.subheader(item["title"])
            st.write(item["body"])
            st.caption(f"Posted by {item['author_name']} · {item['created_at']}")

elif page == "Audit Log" and can_admin():
    st.title("Audit Log")
    from backend.db import audit_logs
    show_table(audit_logs())
    st.subheader("AI Assistant call log")
    show_table(list_ai_logs())

elif page == "Change Password":
    st.title("Change Password")
    with st.form("change_pw"):
        old = st.text_input("Current password", type="password")
        new = st.text_input("New password", type="password")
        confirm = st.text_input("Confirm new password", type="password")
        if st.form_submit_button("Update password"):
            if new != confirm:
                st.error("New passwords do not match.")
            else:
                ok, msg = change_password(user["id"], old, new)
                if ok:
                    st.session_state.user["must_change_password"] = 0
                    log_action(user["id"], "change_password", "user", user["id"])
                (st.success if ok else st.error)(msg)
                if ok: st.rerun()

st.sidebar.caption("HCM Lite prototype · do not use for production HR data without security review.")
