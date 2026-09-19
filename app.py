import streamlit as st

from database import (
    get_all_patients,
    get_all_screenings,
    get_all_referrals,
    get_all_followups,
)

from screens.screening import show_screening
from screens.results import show_results
from screens.patients import show_patients
from screens.history import show_history
from screens.referrals import show_referrals
from screens.followups import show_followups
from theme import apply_theme


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="NetraTrace | AI Retinal Screening",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.session_state["theme_mode"] = "light"
apply_theme("light")


# ============================================================
# SESSION STATE
# ============================================================

defaults = {

    # LOGIN
    "logged_in": False,

    # NAVIGATION
    "current_screen": "dashboard",

    # SCREENING
    "screening_started": False,
    "screening_result": False,
    "screening_saved": False,
    "screening_id": "",

    # PATIENT FILTER
    "patient_filter": "",

    # PATIENT INFORMATION
    "patient_id": "",
    "patient_name": "",
    "patient_age": 18,
    "patient_gender": "Male",
    "patient_phone": "",
    "patient_email": "",
    "patient_address": "",
    "diabetes_status": "Unknown",

    # SCREENING INFORMATION
    "screening_eye": "Right Eye",
    "screening_date": None,

    # IMAGE
    "uploaded_image": None,
    "image_name": "",

    # AI RESULT
    "quality_status": "",
    "dr_grade": None,
    "severity": "",
    "confidence": 0.0,
    "referral_priority": "",

    # ANALYSIS MODE
    "analysis_mode": "Real AI Model",
    "demo_grade": 3,

    # REFERRAL
    "referral_created": False,

    # PATIENT EDIT / DELETE
    "edit_patient_id": None,
    "confirm_delete_patient": None,

    # REFERRAL EDIT / DELETE
    "edit_referral_id": None,
    "delete_referral_id": None,

    # FOLLOW-UP
    "followup_referral_id": "",
    "edit_followup_id": None,
    "delete_followup_id": None,
}


for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# LOGIN PAGE
# ============================================================

def show_login():

    st.title("👁️ NetraTrace")

    st.subheader(
        "AI-Assisted Diabetic Retinopathy Screening"
    )

    st.markdown("---")

    col1, col2, col3 = st.columns(
        [1, 2, 1]
    )

    with col2:

        st.markdown("### 🔐 Login")

        username = st.text_input(
            "Username",
            placeholder="Enter username",
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter password",
        )

        login_clicked = st.button(
            "Login",
            width="stretch",
        )

        if login_clicked:

            if (
                username.strip() == "admin"
                and password == "admin123"
            ):

                st.session_state[
                    "logged_in"
                ] = True

                st.session_state[
                    "current_screen"
                ] = "dashboard"

                st.success(
                    "Login successful."
                )

                st.rerun()

            else:

                st.error(
                    "Invalid username or password."
                )

        st.caption(
            "Prototype login: admin / admin123"
        )


# ============================================================
# LOGOUT
# ============================================================

def logout():

    st.session_state[
        "logged_in"
    ] = False

    st.session_state[
        "current_screen"
    ] = "dashboard"

    st.session_state[
        "screening_started"
    ] = False

    st.session_state[
        "screening_result"
    ] = False

    st.session_state[
        "screening_saved"
    ] = False

    st.session_state[
        "screening_id"
    ] = ""

    st.session_state[
        "uploaded_image"
    ] = None

    st.session_state[
        "patient_filter"
    ] = ""

    st.session_state[
        "followup_referral_id"
    ] = ""

    st.rerun()


# ============================================================
# CLEAR SCREENING STATE
# ============================================================

