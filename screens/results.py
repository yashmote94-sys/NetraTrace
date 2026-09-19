import streamlit as st

from database import get_screening, get_patient


CLASS_NAMES = [
    "Grade 0 - No DR",
    "Grade 1 - Mild NPDR",
    "Grade 2 - Moderate NPDR",
    "Grade 3 - Severe NPDR",
    "Grade 4 - Proliferative DR",
]

GRADE_DETAILS = {
    0: "No DR",
    1: "Mild NPDR",
    2: "Moderate NPDR",
    3: "Severe NPDR",
    4: "Proliferative DR",
}

GRADE_DESCRIPTIONS = {
    0: "No diabetic retinopathy predicted by the screening model.",
    1: "Features consistent with mild non-proliferative diabetic retinopathy.",
    2: "Features consistent with moderate non-proliferative diabetic retinopathy.",
    3: "Features consistent with severe non-proliferative diabetic retinopathy.",
    4: "Features consistent with proliferative diabetic retinopathy.",
}


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clean_probabilities(probabilities):
    """Return five display probabilities that sum exactly to 100.00%."""
    if not isinstance(probabilities, dict):
        return {}

    values = [max(0.0, _safe_float(probabilities.get(name, 0.0))) for name in CLASS_NAMES]
    total = sum(values)
    if total <= 0:
        return {}

    values = [(v / total) * 100.0 for v in values]
    values = [round(v, 2) for v in values]
    correction = round(100.00 - sum(values), 2)
    if correction:
        largest = max(range(5), key=lambda i: values[i])
        values[largest] = round(values[largest] + correction, 2)

    return {CLASS_NAMES[i]: values[i] for i in range(5)}


def _top_two(probabilities):
    cleaned = _clean_probabilities(probabilities)
    if not cleaned:
        return []
    return sorted(cleaned.items(), key=lambda x: x[1], reverse=True)[:2]


def _status_copy(status):
    if status == "MANUAL REVIEW REQUIRED":
        return "Manual Review Required", "The AI safety layer detected a major uncertainty or disagreement."
    if status == "RECHECK REQUIRED":
        return "Recheck Required", "The result should be rechecked before relying on the screening output."
    return "Automated Screening Result", "The primary prediction passed the current prototype safety checks."


def _status_box(status):
    label, description = _status_copy(status)
    if status == "MANUAL REVIEW REQUIRED":
        st.error(f"🚨 **{label}**  ·  {description}")
    elif status == "RECHECK REQUIRED":
        st.warning(f"⚠️ **{label}**  ·  {description}")
    else:
        st.success(f"✅ **{label}**  ·  {description}")


def _display_probability_table(first_probs, tta_probs):
    first = _clean_probabilities(first_probs)
    tta = _clean_probabilities(tta_probs)
    if not first:
        st.info("Model probability data is not available for this screening.")
        return

    rows = []
    for name in CLASS_NAMES:
        fp = first.get(name, 0.0)
        tp = tta.get(name) if tta else None
        rows.append({
            "DR Grade": name,
            "Primary Model": f"{fp:.2f}%",
            "TTA Recheck": f"{tp:.2f}%" if tp is not None else "—",
            "Absolute Difference": f"{abs(fp - tp):.2f}%" if tp is not None else "—",
        })
    st.table(rows)


