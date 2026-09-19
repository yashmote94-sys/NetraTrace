import streamlit as st
from datetime import date

from database import (
    get_all_referrals,
    get_referral,
    get_screening,
    get_patient,
    save_referral,
    update_referral,
    delete_referral,
    generate_referral_id,
    get_referral_followups,
)


# ============================================================
# CONSTANTS
# ============================================================

PRIORITY_OPTIONS = [
    "HIGH",
    "MEDIUM",
    "LOW",
]

STATUS_OPTIONS = [
    "Pending",
    "Scheduled",
    "Completed",
    "Cancelled",
]

REFERRAL_TYPES = [
    "Ophthalmologist",
    "Retina Specialist",
    "Eye Hospital",
    "General Eye Care",
    "Emergency Eye Care",
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def status_icon(status):
    status = str(status).lower()

    if status == "pending":
        return "🟡"
    elif status == "scheduled":
        return "🔵"
    elif status == "completed":
        return "🟢"
    elif status == "cancelled":
        return "🔴"

    return "⚪"


def priority_icon(priority):
    priority = str(priority).upper()

    if priority == "HIGH":
        return "🔴"
    elif priority == "MEDIUM":
        return "🟠"
    elif priority == "LOW":
        return "🟢"

    return "⚪"


def get_grade_label(grade):
    try:
        grade = int(grade)
    except Exception:
        return "Unknown"

    labels = {
        0: "No DR",
        1: "Mild NPDR",
        2: "Moderate NPDR",
        3: "Severe NPDR",
        4: "Proliferative DR",
    }

    return labels.get(grade, "Unknown")


# ============================================================
# MAIN REFERRAL SCREEN
# ============================================================

def show_referrals():


    st.markdown("""
    <style>
    .page-kicker {font-size:.68rem;letter-spacing:.15em;font-weight:800;color:#148f89;margin-bottom:.15rem;}
    .referral-hero {display:flex;justify-content:space-between;align-items:center;gap:20px;padding:21px 23px;margin:8px 0 22px;border:1px solid #dfe8eb;border-radius:16px;background:#fff;box-shadow:0 5px 18px rgba(25,55,65,.045);}
    .referral-hero-label,.linked-title {font-size:.67rem;letter-spacing:.13em;font-weight:800;color:#148f89;}
    .referral-hero-title {font-size:1.3rem;font-weight:800;color:#18323d;margin:5px 0;}
    .referral-hero-copy {color:#6d7f88;font-size:.86rem;max-width:700px;}
    .referral-hero-status {font-size:.67rem;font-weight:800;letter-spacing:.08em;white-space:nowrap;padding:8px 11px;border-radius:999px;background:#eaf7f5;color:#176f6a;border:1px solid #d4ebe8;}
    .dot {display:inline-block;width:7px;height:7px;border-radius:50%;background:#148f89;margin-right:7px;}
    .section-divider {height:1px;background:#e1e9ec;margin:22px 0;}
    .linked-screening {padding:15px 17px;border:1px solid #dfe8eb;border-radius:13px;background:#f9fbfc;margin:10px 0 18px;}
    .linked-main {font-size:1.02rem;font-weight:800;color:#18323d;margin:4px 0;}
    .linked-meta {font-size:.82rem;color:#6d7f88;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-kicker">CARE COORDINATION</div>', unsafe_allow_html=True)
    st.title("Referral Management")
    st.caption(
        "Coordinate specialist referrals, track priority, and keep every patient handoff visible."
    )
    st.markdown(
        """<div class="referral-hero">
            <div>
                <div class="referral-hero-label">REFERRAL WORKSPACE</div>
                <div class="referral-hero-title">From AI screening to clinical follow-up</div>
                <div class="referral-hero-copy">Review referral priority, assign care details, and track the next action without losing the screening context.</div>
            </div>
            <div class="referral-hero-status"><span class="dot"></span> CARE COORDINATION ACTIVE</div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ========================================================
    # GET REFERRALS
    # ========================================================

    referrals = get_all_referrals()

    # ========================================================
    # OVERVIEW METRICS
    # ========================================================

    total = len(referrals)

    high = sum(
        1
        for r in referrals
        if str(r["priority"]).upper() == "HIGH"
    )

    medium = sum(
        1
        for r in referrals
        if str(r["priority"]).upper() == "MEDIUM"
    )

    low = sum(
        1
        for r in referrals
        if str(r["priority"]).upper() == "LOW"
    )

    pending = sum(
        1
        for r in referrals
        if str(r["status"]).lower() == "pending"
    )

    scheduled = sum(
        1
        for r in referrals
        if str(r["status"]).lower() == "scheduled"
    )

    completed = sum(
        1
        for r in referrals
        if str(r["status"]).lower() == "completed"
    )

    cancelled = sum(
        1
        for r in referrals
        if str(r["status"]).lower() == "cancelled"
    )

    st.markdown("### Referral overview")
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.metric("Total Referrals", total)

    with c2:
        st.metric("🔴 High Priority", high)

    with c3:
        st.metric("🟡 Pending", pending)

    with c4:
        st.metric("🔵 Scheduled", scheduled)

    with c5:
        st.metric("🟢 Completed", completed)

    st.markdown("<div class=\"section-divider\"></div>", unsafe_allow_html=True)

    # ========================================================
    # CREATE REFERRAL FROM SCREENING
    # ========================================================

    screening_id = st.session_state.get(
        "screening_id",
        ""
    )

    if screening_id:

        screening = get_screening(screening_id)

        if screening:

            patient = get_patient(
                screening["patient_id"]
            )

            st.markdown("### Create referral")
            st.caption("Referral is linked directly to the selected screening and patient record.")

            if patient:

                st.markdown(
                    f"""<div class="linked-screening">
                    <div class="linked-title">Linked screening</div>
                    <div class="linked-main">{patient['patient_id']} · {patient['name']}</div>
                    <div class="linked-meta">Screening {screening_id} · {screening['eye']} · Grade {screening['dr_grade']} · {get_grade_label(screening['dr_grade'])} · {screening['confidence']}% confidence</div>
                    </div>""", unsafe_allow_html=True
                )

            with st.form("create_referral_form"):

                c1, c2 = st.columns(2)

                # ------------------------------------------------
                # LEFT
                # ------------------------------------------------

                with c1:

                    referral_date = st.date_input(
                        "Referral Date",
                        value=date.today(),
                    )

                    default_priority = (
                        screening["referral_priority"]
                        if screening["referral_priority"]
                        in PRIORITY_OPTIONS
                        else "HIGH"
                    )

                    priority = st.selectbox(
                        "Priority",
                        PRIORITY_OPTIONS,
                        index=PRIORITY_OPTIONS.index(
                            default_priority
                        ),
                    )

                    referral_type = st.selectbox(
                        "Referral Type",
                        REFERRAL_TYPES,
                    )

                    doctor_name = st.text_input(
                        "Doctor Name",
                        placeholder="Example: Dr. ABC Sharma",
                    )

                # ------------------------------------------------
                # RIGHT
                # ------------------------------------------------

                with c2:

                    facility = st.text_input(
                        "Preferred Facility",
                        placeholder="Example: Ruby Hall Clinic",
                    )

                    reason = st.text_area(
                        "Reason for Referral",
                        value=(
                            screening["severity"]
                            or ""
                        ),
                    )

                    status = st.selectbox(
                        "Status",
                        STATUS_OPTIONS,
                    )

                    notes = st.text_area(
                        "Notes",
                        placeholder=(
                            "Additional referral notes..."
                        ),
                    )

                create = st.form_submit_button(
                    "📋 Create Referral",
                    width="stretch",
                )

            if create:

                if not doctor_name.strip():

                    st.error(
                        "Doctor Name is required."
                    )

                elif not facility.strip():

                    st.error(
                        "Preferred Facility is required."
                    )

                else:

                    referral_id = generate_referral_id()

                    save_referral(
                        referral_id,
                        screening_id,
                        screening["patient_id"],
                        referral_date,
                        priority,
                        referral_type,
                        doctor_name.strip(),
                        facility.strip(),
                        reason.strip(),
                        status,
                        notes.strip(),
                    )

                    st.success(
                        f"Referral {referral_id} "
                        "created successfully."
                    )

                    st.session_state[
                        "screening_id"
                    ] = ""

                    st.rerun()

    # ========================================================
    # REFERRAL STATUS SUMMARY
    # ========================================================

    st.markdown("### Referral status")

    s1, s2, s3, s4 = st.columns(4)

    with s1:
        st.metric(
            "🟡 Pending",
            pending
        )

    with s2:
        st.metric(
            "🔵 Scheduled",
            scheduled
        )

    with s3:
        st.metric(
            "🟢 Completed",
            completed
        )

    with s4:
        st.metric(
            "🔴 Cancelled",
            cancelled
        )

    st.markdown("<div class=\"section-divider\"></div>", unsafe_allow_html=True)

    # ========================================================
    # SEARCH & FILTER
    # ========================================================

    st.markdown("### Find a referral")
    st.caption("Search by patient, screening, doctor, facility, referral ID, status, or priority.")

    f1, f2, f3 = st.columns(3)

    with f1:

        search_text = st.text_input(
            "Search",
            placeholder=(
                "Referral ID, patient ID, patient name..."
            ),
        )

    with f2:

        status_filter = st.selectbox(
            "Status",
            ["All"] + STATUS_OPTIONS,
        )

    with f3:

        priority_filter = st.selectbox(
            "Priority",
            ["All"] + PRIORITY_OPTIONS,
        )

    # ========================================================
    # APPLY FILTERS
    # ========================================================

    filtered_referrals = []

    search_text = search_text.strip().lower()

    for referral in referrals:

        if search_text:

            searchable = " ".join(
                [
                    str(
                        referral["referral_id"]
                        or ""
                    ),
                    str(
                        referral["patient_id"]
                        or ""
                    ),
                    str(
                        referral["patient_name"]
                        or ""
                    ),
                    str(
                        referral["screening_id"]
                        or ""
                    ),
                    str(
                        referral["doctor_name"]
                        or ""
                    ),
                    str(
                        referral["facility"]
                        or ""
                    ),
                ]
            ).lower()

            if search_text not in searchable:
                continue

        if status_filter != "All":

            if (
                str(referral["status"])
                != status_filter
            ):
                continue

        if priority_filter != "All":

            if (
                str(referral["priority"]).upper()
                != priority_filter
            ):
                continue

        filtered_referrals.append(referral)

    # ========================================================
    # RESULTS COUNT
    # ========================================================

    st.caption(
        f"Showing {len(filtered_referrals)} "
        f"of {total} referral(s)"
    )

    # ========================================================
    # REFERRAL RECORDS
    # ========================================================

    st.markdown("### Referral queue")

    if not filtered_referrals:

        st.info(
            "No referrals match the selected filters."
        )

    else:

        for referral in filtered_referrals:

            referral_id = referral[
                "referral_id"
            ]

            patient_id = referral[
                "patient_id"
            ]

            patient_name = referral[
                "patient_name"
            ]

            screening_id = referral[
                "screening_id"
            ]

            doctor_name = (
                referral["doctor_name"]
                or "Not specified"
            )

            facility = (
                referral["facility"]
                or "Not specified"
            )

            priority = str(
                referral["priority"]
            ).upper()

            status = str(
                referral["status"]
            )

            with st.container(border=True):

                # =================================================
                # HEADER
                # =================================================

                c1, c2, c3 = st.columns(
                    [2, 5, 2]
                )

                with c1:

                    st.markdown(
                        f"### {referral_id}"
                    )

                    st.caption(
                        f"Date: {referral['referral_date']}"
                    )

                with c2:

                    st.markdown(
                        f"**{patient_id} — "
                        f"{patient_name}**"
                    )

                    st.caption(
                        f"Screening: {screening_id}"
                    )

                with c3:

                    st.markdown(
                        f"### "
                        f"{priority_icon(priority)} "
                        f"{priority}"
                    )

                    st.caption(
                        f"{status_icon(status)} "
                        f"{status}"
                    )

                # =================================================
                # SCREENING INFORMATION
                # =================================================

                screening = get_screening(
                    screening_id
                )

                if screening:

                    st.markdown("#### 🩺 Screening Information")

                    sc1, sc2, sc3, sc4 = st.columns(4)

                    with sc1:
                        st.write(
                            f"**DR Grade**  \n"
                            f"{screening['dr_grade']}"
                        )

                    with sc2:
                        st.write(
                            f"**Severity**  \n"
                            f"{screening['severity']}"
                        )

                    with sc3:
                        st.write(
                            f"**Eye**  \n"
                            f"{screening['eye']}"
                        )

                    with sc4:
                        st.write(
                            f"**Confidence**  \n"
                            f"{screening['confidence']}%"
                        )

                # =================================================
                # REFERRAL DETAILS
                # =================================================

                st.markdown("#### 📋 Referral Details")

                d1, d2, d3 = st.columns(3)

                with d1:

                    st.write(
                        f"**👨‍⚕️ Doctor**  \n"
                        f"{doctor_name}"
                    )

                with d2:

                    st.write(
                        f"**🏥 Facility**  \n"
                        f"{facility}"
                    )

                with d3:

                    st.write(
                        f"**Referral Type**  \n"
                        f"{referral['referral_type']}"
                    )

                st.write(
                    f"**Reason:** "
                    f"{referral['reason'] or 'Not specified'}"
                )

                if referral["notes"]:

                    st.caption(
                        f"📝 Notes: {referral['notes']}"
                    )

                # =================================================
                # ACTIONS
                # =================================================

                # =================================================
                # ACTIONS
                # =================================================

                followups = get_referral_followups(referral_id)
                followup_count = len(followups)

                if followup_count:
                    latest_followup = followups[0]
                    latest_status = latest_followup["status"] or "Pending"
                    st.caption(
                        f"📅 Follow-ups: {followup_count} • "
                        f"Latest status: {status_icon(latest_status)} "
                        f"{latest_status}"
                    )
                else:
                    st.caption("📅 No follow-up scheduled yet.")

                a1, a2, a3, a4 = st.columns(4)

                with a1:

                    if st.button(
                        "📅 Schedule Follow-up",
                        key=f"followup_ref_{referral_id}",
                        width="stretch",
                    ):

                        st.session_state[
                            "followup_referral_id"
                        ] = referral_id

                        st.session_state[
                            "current_screen"
                        ] = "followups"

                        st.rerun()

                with a2:

                    if st.button(
                        "👤 View Patient",
                        key=f"patient_{referral_id}",
                        width="stretch",
                    ):

                        st.session_state[
                            "patient_filter"
                        ] = patient_id

                        st.session_state[
                            "current_screen"
                        ] = "patients"

                        st.rerun()

                with a3:

                    if st.button(
                        "📊 View Screening",
                        key=f"screening_{referral_id}",
                        width="stretch",
                    ):

                        st.session_state[
                            "screening_id"
                        ] = screening_id

                        st.session_state[
                            "current_screen"
                        ] = "results"

                        st.rerun()

                with a4:

                    if st.button(
                        "✏️ Edit",
                        key=f"edit_ref_{referral_id}",
                        width="stretch",
                    ):

                        st.session_state[
                            "edit_referral_id"
                        ] = referral_id

                        st.rerun()

                # =================================================
                # EDIT REFERRAL
                # =================================================

                if (
                    st.session_state.get(
                        "edit_referral_id"
                    )
                    == referral_id
                ):

                    st.markdown("---")

                    st.subheader(
                        f"✏️ Edit Referral — "
                        f"{referral_id}"
                    )

                    current_date = date.today()

                    try:

                        current_date = date.fromisoformat(
                            str(
                                referral[
                                    "referral_date"
                                ]
                            )
                        )

                    except Exception:

                        pass

                    with st.form(
                        f"edit_referral_form_{referral_id}"
                    ):

                        c1, c2 = st.columns(2)

                        with c1:

                            new_date = st.date_input(
                                "Referral Date",
                                value=current_date,
                            )

                            current_priority = (
                                referral["priority"]
                                if referral["priority"]
                                in PRIORITY_OPTIONS
                                else "HIGH"
                            )

                            new_priority = st.selectbox(
                                "Priority",
                                PRIORITY_OPTIONS,
                                index=PRIORITY_OPTIONS.index(
                                    current_priority
                                ),
                            )

                            current_type = (
                                referral["referral_type"]
                                if referral[
                                    "referral_type"
                                ] in REFERRAL_TYPES
                                else "Ophthalmologist"
                            )

                            new_type = st.selectbox(
                                "Referral Type",
                                REFERRAL_TYPES,
                                index=REFERRAL_TYPES.index(
                                    current_type
                                ),
                            )

                            new_doctor = st.text_input(
                                "Doctor Name",
                                value=(
                                    referral[
                                        "doctor_name"
                                    ]
                                    or ""
                                ),
                            )

                        with c2:

                            new_facility = st.text_input(
                                "Preferred Facility",
                                value=(
                                    referral[
                                        "facility"
                                    ]
                                    or ""
                                ),
                            )

                            new_reason = st.text_area(
                                "Reason",
                                value=(
                                    referral["reason"]
                                    or ""
                                ),
                            )

                            current_status = (
                                referral["status"]
                                if referral["status"]
                                in STATUS_OPTIONS
                                else "Pending"
                            )

                            new_status = st.selectbox(
                                "Status",
                                STATUS_OPTIONS,
                                index=STATUS_OPTIONS.index(
                                    current_status
                                ),
                            )

                            new_notes = st.text_area(
                                "Notes",
                                value=(
                                    referral["notes"]
                                    or ""
                                ),
                            )

                        save_changes = (
                            st.form_submit_button(
                                "💾 Save Changes",
                                width="stretch",
                            )
                        )

                    if save_changes:

                        if not new_doctor.strip():

                            st.error(
                                "Doctor Name is required."
                            )

                        elif not new_facility.strip():

                            st.error(
                                "Preferred Facility "
                                "is required."
                            )

                        else:

                            update_referral(
                                referral_id,
                                new_date,
                                new_priority,
                                new_type,
                                new_doctor.strip(),
                                new_facility.strip(),
                                new_reason.strip(),
                                new_status,
                                new_notes.strip(),
                            )

                            st.session_state[
                                "edit_referral_id"
                            ] = None

                            st.success(
                                "Referral updated successfully."
                            )

                            st.rerun()

                    if st.button(
                        "Cancel Edit",
                        key=f"cancel_edit_{referral_id}",
                        width="stretch",
                    ):

                        st.session_state[
                            "edit_referral_id"
                        ] = None

                        st.rerun()

                # =================================================
                # DELETE
                # =================================================

                delete_key = (
                    f"delete_ref_{referral_id}"
                )

                if st.button(
                    "🗑️ Delete Referral",
                    key=delete_key,
                    width="stretch",
                ):

                    st.session_state[
                        "delete_referral_id"
                    ] = referral_id

                    st.rerun()

                if (
                    st.session_state.get(
                        "delete_referral_id"
                    )
                    == referral_id
                ):

                    st.warning(
                        f"Are you sure you want to delete "
                        f"**{referral_id}**?"
                    )

                    d1, d2 = st.columns(2)

                    with d1:

                        if st.button(
                            "⚠️ Confirm Delete",
                            key=f"confirm_delete_{referral_id}",
                            width="stretch",
                        ):

                            delete_referral(
                                referral_id
                            )

                            st.session_state[
                                "delete_referral_id"
                            ] = None

                            st.success(
                                "Referral deleted successfully."
                            )

                            st.rerun()

                    with d2:

                        if st.button(
                            "Cancel",
                            key=f"cancel_delete_{referral_id}",
                            width="stretch",
                        ):

                            st.session_state[
                                "delete_referral_id"
                            ] = None

                            st.rerun()

    # ========================================================
    # BOTTOM NAVIGATION
    # ========================================================

    st.markdown("---")

    c1, c2, c3 = st.columns(3)

    with c1:

        if st.button(
            "🩺 New Screening",
            width="stretch",
        ):

            st.session_state[
                "current_screen"
            ] = "screening_selection"

            st.rerun()

    with c2:

        if st.button(
            "📋 Screening History",
            width="stretch",
        ):

            st.session_state[
                "current_screen"
            ] = "history"

            st.rerun()

    with c3:

        if st.button(
            "🏠 Dashboard",
            width="stretch",
        ):

            st.session_state[
                "current_screen"
            ] = "dashboard"

            st.rerun()