import streamlit as st
from datetime import date, time, datetime

from database import (
    get_all_followups,
    get_all_referrals,
    get_referral,
    get_patient,
    get_screening,
    get_referral_followups,
    generate_followup_id,
    save_followup,
    update_followup,
    delete_followup,
)

STATUS_OPTIONS = ["Pending", "Scheduled", "Completed", "Cancelled"]


def _status_icon(status):
    return {
        "pending": "🟡",
        "scheduled": "🔵",
        "completed": "🟢",
        "cancelled": "⚪",
    }.get(str(status or "").lower(), "⚪")


def _priority_icon(priority):
    return {
        "HIGH": "🔴",
        "MEDIUM": "🟠",
        "LOW": "🟢",
    }.get(str(priority or "").upper(), "⚪")


def _safe_date(value, fallback=None):
    fallback = fallback or date.today()
    try:
        return date.fromisoformat(str(value))
    except Exception:
        return fallback


def _safe_time(value):
    try:
        return time.fromisoformat(str(value))
    except Exception:
        return time(10, 0)


def _is_overdue(followup):
    try:
        appt = _safe_date(followup["appointment_date"])
        status = str(followup["status"] or "").lower()
        return appt < date.today() and status not in {"completed", "cancelled"}
    except Exception:
        return False