def _uncertainty_section(screening, grade, severity, confidence):
    status = st.session_state.get("ai_status") or "AUTOMATED SCREENING RESULT"
    recommendation = st.session_state.get("ai_recommendation") or ""
    reasons = st.session_state.get("ai_reasons") or []
    agreement = st.session_state.get("ai_agreement")
    grade_difference = st.session_state.get("ai_grade_difference")
    probability_difference = st.session_state.get("ai_probability_difference")
    probability_stable = st.session_state.get("ai_probability_stable")
    first_grade = st.session_state.get("first_pass_grade")
    first_confidence = st.session_state.get("first_pass_confidence")
    first_margin = st.session_state.get("first_pass_margin")
    tta_grade = st.session_state.get("tta_grade")
    tta_confidence = st.session_state.get("tta_confidence")
    tta_margin = st.session_state.get("tta_margin")

    first_probs = st.session_state.get("first_pass_probabilities") or st.session_state.get("ai_probabilities") or {}
    tta_probs = st.session_state.get("tta_probabilities") or {}
    first_probs = _clean_probabilities(first_probs)
    tta_probs = _clean_probabilities(tta_probs)

    _status_box(status)

    st.markdown("#### Primary prediction vs TTA verification")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Primary Grade", f"Grade {first_grade if first_grade is not None else grade}")
    with c2:
        st.metric("Primary Confidence", f"{_safe_float(first_confidence, confidence):.2f}%")
    with c3:
        st.metric("TTA Grade", f"Grade {tta_grade}" if tta_grade is not None else "—")
    with c4:
        st.metric("TTA Confidence", f"{_safe_float(tta_confidence):.2f}%" if tta_confidence is not None else "—")

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.metric("Prediction Agreement", "YES" if agreement else "NO" if agreement is not None else "—")
    with c6:
        st.metric("Grade Difference", f"{grade_difference}" if grade_difference is not None else "—")
    with c7:
        st.metric("Max Probability Shift", f"{_safe_float(probability_difference):.2f}%" if probability_difference is not None else "—")
    with c8:
        stable_text = "STABLE" if probability_stable else "UNSTABLE" if probability_stable is not None else "—"
        st.metric("Probability Stability", stable_text)

    if recommendation:
        st.info(f"**Safety recommendation:** {recommendation}")

    if reasons:
        with st.expander("Why was this result flagged?", expanded=status != "AUTOMATED SCREENING RESULT"):
            for reason in reasons:
                st.write(f"• {reason}")

    if first_probs:
        st.markdown("#### Detailed probability distribution")
        _display_probability_table(first_probs, tta_probs)

        top_first = _top_two(first_probs)
        top_tta = _top_two(tta_probs)
        u1, u2 = st.columns(2)
        with u1:
            st.markdown("**Primary model — top two classes**")
            for name, value in top_first:
                st.write(f"**{name}** — {value:.2f}%")
        with u2:
            st.markdown("**TTA recheck — top two classes**")
            if top_tta:
                for name, value in top_tta:
                    st.write(f"**{name}** — {value:.2f}%")
            else:
                st.write("TTA probabilities unavailable.")

        g3 = first_probs.get(CLASS_NAMES[3], 0.0)
        g4 = first_probs.get(CLASS_NAMES[4], 0.0)
        tg3 = tta_probs.get(CLASS_NAMES[3], 0.0)
        tg4 = tta_probs.get(CLASS_NAMES[4], 0.0)
        first_gap = abs(g3 - g4)
        tta_gap = abs(tg3 - tg4) if tta_probs else None

        st.markdown("#### Grade 3 ↔ Grade 4 boundary check")
        b1, b2 = st.columns(2)
        with b1:
            st.metric("Primary Gap", f"{first_gap:.2f}%")
            st.caption(f"Grade 3: {g3:.2f}%  |  Grade 4: {g4:.2f}%")
        with b2:
            if tta_gap is not None:
                st.metric("TTA Gap", f"{tta_gap:.2f}%")
                st.caption(f"Grade 3: {tg3:.2f}%  |  Grade 4: {tg4:.2f}%")
            else:
                st.metric("TTA Gap", "—")

        if first_gap <= 10.0 or (tta_gap is not None and tta_gap <= 10.0):
            st.warning(
                "The model is relatively close to the Grade 3 / Grade 4 boundary. "
                "Specialist review is recommended for this uncertainty region."
            )

    if first_margin is not None or tta_margin is not None:
        with st.expander("Technical confidence details"):
            if first_margin is not None:
                st.write(f"Primary probability margin: **{_safe_float(first_margin) * 100.0:.2f}%**")
            if tta_margin is not None:
                st.write(f"TTA probability margin: **{_safe_float(tta_margin) * 100.0:.2f}%**")
            st.caption(
                "These are model-output confidence measures used by the prototype safety layer. "
                "They are not clinically validated probabilities."
            )


def _probability_bars(first_probs, grade):
    probs = _clean_probabilities(first_probs)
    if not probs:
        st.info("Probability distribution is not available.")
        return

    for index, name in enumerate(CLASS_NAMES):
        value = probs.get(name, 0.0)
        label = GRADE_DETAILS[index]
        marker = "  ← predicted" if index == grade else ""
        st.markdown(f"**Grade {index} · {label}**{marker}  \n{value:.2f}%")
        st.progress(min(max(value / 100.0, 0.0), 1.0))


