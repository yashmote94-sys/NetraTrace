import streamlit as st

from database import (
    get_all_screenings,
    get_screening,
    get_patient,
)


# ============================================================
# DR GRADE INFORMATION
# ============================================================

GRADE_INFO = {
    0: "No DR",
    1: "Mild NPDR",
    2: "Moderate NPDR",
    3: "Severe NPDR",
    4: "Proliferative DR",
}


# ============================================================
# SHOW HISTORY
# ============================================================

def show_history():

    st.title("📜 Screening History")

    st.caption(
        "View screening records and track diabetic "
        "retinopathy progression over time."
    )

    # ========================================================
    # GET SCREENINGS
    # ========================================================

    screenings = get_all_screenings()

    if not screenings:

        st.info(
            "No screening records found."
        )

        if st.button(
            "➕ Start New Screening",
            type="primary",
            width="stretch"
        ):

            st.session_state.current_screen = (
                "screening_selection"
            )

            st.rerun()

        return

    # ========================================================
    # PATIENT FILTER
    # ========================================================

    patient_filter = st.session_state.get(
        "patient_filter",
        ""
    )

    selected_patient = None

    if patient_filter:

        selected_patient = get_patient(
            patient_filter
        )

        if selected_patient:

            st.success(
                f"👤 Showing screening history for "
                f"**{selected_patient['patient_id']} — "
                f"{selected_patient['name']}**"
            )

            if st.button(
                "✖ Clear Patient Filter",
                width="stretch"
            ):

                st.session_state[
                    "patient_filter"
                ] = ""

                st.rerun()

            st.divider()

    # ========================================================
    # SUMMARY
    # ========================================================

    st.subheader("📊 Screening Overview")

    # Filter screenings for selected patient

    if selected_patient:

        patient_screenings = [
            screening
            for screening in screenings
            if screening["patient_id"]
            == selected_patient["patient_id"]
        ]

    else:

        patient_screenings = screenings

    total_screenings = len(
        patient_screenings
    )

    # ========================================================
    # GRADE COUNTS
    # ========================================================

    grade_counts = {
        0: 0,
        1: 0,
        2: 0,
        3: 0,
        4: 0,
    }

    for screening in patient_screenings:

        try:

            grade = int(
                screening["dr_grade"]
            )

            if grade in grade_counts:
                grade_counts[grade] += 1

        except (
            TypeError,
            ValueError
        ):

            pass

    # ========================================================
    # SUMMARY METRICS
    # ========================================================

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:

        st.metric(
            "Total",
            total_screenings
        )

    with c2:

        st.metric(
            "Grade 0",
            grade_counts[0]
        )

    with c3:

        st.metric(
            "Grade 1",
            grade_counts[1]
        )

    with c4:

        st.metric(
            "Grade 2",
            grade_counts[2]
        )

    with c5:

        st.metric(
            "Grade 3",
            grade_counts[3]
        )

    with c6:

        st.metric(
            "Grade 4",
            grade_counts[4]
        )

    # ========================================================
    # PATIENT TIMELINE
    # ========================================================

    if selected_patient:

        st.divider()

        st.subheader(
            "🧬 Patient Screening Timeline"
        )

        st.caption(
            "Chronological view of this patient's "
            "screening history."
        )

        # Sort newest first

        timeline = sorted(
            patient_screenings,
            key=lambda x: str(
                x["screening_date"] or ""
            ),
            reverse=True,
        )

        if timeline:

            latest = timeline[0]

            try:
                latest_grade = int(
                    latest["dr_grade"]
                )
            except (
                TypeError,
                ValueError
            ):
                latest_grade = 0

            # --------------------------------------------
            # PATIENT OVERVIEW
            # --------------------------------------------

            st.markdown(
                "### 👤 Patient Overview"
            )

            p1, p2, p3, p4 = st.columns(4)

            with p1:

                st.metric(
                    "Patient",
                    selected_patient["name"]
                )

            with p2:

                st.metric(
                    "Screenings",
                    total_screenings
                )

            with p3:

                st.metric(
                    "Latest Grade",
                    f"Grade {latest_grade}"
                )

            with p4:

                st.metric(
                    "Latest Severity",
                    latest["severity"]
                )

            st.markdown("---")

            # --------------------------------------------
            # GRADE PROGRESSION
            # --------------------------------------------

            st.markdown(
                "### 📈 DR Grade Progression"
            )

            progression_data = {}

            for screening in reversed(
                timeline
            ):

                date = str(
                    screening["screening_date"]
                )

                try:
                    grade = int(
                        screening["dr_grade"]
                    )
                except (
                    TypeError,
                    ValueError
                ):
                    grade = 0

                progression_data[
                    date
                ] = grade

            if progression_data:

                st.line_chart(
                    progression_data,
                    y_label="DR Grade",
                    x_label="Screening Date",
                )

                st.caption(
                    "Grade scale: 0 = No DR, "
                    "1 = Mild NPDR, "
                    "2 = Moderate NPDR, "
                    "3 = Severe NPDR, "
                    "4 = Proliferative DR."
                )

            # --------------------------------------------
            # TIMELINE RECORDS
            # --------------------------------------------

            st.markdown(
                "### 🗓️ Screening Timeline"
            )

            for index, screening in enumerate(
                timeline
            ):

                try:
                    grade = int(
                        screening["dr_grade"]
                    )
                except (
                    TypeError,
                    ValueError
                ):
                    grade = 0

                severity = screening[
                    "severity"
                ]

                priority = screening[
                    "referral_priority"
                ]

                confidence = screening[
                    "confidence"
                ]

                screening_id = screening[
                    "screening_id"
                ]

                # Timeline card

                with st.container(
                    border=True
                ):

                    header1, header2 = (
                        st.columns([4, 1])
                    )

                    with header1:

                        st.markdown(
                            f"### 🩺 {screening_id}"
                        )

                        st.write(
                            f"**Date:** "
                            f"{screening['screening_date']}"
                        )

                    with header2:

                        if priority == "HIGH":

                            st.error(
                                "🔴 HIGH"
                            )

                        elif priority == "MEDIUM":

                            st.warning(
                                "🟠 MEDIUM"
                            )

                        else:

                            st.success(
                                "🟢 LOW"
                            )

                    d1, d2, d3, d4 = (
                        st.columns(4)
                    )

                    with d1:

                        st.write(
                            "**Eye**"
                        )

                        st.write(
                            screening["eye"]
                        )

                    with d2:

                        st.write(
                            "**DR Grade**"
                        )

                        st.write(
                            f"Grade {grade}"
                        )

                    with d3:

                        st.write(
                            "**Severity**"
                        )

                        st.write(
                            severity
                        )

                    with d4:

                        st.write(
                            "**Confidence**"
                        )

                        if confidence is not None:

                            st.write(
                                f"{float(confidence):.1f}%"
                            )

                    # ------------------------------------
                    # GRADE DESCRIPTION
                    # ------------------------------------

                    st.caption(
                        f"Grade {grade}: "
                        f"{GRADE_INFO.get(
                            grade,
                            'Unknown'
                        )}"
                    )

                    # ------------------------------------
                    # ACTIONS
                    # ------------------------------------

                    action1, action2 = (
                        st.columns(2)
                    )

                    with action1:

                        if st.button(
                            "👁️ View Result",
                            key=(
                                f"timeline_view_"
                                f"{screening_id}"
                            ),
                            width="stretch"
                        ):

                            st.session_state[
                                "screening_id"
                            ] = screening_id

                            st.session_state[
                                "current_screen"
                            ] = "results"

                            patient = get_patient(
                                selected_patient[
                                    "patient_id"
                                ]
                            )

                            if patient:

                                st.session_state[
                                    "patient_id"
                                ] = patient[
                                    "patient_id"
                                ]

                                st.session_state[
                                    "patient_name"
                                ] = patient[
                                    "name"
                                ]

                                st.session_state[
                                    "patient_age"
                                ] = patient[
                                    "age"
                                ]

                                st.session_state[
                                    "patient_gender"
                                ] = patient[
                                    "gender"
                                ]

                                st.session_state[
                                    "diabetes_status"
                                ] = patient[
                                    "diabetes_status"
                                ]

                            st.session_state[
                                "dr_grade"
                            ] = grade

                            st.session_state[
                                "severity"
                            ] = severity

                            st.session_state[
                                "confidence"
                            ] = confidence

                            st.session_state[
                                "referral_priority"
                            ] = priority

                            st.session_state[
                                "screening_result"
                            ] = True

                            st.rerun()

                    with action2:

                        if st.button(
                            "➕ New Screening",
                            key=(
                                f"timeline_new_"
                                f"{screening_id}"
                            ),
                            width="stretch"
                        ):

                            st.session_state[
                                "patient_id"
                            ] = selected_patient[
                                "patient_id"
                            ]

                            st.session_state[
                                "patient_name"
                            ] = selected_patient[
                                "name"
                            ]

                            st.session_state[
                                "patient_age"
                            ] = selected_patient[
                                "age"
                            ]

                            st.session_state[
                                "patient_gender"
                            ] = selected_patient[
                                "gender"
                            ]

                            st.session_state[
                                "patient_phone"
                            ] = selected_patient[
                                "phone"
                            ]

                            st.session_state[
                                "patient_email"
                            ] = selected_patient[
                                "email"
                            ]

                            st.session_state[
                                "patient_address"
                            ] = selected_patient[
                                "address"
                            ]

                            st.session_state[
                                "diabetes_status"
                            ] = selected_patient[
                                "diabetes_status"
                            ]

                            st.session_state[
                                "screening_started"
                            ] = True

                            st.session_state[
                                "current_screen"
                            ] = "screening"

                            st.rerun()

        else:

            st.info(
                "This patient has no screening records."
            )

        st.divider()

    # ========================================================
    # ALL SCREENINGS / SEARCH
    # ========================================================

    st.subheader(
        "🔎 Find Screening"
    )

    search_text = st.text_input(
        "Search",
        placeholder=(
            "Search by Screening ID, Patient ID, "
            "Patient Name or severity"
        )
    )

    filter_priority = st.selectbox(
        "Referral Priority",
        [
            "All",
            "HIGH",
            "MEDIUM",
            "LOW",
        ]
    )

    filter_grade = st.selectbox(
        "DR Grade",
        [
            "All",
            "Grade 0",
            "Grade 1",
            "Grade 2",
            "Grade 3",
            "Grade 4",
        ]
    )

    # ========================================================
    # FILTER RECORDS
    # ========================================================

    filtered_screenings = []

    for screening in screenings:

        # Patient filter

        if selected_patient:

            if (
                screening["patient_id"]
                != selected_patient["patient_id"]
            ):

                continue

        # Search filter

        if search_text.strip():

            search = (
                search_text.strip().lower()
            )

            searchable_text = " ".join(
                [
                    str(
                        screening[
                            "screening_id"
                        ] or ""
                    ),
                    str(
                        screening[
                            "patient_id"
                        ] or ""
                    ),
                    str(
                        screening[
                            "patient_name"
                        ] or ""
                    ),
                    str(
                        screening[
                            "severity"
                        ] or ""
                    ),
                    str(
                        screening[
                            "eye"
                        ] or ""
                    ),
                ]
            ).lower()

            if search not in searchable_text:

                continue

        # Priority filter

        if filter_priority != "All":

            if (
                screening[
                    "referral_priority"
                ]
                != filter_priority
            ):

                continue

        # Grade filter

        if filter_grade != "All":

            selected_grade = int(
                filter_grade.split(" ")[1]
            )

            if (
                screening["dr_grade"]
                != selected_grade
            ):

                continue

        filtered_screenings.append(
            screening
        )

    st.write(
        f"**Showing "
        f"{len(filtered_screenings)} "
        f"of {len(screenings)} screenings**"
    )

    st.divider()

    # ========================================================
    # SCREENING LIST
    # ========================================================

    if not filtered_screenings:

        st.warning(
            "No screenings match your search/filter."
        )

    else:

        for screening in filtered_screenings:

            screening_id = screening[
                "screening_id"
            ]

            patient_id = screening[
                "patient_id"
            ]

            patient_name = screening[
                "patient_name"
            ]

            with st.container(
                border=True
            ):

                header_col1, header_col2 = (
                    st.columns([3, 1])
                )

                with header_col1:

                    st.subheader(
                        f"🩺 {screening_id}"
                    )

                    st.write(
                        f"**Patient:** "
                        f"{patient_name} "
                        f"({patient_id})"
                    )

                with header_col2:

                    priority = screening[
                        "referral_priority"
                    ]

                    if priority == "HIGH":

                        st.error(
                            f"🔴 {priority}"
                        )

                    elif priority == "MEDIUM":

                        st.warning(
                            f"🟠 {priority}"
                        )

                    else:

                        st.success(
                            f"🟢 {priority}"
                        )

                col1, col2, col3, col4 = (
                    st.columns(4)
                )

                with col1:

                    st.write(
                        f"**Date**  \n"
                        f"{screening['screening_date']}"
                    )

                with col2:

                    st.write(
                        f"**Eye**  \n"
                        f"{screening['eye']}"
                    )

                with col3:

                    st.write(
                        f"**DR Grade**  \n"
                        f"Grade {screening['dr_grade']}"
                    )

                with col4:

                    st.write(
                        f"**Severity**  \n"
                        f"{screening['severity']}"
                    )

                st.write(
                    f"**Confidence:** "
                    f"{float(screening['confidence']):.1f}%"
                )

                st.write(
                    f"**Quality:** "
                    f"{screening['quality_status']}"
                )

                if st.button(
                    "👁️ View Result",
                    key=f"history_{screening_id}",
                    width="stretch"
                ):

                    st.session_state[
                        "screening_id"
                    ] = screening_id

                    st.session_state[
                        "current_screen"
                    ] = "results"

                    patient = get_patient(
                        patient_id
                    )

                    if patient:

                        st.session_state[
                            "patient_id"
                        ] = patient[
                            "patient_id"
                        ]

                        st.session_state[
                            "patient_name"
                        ] = patient[
                            "name"
                        ]

                        st.session_state[
                            "patient_age"
                        ] = patient[
                            "age"
                        ]

                        st.session_state[
                            "patient_gender"
                        ] = patient[
                            "gender"
                        ]

                        st.session_state[
                            "diabetes_status"
                        ] = patient[
                            "diabetes_status"
                        ]

                    st.session_state[
                        "dr_grade"
                    ] = screening[
                        "dr_grade"
                    ]

                    st.session_state[
                        "severity"
                    ] = screening[
                        "severity"
                    ]

                    st.session_state[
                        "confidence"
                    ] = screening[
                        "confidence"
                    ]

                    st.session_state[
                        "referral_priority"
                    ] = screening[
                        "referral_priority"
                    ]

                    st.session_state[
                        "screening_result"
                    ] = True

                    st.rerun()

    # ========================================================
    # BOTTOM BUTTONS
    # ========================================================

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "➕ New Screening",
            type="primary",
            width="stretch"
        ):

            st.session_state.current_screen = (
                "screening_selection"
            )

            st.rerun()

    with col2:

        if st.button(
            "← Dashboard",
            width="stretch"
        ):

            st.session_state.current_screen = (
                "dashboard"
            )

            st.rerun()