def clear_screening_state():

    st.session_state[
        "screening_started"
    ] = False

    st.session_state[
        "screening_result"
    ] = False

    st.session_state[
        "screening_saved"
    ] = False

    st.session_state[
        "screening_id"
    ] = ""

    st.session_state[
        "uploaded_image"
    ] = None

    st.session_state[
        "image_name"
    ] = ""

    st.session_state[
        "quality_status"
    ] = ""

    st.session_state[
        "dr_grade"
    ] = None

    st.session_state[
        "severity"
    ] = ""

    st.session_state[
        "confidence"
    ] = 0.0

    st.session_state[
        "referral_priority"
    ] = ""

    st.session_state[
        "referral_created"
    ] = False

    st.session_state[
        "analysis_mode"
    ] = "Real AI Model"

    st.session_state[
        "demo_grade"
    ] = 3


# ============================================================
# SIDEBAR
# ============================================================

def show_sidebar():

    with st.sidebar:

        st.markdown(
            "<div class=\"sidebar-brand\"><span class=\"sidebar-mark\">◉</span><div><strong>NetraTrace</strong><small>AI RETINAL SCREENING</small></div></div>",
            unsafe_allow_html=True,
        )

        st.caption(
            "AI-Assisted DR Screening"
        )

        st.markdown("---")

        # ====================================================
        # DASHBOARD
        # ====================================================

        if st.button(
            "🏠 Dashboard",
            key="sidebar_dashboard",
            width="stretch",
        ):

            st.session_state[
                "patient_filter"
            ] = ""

            st.session_state[
                "current_screen"
            ] = "dashboard"

            st.rerun()

        # ====================================================
        # PATIENTS
        # ====================================================

        if st.button(
            "👥 Patients",
            key="sidebar_patients",
            width="stretch",
        ):

            st.session_state[
                "current_screen"
            ] = "patients"

            st.rerun()

        # ====================================================
        # NEW SCREENING
        # ====================================================

        if st.button(
            "🩺 New Screening",
            key="sidebar_screening",
            width="stretch",
        ):

            clear_screening_state()

            st.session_state[
                "patient_filter"
            ] = ""

            st.session_state[
                "current_screen"
            ] = "screening_selection"

            st.rerun()

        # ====================================================
        # HISTORY
        # ====================================================

        if st.button(
            "📋 Screening History",
            key="sidebar_history",
            width="stretch",
        ):

            st.session_state[
                "current_screen"
            ] = "history"

            st.rerun()

        # ====================================================
        # REFERRALS
        # ====================================================

        if st.button(
            "🏥 Referrals",
            key="sidebar_referrals",
            width="stretch",
        ):

            st.session_state[
                "current_screen"
            ] = "referrals"

            st.rerun()

        # ====================================================
        # FOLLOW-UPS
        # ====================================================

        if st.button(
            "📅 Follow-ups",
            key="sidebar_followups",
            width="stretch",
        ):

            st.session_state[
                "current_screen"
            ] = "followups"

            st.rerun()

        st.markdown("---")

        # ====================================================
        # SYSTEM STATUS
        # ====================================================

        st.caption("SYSTEM STATUS")

        st.success(
            "● Database Connected"
        )

        st.success(
            "● Screening Module Ready"
        )

        st.success(
            "● Referral Module Ready"
        )

        st.success(
            "● Follow-up Module Ready"
        )

        st.success(
            "● Real AI Model Active"
        )

        st.markdown("---")

        # ====================================================
        # LOGOUT
        # ====================================================

        if st.button(
            "🚪 Logout",
            key="sidebar_logout",
            width="stretch",
        ):

            logout()


# ============================================================
# DASHBOARD
# ============================================================