def show_results():
    screening_id = st.session_state.get("screening_id")
    if not screening_id:
        st.warning("No screening result is currently selected.")
        if st.button("🩺 Start New Screening", width="stretch"):
            st.session_state["current_screen"] = "screening_selection"
            st.rerun()
        return

    screening = get_screening(screening_id)
    if not screening:
        st.error(f"Screening **{screening_id}** could not be found in the database.")
        return

    patient = get_patient(screening["patient_id"])
    if not patient:
        st.error("Patient record associated with this screening could not be found.")
        return

    grade = int(screening["dr_grade"])
    severity = screening["severity"] or GRADE_DETAILS.get(grade, "Unknown")
    confidence = _safe_float(screening["confidence"])
    priority = screening["referral_priority"] or "N/A"

    live_grade = st.session_state.get("dr_grade")
    if live_grade is not None:
        try:
            grade = int(live_grade)
        except (TypeError, ValueError):
            pass
    severity = st.session_state.get("severity") or severity
    confidence = _safe_float(st.session_state.get("confidence"), confidence)
    priority = st.session_state.get("referral_priority") or priority
    status = st.session_state.get("ai_status") or "AUTOMATED SCREENING RESULT"

    # ── Header ──────────────────────────────────────────────────────────────
    st.markdown('<div class="page-kicker">AI RETINAL SCREENING</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="page-title">Screening Results</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Clinical review workspace for the AI-assisted diabetic retinopathy screening result.</div>',
        unsafe_allow_html=True,
    )

    _status_box(status)

    # ── Result hero ─────────────────────────────────────────────────────────
    left, right = st.columns([1.25, 1])
    with left:
        st.markdown("### Final AI screening result")
        g1, g2, g3 = st.columns(3)
        with g1:
            st.metric("DR Grade", f"Grade {grade}")
        with g2:
            st.metric("Severity", severity)
        with g3:
            st.metric("Confidence", f"{confidence:.2f}%")
        st.markdown(f"**Interpretation:** {GRADE_DESCRIPTIONS.get(grade, 'No interpretation available.')}")
        st.caption("The primary model prediction is retained as the final grade; TTA is used as a verification layer.")

    with right:
        st.markdown("### Screening details")
        d1, d2 = st.columns(2)
        with d1:
            st.write(f"**Screening ID**  \n{screening['screening_id']}")
            st.write(f"**Patient ID**  \n{patient['patient_id']}")
            st.write(f"**Eye**  \n{screening['eye']}")
        with d2:
            st.write(f"**Date**  \n{screening['screening_date']}")
            st.write(f"**Referral priority**  \n{priority}")
            st.write(f"**Quality status**  \n{screening['quality_status'] or 'Passed'}")

    st.divider()

    # ── Image and probability overview ──────────────────────────────────────
    image_col, probability_col = st.columns([1.05, 1])
    with image_col:
        st.markdown("### Fundus image")
        uploaded_image = st.session_state.get("uploaded_image")
        if uploaded_image is not None:
            st.image(uploaded_image, caption=screening["image_name"], width="stretch")
        else:
            st.info(f"Image: {screening['image_name']}")
            st.warning("The uploaded image is no longer available in the current session.")

    with probability_col:
        st.markdown("### AI probability distribution")
        first_probs = st.session_state.get("first_pass_probabilities") or st.session_state.get("ai_probabilities") or {}
        _probability_bars(first_probs, grade)
        st.caption("Displayed values are normalized and rounded to two decimals for presentation; underlying model probabilities are not modified.")

    st.divider()

    # ── Safety verification ──────────────────────────────────────────────────
    st.markdown("### 01 · AI safety verification")
    st.caption("A second-pass test-time augmentation (TTA) check is compared with the primary prediction before the result is classified as stable.")
    _uncertainty_section(screening, grade, severity, confidence)

    st.divider()

    # ── Severity scale ──────────────────────────────────────────────────────
    st.markdown("### 02 · Diabetic retinopathy severity scale")
    grade_cols = st.columns(5)
    for i, col in enumerate(grade_cols):
        with col:
            if i == grade:
                st.success(f"**Grade {i}**\n\n{GRADE_DETAILS[i]}")
            else:
                st.info(f"**Grade {i}**\n\n{GRADE_DETAILS[i]}")

    st.divider()

    # ── Explainability ──────────────────────────────────────────────────────
    st.markdown("### 03 · Explainable AI")
    st.caption("Grad-CAM highlights image regions that received higher model attention. It is an explanation aid, not independent clinical evidence.")
    tab1, tab2, tab3 = st.tabs(["Original", "Grad-CAM heatmap", "Attention overlay"])

    original = st.session_state.get("gradcam_original")
    overlay = st.session_state.get("gradcam_overlay")
    heatmap = st.session_state.get("gradcam_heatmap")

    with tab1:
        if original is not None:
            st.image(original, caption="Original fundus image", width="stretch")
        elif uploaded_image is not None:
            st.image(uploaded_image, caption="Original fundus image", width="stretch")
        else:
            st.info("Original image is not available in the current session.")

    with tab2:
        if heatmap is not None:
            st.image(heatmap, caption="Grad-CAM heatmap", width="stretch")
        else:
            st.info("Grad-CAM heatmap is not available for this screening session.")

    with tab3:
        if overlay is not None:
            st.image(overlay, caption="Grad-CAM attention overlay", width="stretch")
        else:
            st.info("Grad-CAM overlay is not available for this screening session.")

    with st.expander("What the AI saw"):
        st.write(
            "Grad-CAM is shown to make the model's attention pattern easier to inspect. "
            "Highlighted regions should not be interpreted as a definitive diagnosis or as proof that a specific lesion caused the prediction."
        )
        if status != "AUTOMATED SCREENING RESULT":
            st.warning("Because the safety layer flagged this screening, the AI output should be treated as a screening aid and reviewed by a qualified clinician.")

    st.divider()

    # ── Referral action ──────────────────────────────────────────────────────
    st.markdown("### 04 · Clinical follow-up")
    referral_needed = grade >= 2 or priority.upper() in {"HIGH", "URGENT", "CRITICAL"} or status != "AUTOMATED SCREENING RESULT"
    if referral_needed:
        st.warning("This screening may require clinical follow-up based on the current AI grade, referral priority, or safety status.")
        rc1, rc2 = st.columns(2)
        with rc1:
            if st.button("📋 Open Referral Management", width="stretch"):
                st.session_state["current_screen"] = "referrals"
                st.rerun()
        with rc2:
            if st.button("📅 Open Follow-ups", width="stretch"):
                st.session_state["current_screen"] = "followups"
                st.rerun()
    else:
        st.success("No elevated referral priority was generated by this screening result.")

    st.divider()

    # ── Patient context ─────────────────────────────────────────────────────
    with st.expander("Patient information", expanded=False):
        p1, p2, p3 = st.columns(3)
        with p1:
            st.write(f"**Patient ID:** {patient['patient_id']}")
            st.write(f"**Name:** {patient['name']}")
            st.write(f"**Age:** {patient['age']}")
        with p2:
            st.write(f"**Gender:** {patient['gender']}")
            st.write(f"**Diabetes:** {patient['diabetes_status']}")
            st.write(f"**Phone:** {patient['phone'] or 'N/A'}")
        with p3:
            st.write(f"**Screening ID:** {screening['screening_id']}")
            st.write(f"**Screening Date:** {screening['screening_date']}")
            st.write(f"**Eye:** {screening['eye']}")

    st.caption(
        "NetraTrace • ResNet18 AI Screening • TTA Safety Verification • Grad-CAM Explainability • Prototype for screening support, not a clinical diagnosis"
    )

    # ── Navigation ──────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🩺 New Screening", width="stretch"):
            st.session_state["current_screen"] = "screening_selection"
            st.rerun()
    with c2:
        if st.button("📋 Screening History", width="stretch"):
            st.session_state["current_screen"] = "history"
            st.rerun()
    with c3:
        if st.button("🏠 Dashboard", width="stretch"):
            st.session_state["current_screen"] = "dashboard"
            st.rerun()