def show_followups():
    followups = get_all_followups()
    referrals = get_all_referrals()

    total = len(followups)
    pending = sum(str(f["status"] or "").lower() == "pending" for f in followups)
    scheduled = sum(str(f["status"] or "").lower() == "scheduled" for f in followups)
    completed = sum(str(f["status"] or "").lower() == "completed" for f in followups)
    cancelled = sum(str(f["status"] or "").lower() == "cancelled" for f in followups)
    overdue = sum(_is_overdue(f) for f in followups)
    today_count = sum(
        _safe_date(f["appointment_date"]) == date.today()
        and str(f["status"] or "").lower() not in {"completed", "cancelled"}
        for f in followups
    )

    # Header
    st.markdown(
        '<div class="eyebrow">CARE COORDINATION</div>',
        unsafe_allow_html=True,
    )
    st.title("Follow-up Management")
    st.caption("Coordinate ophthalmology appointments, track outcomes, and keep referred patients moving through care.")

    # KPI row
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Total", total)
    with k2:
        st.metric("Today", today_count)
    with k3:
        st.metric("Scheduled", scheduled)
    with k4:
        st.metric("Completed", completed)
    with k5:
        st.metric("Overdue", overdue)

    if overdue:
        st.error(f"⚠️ {overdue} follow-up(s) are overdue. Review the care queue below.")

    # Create / schedule section
    selected_referral_id = st.session_state.get("followup_referral_id", "")
    selected_referral = get_referral(selected_referral_id) if selected_referral_id else None
    selected_screening = None
    selected_patient = None
    if selected_referral:
        selected_screening = get_screening(selected_referral["screening_id"])
        selected_patient = get_patient(selected_referral["patient_id"])

    st.markdown("### Schedule a follow-up")
    st.caption("Create a follow-up directly from a referral or choose a referral from the list.")

    referral_options = []
    referral_lookup = {}
    for r in referrals:
        rid = r["referral_id"]
        label = f"{rid} · {r['patient_id']} — {r['patient_name']} · {str(r['priority'] or '—').upper()}"
        referral_options.append(label)
        referral_lookup[label] = rid

    if referral_options:
        default_index = 0
        if selected_referral_id:
            for i, label in enumerate(referral_options):
                if referral_lookup[label] == selected_referral_id:
                    default_index = i
                    break

        with st.container(border=True):
            chosen_label = st.selectbox("Referral", referral_options, index=default_index, key="followup_referral_selector")
            chosen_referral_id = referral_lookup[chosen_label]
            chosen_referral = get_referral(chosen_referral_id)
            chosen_screening = get_screening(chosen_referral["screening_id"])
            chosen_patient = get_patient(chosen_referral["patient_id"])

            st.markdown(
                f"**{chosen_patient['patient_id']} — {chosen_patient['name']}**  ·  "
                f"Screening {chosen_referral['screening_id']}  ·  "
                f"{_priority_icon(chosen_referral['priority'])} {str(chosen_referral['priority'] or '—').upper()}"
            )
            if chosen_screening:
                st.caption(
                    f"DR Grade {chosen_screening['dr_grade']} · {chosen_screening['severity']} · "
                    f"{chosen_screening['eye']} · AI confidence {chosen_screening['confidence']}%"
                )

            with st.form("create_followup_form"):
                c1, c2 = st.columns(2)
                with c1:
                    appointment_date = st.date_input("Appointment Date", value=date.today())
                    appointment_time = st.time_input("Appointment Time", value=time(10, 0))
                    doctor_name = st.text_input(
                        "Doctor Name",
                        value=(chosen_referral["doctor_name"] or ""),
                        placeholder="Example: Dr. ABC Sharma",
                    )
                with c2:
                    facility = st.text_input(
                        "Facility",
                        value=(chosen_referral["facility"] or ""),
                        placeholder="Example: Eye hospital / clinic",
                    )
                    status = st.selectbox("Status", STATUS_OPTIONS, index=1)
                    notes = st.text_area("Notes", placeholder="Appointment notes, instructions, or outcome details...")

                create = st.form_submit_button("＋ Schedule Follow-up", type="primary", width="stretch")

            if create:
                if not doctor_name.strip():
                    st.error("Doctor Name is required.")
                elif not facility.strip():
                    st.error("Facility is required.")
                else:
                    followup_id = generate_followup_id()
                    save_followup(
                        followup_id,
                        chosen_referral_id,
                        chosen_referral["screening_id"],
                        chosen_referral["patient_id"],
                        doctor_name.strip(),
                        facility.strip(),
                        appointment_date,
                        appointment_time.strftime("%H:%M"),
                        status,
                        notes.strip(),
                    )
                    st.session_state["followup_referral_id"] = ""
                    st.success(f"Follow-up {followup_id} scheduled successfully.")
                    st.rerun()
    else:
        st.info("No referrals are available yet. Create a referral from a screening result first.")

    # Filters
    st.markdown("### Follow-up queue")
    f1, f2, f3 = st.columns([2.2, 1, 1])
    with f1:
        search = st.text_input("Search", placeholder="Patient, follow-up ID, doctor, facility…", label_visibility="collapsed")
    with f2:
        status_filter = st.selectbox("Status", ["All"] + STATUS_OPTIONS, label_visibility="collapsed")
    with f3:
        view_filter = st.selectbox("View", ["All", "Today", "Overdue", "Upcoming"], label_visibility="collapsed")

    filtered = []
    for f in followups:
        status = str(f["status"] or "Pending")
        if status_filter != "All" and status != status_filter:
            continue
        if view_filter == "Today" and _safe_date(f["appointment_date"]) != date.today():
            continue
        if view_filter == "Overdue" and not _is_overdue(f):
            continue
        if view_filter == "Upcoming":
            if _safe_date(f["appointment_date"]) < date.today() or status.lower() in {"completed", "cancelled"}:
                continue
        haystack = " ".join(str(f[k] if k in f.keys() else "" or "") for k in ["followup_id", "patient_id", "patient_name", "doctor_name", "facility"]).lower()
        if search.strip().lower() not in haystack:
            continue
        filtered.append(f)

    filtered.sort(key=lambda x: (str(x["appointment_date"] or ""), str(x["appointment_time"] or "")))
    st.caption(f"Showing {len(filtered)} of {total} follow-up(s)")

    if not filtered:
        st.info("No follow-ups match the selected filters.")
    else:
        for f in filtered:
            fid = f["followup_id"]
            status = str(f["status"] or "Pending")
            overdue_flag = _is_overdue(f)
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1.5, 3, 2.5, 1.6])
                with c1:
                    st.markdown(f"**{fid}**")
                    st.caption(str(f["appointment_date"]))
                    st.caption(f"🕐 {f['appointment_time'] or 'Time not set'}")
                with c2:
                    st.markdown(f"**{f['patient_id']} — {f['patient_name']}**")
                    st.caption(f"Referral {f['referral_id']} · Screening {f['screening_id']}")
                    st.caption(f"{_status_icon(status)} {status}" + (" · ⚠️ OVERDUE" if overdue_flag else ""))
                with c3:
                    st.markdown(f"👨‍⚕️ **{f['doctor_name'] or 'Doctor not specified'}**")
                    st.caption(f"🏥 {f['facility'] or 'Facility not specified'}")
                    if f["notes"]:
                        st.caption(f"📝 {f['notes']}")
                with c4:
                    if st.button("✏️ Edit", key=f"edit_fup_{fid}", width="stretch"):
                        st.session_state["edit_followup_id"] = fid
                        st.rerun()
                    if st.button("🗑️ Delete", key=f"delete_fup_{fid}", width="stretch"):
                        st.session_state["delete_followup_id"] = fid
                        st.rerun()

                if st.session_state.get("edit_followup_id") == fid:
                    with st.form(f"edit_followup_{fid}"):
                        e1, e2 = st.columns(2)
                        with e1:
                            new_date = st.date_input("Appointment Date", value=_safe_date(f["appointment_date"]))
                            new_time = st.time_input("Appointment Time", value=_safe_time(f["appointment_time"]))
                            new_doctor = st.text_input("Doctor Name", value=f["doctor_name"] or "")
                        with e2:
                            new_facility = st.text_input("Facility", value=f["facility"] or "")
                            current_status = status if status in STATUS_OPTIONS else "Pending"
                            new_status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(current_status))
                            new_notes = st.text_area("Notes", value=f["notes"] or "")
                        save = st.form_submit_button("💾 Save Changes", type="primary", width="stretch")
                    if save:
                        if not new_doctor.strip() or not new_facility.strip():
                            st.error("Doctor Name and Facility are required.")
                        else:
                            update_followup(
                                fid,
                                new_doctor.strip(),
                                new_facility.strip(),
                                new_date,
                                new_time.strftime("%H:%M"),
                                new_status,
                                new_notes.strip(),
                            )
                            st.session_state["edit_followup_id"] = None
                            st.success("Follow-up updated successfully.")
                            st.rerun()

                if st.session_state.get("delete_followup_id") == fid:
                    st.warning(f"Delete **{fid}**? This will remove the follow-up record.")
                    d1, d2 = st.columns(2)
                    with d1:
                        if st.button("Confirm Delete", key=f"confirm_del_fup_{fid}", width="stretch"):
                            delete_followup(fid)
                            st.session_state["delete_followup_id"] = None
                            st.success("Follow-up deleted successfully.")
                            st.rerun()
                    with d2:
                        if st.button("Cancel", key=f"cancel_del_fup_{fid}", width="stretch"):
                            st.session_state["delete_followup_id"] = None
                            st.rerun()

    # Navigation
    st.markdown("### Care workflow")
    n1, n2, n3 = st.columns(3)
    with n1:
        if st.button("🏥 Referrals", width="stretch"):
            st.session_state["current_screen"] = "referrals"
            st.rerun()
    with n2:
        if st.button("📋 Screening History", width="stretch"):
            st.session_state["current_screen"] = "history"
            st.rerun()
    with n3:
        if st.button("🩺 New Screening", width="stretch"):
            st.session_state["current_screen"] = "screening_selection"
            st.rerun()