def show_dashboard():
    """Clinical dashboard: live database metrics + polished SaaS presentation."""
    from datetime import date

    patients = get_all_patients()
    screenings = get_all_screenings()
    referrals = get_all_referrals()
    followups = get_all_followups()

    total_patients = len(patients)
    total_screenings = len(screenings)
    total_referrals = len(referrals)
    total_followups = len(followups)

    high_priority = sum(1 for s in screenings if str(s["referral_priority"] or "").upper() == "HIGH")
    medium_priority = sum(1 for s in screenings if str(s["referral_priority"] or "").upper() == "MEDIUM")
    low_priority = sum(1 for s in screenings if str(s["referral_priority"] or "").upper() == "LOW")

    grade_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    for screening in screenings:
        try:
            grade = int(screening["dr_grade"])
            if grade in grade_counts:
                grade_counts[grade] += 1
        except (TypeError, ValueError):
            pass

    screened_patient_ids = {s["patient_id"] for s in screenings}
    patients_screened = len(screened_patient_ids)
    patients_unscreened = max(total_patients - patients_screened, 0)

    diabetic = sum(1 for p in patients if str(p["diabetes_status"] or "").lower() == "diabetic")
    non_diabetic = sum(1 for p in patients if str(p["diabetes_status"] or "").lower() == "non-diabetic")
    unknown_diabetes = max(total_patients - diabetic - non_diabetic, 0)

    pending = sum(1 for f in followups if str(f["status"] or "").lower() == "pending")
    scheduled = sum(1 for f in followups if str(f["status"] or "").lower() == "scheduled")
    completed = sum(1 for f in followups if str(f["status"] or "").lower() == "completed")
    cancelled = sum(1 for f in followups if str(f["status"] or "").lower() == "cancelled")

    overdue = 0
    today = 0
    upcoming = []
    for f in followups:
        try:
            appt = date.fromisoformat(str(f["appointment_date"]))
            status = str(f["status"] or "").lower()
            if appt < date.today() and status not in ("completed", "cancelled"):
                overdue += 1
            if appt == date.today() and status not in ("completed", "cancelled"):
                today += 1
            if appt >= date.today() and status not in ("completed", "cancelled"):
                upcoming.append(f)
        except Exception:
            pass
    upcoming.sort(key=lambda x: (str(x["appointment_date"] or ""), str(x["appointment_time"] or "")))

    # --------------------------------------------------------
    # HERO
    # --------------------------------------------------------
    st.markdown(
        """
        <div class="dashboard-hero">
            <div>
                <div class="eyebrow">CLINICAL SCREENING WORKSPACE</div>
                <h1>Good morning, Screening Team.</h1>
                <p>Monitor retinal screening activity, identify high-risk cases, and keep patient referrals moving from screening to follow-up.</p>
            </div>
            <div class="hero-badge"><span>●</span> System Ready</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="ai-banner">
            <span class="ai-pulse"></span>
            <div><strong>Real AI Screening Active</strong><div>ResNet18 classification · TTA safety verification · Grad-CAM explainability</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Primary CTA
    cta1, cta2 = st.columns([5, 1.25])
    with cta1:
        st.markdown("### Screening overview")
        st.caption("Live operational snapshot from your NetraTrace database.")
    with cta2:
        if st.button("＋ New Screening", key="dashboard_primary_screening", width="stretch"):
            clear_screening_state()
            st.session_state["patient_filter"] = ""
            st.session_state["current_screen"] = "screening_selection"
            st.rerun()

    # --------------------------------------------------------
    # KPI ROW
    # --------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("👥 Patients", total_patients)
        st.caption(f"{patients_screened} screened · {patients_unscreened} pending")
    with k2:
        st.metric("🩺 Screenings", total_screenings)
        st.caption("Completed AI screening records")
    with k3:
        st.metric("🏥 Referrals", total_referrals)
        st.caption(f"{high_priority} high-priority cases")
    with k4:
        st.metric("🚨 High Risk", high_priority)
        st.caption("Cases requiring clinical attention")

    # --------------------------------------------------------
    # RISK OVERVIEW
    # --------------------------------------------------------
    st.markdown("### Clinical risk overview")
    left, right = st.columns([1.45, 1])

    with left:
        st.markdown("#### DR severity distribution")
        labels = {
            0: "Grade 0 · No DR",
            1: "Grade 1 · Mild NPDR",
            2: "Grade 2 · Moderate NPDR",
            3: "Grade 3 · Severe NPDR",
            4: "Grade 4 · Proliferative DR",
        }
        for grade in range(5):
            count = grade_counts[grade]
            pct = (count / total_screenings * 100) if total_screenings else 0
            st.markdown(f"**{labels[grade]}** <span style='float:right'>{count} · {pct:.1f}%</span>", unsafe_allow_html=True)
            st.progress(min(pct / 100, 1.0))

    with right:
        st.markdown("#### Referral priority")
        r1, r2, r3 = st.columns(3)
        with r1:
            st.metric("High", high_priority)
        with r2:
            st.metric("Medium", medium_priority)
        with r3:
            st.metric("Low", low_priority)
        if total_screenings:
            st.caption(f"{(high_priority / total_screenings * 100):.1f}% of screenings currently marked high priority.")
        else:
            st.caption("Priority distribution will appear after the first screening.")

        if high_priority:
            st.warning(f"{high_priority} screening(s) need high-priority referral attention.")
        else:
            st.success("No high-priority screening cases currently recorded.")

    # --------------------------------------------------------
    # FOLLOW-UP CENTER
    # --------------------------------------------------------
    st.markdown("### Follow-up center")
    f1, f2, f3, f4, f5 = st.columns(5)
    with f1:
        st.metric("Today", today)
    with f2:
        st.metric("Scheduled", scheduled)
    with f3:
        st.metric("Pending", pending)
    with f4:
        st.metric("Completed", completed)
    with f5:
        st.metric("Overdue", overdue)

    if overdue:
        st.error(f"⚠️ {overdue} follow-up(s) are overdue. Review the Follow-ups module.")

    # --------------------------------------------------------
    # ANALYTICS
    # --------------------------------------------------------
    st.markdown("### Analytics")
    a1, a2 = st.columns(2)
    with a1:
        st.markdown("#### Screening volume by DR grade")
        if total_screenings:
            st.bar_chart({
                "Grade 0": grade_counts[0],
                "Grade 1": grade_counts[1],
                "Grade 2": grade_counts[2],
                "Grade 3": grade_counts[3],
                "Grade 4": grade_counts[4],
            }, horizontal=True)
        else:
            st.info("No screening data available yet.")

    with a2:
        st.markdown("#### Patient screening coverage")
        if total_patients:
            st.bar_chart({"Screened": patients_screened, "Not screened": patients_unscreened}, horizontal=True)
        else:
            st.info("No patient data available yet.")
        st.caption(f"Diabetes status: {diabetic} diabetic · {non_diabetic} non-diabetic · {unknown_diabetes} unknown")

    # --------------------------------------------------------
    # UPCOMING FOLLOW-UPS
    # --------------------------------------------------------
    st.markdown("### Upcoming follow-ups")
    if upcoming:
        for f in upcoming[:5]:
            with st.container(border=True):
                u1, u2, u3, u4 = st.columns([1.4, 2.8, 2.8, 1.6])
                with u1:
                    st.markdown(f"**{f['followup_id']}**")
                    st.caption(str(f["appointment_date"]))
                with u2:
                    st.markdown(f"**{f['patient_id']} — {f['patient_name']}**")
                    st.caption(f["status"] or "Pending")
                with u3:
                    st.write(f"👨‍⚕️ {f['doctor_name'] or 'Doctor not specified'}")
                    st.caption(f"🏥 {f['facility'] or 'Facility not specified'}")
                with u4:
                    st.write(f"🕐 {f['appointment_time'] or 'N/A'}")
                    if st.button("Open", key=f"dashboard_fup_{f['followup_id']}", width="stretch"):
                        st.session_state["current_screen"] = "followups"
                        st.rerun()
    else:
        st.info("No upcoming follow-ups scheduled.")

    # --------------------------------------------------------
    # RECENT SCREENINGS
    # --------------------------------------------------------
    st.markdown("### Recent screenings")
    if screenings:
        for s in screenings[:5]:
            grade = s["dr_grade"]
            priority = str(s["referral_priority"] or "—").upper()
            confidence = s["confidence"]
            try:
                confidence_text = f"{float(confidence) * 100:.1f}%" if float(confidence) <= 1 else f"{float(confidence):.1f}%"
            except Exception:
                confidence_text = "—"
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([1.45, 2.8, 1.7, 1.6, 1.4])
                with c1:
                    st.markdown(f"**{s['screening_id']}**")
                    st.caption(str(s["screening_date"]))
                with c2:
                    st.markdown(f"**{s['patient_id']} — {s['patient_name']}**")
                    st.caption(f"{s['eye']} · {s['image_name']}")
                with c3:
                    st.markdown(f"**Grade {grade if grade is not None else '—'}**")
                    st.caption(str(s["severity"] or "Not available"))
                with c4:
                    st.markdown(f"**{confidence_text}**")
                    st.caption("Confidence")
                with c5:
                    st.markdown(f"**{priority}**")
                    st.caption("Priority")
    else:
        st.info("No screening records available yet. Start your first screening to populate this area.")

    # --------------------------------------------------------
    # QUICK ACTIONS
    # --------------------------------------------------------
    st.markdown("### Quick actions")
    q1, q2, q3, q4, q5 = st.columns(5)
    actions = [
        (q1, "➕ Add Patient", "patients", "dashboard_add_patient_v2"),
        (q2, "🩺 New Screening", "screening_selection", "dashboard_new_screening_v2"),
        (q3, "📋 History", "history", "dashboard_history_v2"),
        (q4, "🏥 Referrals", "referrals", "dashboard_referrals_v2"),
        (q5, "📅 Follow-ups", "followups", "dashboard_followups_v2"),
    ]
    for col, label, target, key in actions:
        with col:
            if st.button(label, key=key, width="stretch"):
                if target == "screening_selection":
                    clear_screening_state()
                    st.session_state["patient_filter"] = ""
                st.session_state["current_screen"] = target
                st.rerun()

    st.markdown(
        "<div style='height:18px'></div><div class='ai-banner'><span class='ai-pulse'></span><div><strong>NetraTrace AI pipeline ready</strong><div>Fundus validation → image quality gate → DR grading → TTA safety check → Grad-CAM explanation → referral priority</div></div></div>",
        unsafe_allow_html=True,
    )


# ============================================================
# AUTHENTICATION
# ============================================================

if not st.session_state[
    "logged_in"
]:

    show_login()

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

show_sidebar()


# ============================================================
# MANUAL SCREEN ROUTING
# ============================================================

current_screen = st.session_state.get(
    "current_screen",
    "dashboard"
)


# ============================================================
# DASHBOARD
# ============================================================

if current_screen == "dashboard":

    show_dashboard()

    st.stop()


# ============================================================
# SCREENING SELECTION
# ============================================================

if current_screen == "screening_selection":

    show_screening()

    st.stop()


# ============================================================
# SCREENING
# ============================================================

if current_screen == "screening":

    show_screening()

    st.stop()


# ============================================================
# RESULTS
# ============================================================

if current_screen == "results":

    show_results()

    st.stop()


# ============================================================
# PATIENTS
# ============================================================

if current_screen == "patients":

    show_patients()

    st.stop()


# ============================================================
# SCREENING HISTORY
# ============================================================

if current_screen == "history":

    show_history()

    st.stop()


# ============================================================
# REFERRALS
# ============================================================

if current_screen == "referrals":

    show_referrals()

    st.stop()


# ============================================================
# FOLLOW-UPS
# ============================================================

if current_screen == "followups":

    show_followups()

    st.stop()


# ============================================================
# FALLBACK
# ============================================================

st.session_state[
    "current_screen"
] = "dashboard"

st.rerun()