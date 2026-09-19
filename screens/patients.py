import streamlit as st
from PIL import Image

from database import (
    save_patient,
    get_all_patients,
    get_patient,
    update_patient,
    delete_patient,
    get_patient_screenings,
    search_patients,
    generate_screening_id,
    save_screening,
)


# ============================================================
# FUNDUS IMAGE ANALYSIS
# ============================================================

def analyze_fundus_image(uploaded_file):

    try:

        image = Image.open(uploaded_file)

        width, height = image.size

        # Basic image quality gate
        if width < 300 or height < 300:

            return {
                "quality_status": "Poor Quality",
                "dr_grade": 0,
                "severity": "No DR",
                "confidence": 50.0,
                "referral_priority": "LOW",
            }

        # ----------------------------------------------------
        # PROTOTYPE AI RESULT
        # Replace this section later with actual AI model
        # ----------------------------------------------------

        return {
            "quality_status": "Good Quality",
            "dr_grade": 3,
            "severity": "Severe NPDR",
            "confidence": 91.4,
            "referral_priority": "HIGH",
        }

    except Exception:

        return {
            "quality_status": "Invalid Image",
            "dr_grade": 0,
            "severity": "Unable to Analyze",
            "confidence": 0.0,
            "referral_priority": "LOW",
        }


# ============================================================
# MAIN PATIENT SCREEN
# ============================================================

def show_patients():

    st.title("👥 Patient Information")
    st.caption(
        "Manage patients, fundus images and screening records"
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "📋 Patient Records",
            "➕ Add Patient",
            "🔎 Search Patient",
        ]
    )

    # ========================================================
    # TAB 1 — PATIENT RECORDS
    # ========================================================

    with tab1:

        patients = get_all_patients()

        if not patients:

            st.info("No patient records found.")

        else:

            st.subheader("All Patients")

            for patient in patients:

                patient_id = patient["patient_id"]

                with st.container(border=True):

                    col1, col2, col3, col4 = st.columns(
                        [2, 3, 2, 1]
                    )

                    with col1:

                        st.markdown(
                            f"**{patient_id}**"
                        )

                    with col2:

                        st.markdown(
                            f"**{patient['name']}**"
                        )

                        st.caption(
                            f"Age: {patient['age']} | "
                            f"Gender: {patient['gender']}"
                        )

                    with col3:

                        screenings = get_patient_screenings(
                            patient_id
                        )

                        st.caption(
                            f"Diabetes: "
                            f"{patient['diabetes_status']}"
                        )

                        st.caption(
                            f"Screenings: {len(screenings)}"
                        )

                    with col4:

                        if st.button(
                            "✏️ Edit",
                            key=f"edit_{patient_id}",
                        ):

                            st.session_state[
                                "edit_patient_id"
                            ] = patient_id

                            st.rerun()

                    # ------------------------------------------------
                    # EDIT PATIENT
                    # ------------------------------------------------

                    if (
                        st.session_state.get(
                            "edit_patient_id"
                        )
                        == patient_id
                    ):

                        st.markdown("---")

                        st.subheader(
                            f"Edit Patient — {patient_id}"
                        )

                        with st.form(
                            f"edit_form_{patient_id}"
                        ):

                            c1, c2 = st.columns(2)

                            with c1:

                                name = st.text_input(
                                    "Patient Name",
                                    value=patient["name"],
                                )

                                age = st.number_input(
                                    "Age",
                                    min_value=0,
                                    max_value=120,
                                    value=(
                                        patient["age"]
                                        if patient["age"] is not None
                                        else 0
                                    ),
                                )

                                gender_options = [
                                    "Male",
                                    "Female",
                                    "Other",
                                ]

                                current_gender = (
                                    patient["gender"]
                                    if patient["gender"]
                                    in gender_options
                                    else "Male"
                                )

                                gender = st.selectbox(
                                    "Gender",
                                    gender_options,
                                    index=gender_options.index(
                                        current_gender
                                    ),
                                )

                                diabetes_options = [
                                    "Diabetic",
                                    "Non-Diabetic",
                                    "Unknown",
                                ]

                                current_diabetes = (
                                    patient[
                                        "diabetes_status"
                                    ]
                                    if patient[
                                        "diabetes_status"
                                    ]
                                    in diabetes_options
                                    else "Unknown"
                                )

                                diabetes_status = (
                                    st.selectbox(
                                        "Diabetes Status",
                                        diabetes_options,
                                        index=diabetes_options.index(
                                            current_diabetes
                                        ),
                                    )
                                )

                            with c2:

                                phone = st.text_input(
                                    "Phone",
                                    value=(
                                        patient["phone"]
                                        or ""
                                    ),
                                )

                                email = st.text_input(
                                    "Email",
                                    value=(
                                        patient["email"]
                                        or ""
                                    ),
                                )

                                address = st.text_area(
                                    "Address",
                                    value=(
                                        patient["address"]
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

                            if not name.strip():

                                st.error(
                                    "Patient name is required."
                                )

                            else:

                                update_patient(
                                    patient_id,
                                    name.strip(),
                                    age,
                                    gender,
                                    diabetes_status,
                                    phone.strip(),
                                    email.strip(),
                                    address.strip(),
                                )

                                st.session_state[
                                    "edit_patient_id"
                                ] = None

                                st.success(
                                    "Patient updated successfully."
                                )

                                st.rerun()

                        if st.button(
                            "Cancel",
                            key=f"cancel_{patient_id}",
                        ):

                            st.session_state[
                                "edit_patient_id"
                            ] = None

                            st.rerun()

                    # ------------------------------------------------
                    # ACTION BUTTONS
                    # ------------------------------------------------

                    c1, c2, c3 = st.columns(3)

                    with c1:

                        if st.button(
                            "🩺 New Screening",
                            key=f"screen_{patient_id}",
                            width="stretch",
                        ):

                            st.session_state[
                                "patient_id"
                            ] = patient_id

                            st.session_state[
                                "patient_name"
                            ] = patient["name"]

                            st.session_state[
                                "patient_age"
                            ] = patient["age"]

                            st.session_state[
                                "patient_gender"
                            ] = patient["gender"]

                            st.session_state[
                                "patient_phone"
                            ] = patient["phone"] or ""

                            st.session_state[
                                "patient_email"
                            ] = patient["email"] or ""

                            st.session_state[
                                "patient_address"
                            ] = patient["address"] or ""

                            st.session_state[
                                "diabetes_status"
                            ] = patient[
                                "diabetes_status"
                            ]

                            st.session_state[
                                "screening_started"
                            ] = True

                            st.session_state[
                                "current_screen"
                            ] = "screening"

                            st.rerun()

                    with c2:

                        if st.button(
                            "📊 View Screenings",
                            key=f"history_{patient_id}",
                            width="stretch",
                        ):

                            st.session_state[
                                "patient_filter"
                            ] = patient_id

                            st.session_state[
                                "current_screen"
                            ] = "history"

                            st.rerun()

                    with c3:

                        if st.button(
                            "🗑️ Delete",
                            key=f"delete_{patient_id}",
                            width="stretch",
                        ):

                            st.session_state[
                                "confirm_delete_patient"
                            ] = patient_id

                            st.rerun()

                    # ------------------------------------------------
                    # DELETE CONFIRMATION
                    # ------------------------------------------------

                    if (
                        st.session_state.get(
                            "confirm_delete_patient"
                        )
                        == patient_id
                    ):

                        st.warning(
                            "Deleting this patient will also "
                            "delete their screenings and referrals."
                        )

                        d1, d2 = st.columns(2)

                        with d1:

                            if st.button(
                                "⚠️ Confirm Delete",
                                key=f"yes_delete_{patient_id}",
                                width="stretch",
                            ):

                                delete_patient(patient_id)

                                st.session_state[
                                    "confirm_delete_patient"
                                ] = None

                                st.success(
                                    "Patient deleted successfully."
                                )

                                st.rerun()

                        with d2:

                            if st.button(
                                "Cancel",
                                key=f"no_delete_{patient_id}",
                                width="stretch",
                            ):

                                st.session_state[
                                    "confirm_delete_patient"
                                ] = None

                                st.rerun()

    # ========================================================
    # TAB 2 — ADD PATIENT
    # ========================================================

    with tab2:

        st.subheader("➕ Add New Patient")

        st.info(
            "You can optionally upload a fundus image while "
            "creating the patient. The image will be analyzed "
            "and saved as a screening record."
        )

        # ----------------------------------------------------
        # PATIENT INFORMATION
        # ----------------------------------------------------

        with st.form("add_patient_form"):

            st.markdown("### 👤 Patient Details")

            c1, c2 = st.columns(2)

            with c1:

                patient_id = st.text_input(
                    "Patient ID *",
                    placeholder="Example: NT-001",
                )

                name = st.text_input(
                    "Patient Name *",
                    placeholder="Enter full name",
                )

                age = st.number_input(
                    "Age",
                    min_value=0,
                    max_value=120,
                    value=18,
                )

                gender = st.selectbox(
                    "Gender",
                    [
                        "Male",
                        "Female",
                        "Other",
                    ],
                )

                diabetes_status = st.selectbox(
                    "Diabetes Status",
                    [
                        "Diabetic",
                        "Non-Diabetic",
                        "Unknown",
                    ],
                )

            with c2:

                phone = st.text_input(
                    "Phone",
                    placeholder="Enter phone number",
                )

                email = st.text_input(
                    "Email",
                    placeholder="Enter email",
                )

                address = st.text_area(
                    "Address",
                    placeholder="Enter address",
                )

            # ------------------------------------------------
            # FUNDUS IMAGE
            # ------------------------------------------------

            st.markdown("---")

            st.markdown(
                "### 👁️ Fundus Image & Analysis"
            )

            uploaded_file = st.file_uploader(
                "Upload Fundus Image (Optional)",
                type=[
                    "jpg",
                    "jpeg",
                    "png",
                ],
                help=(
                    "Upload a retinal fundus image "
                    "for screening analysis."
                ),
            )

            screening_eye = st.selectbox(
                "Eye",
                [
                    "Right Eye",
                    "Left Eye",
                    "Both Eyes",
                ],
            )

            screening_date = st.date_input(
                "Screening Date"
            )

            # ------------------------------------------------
            # SUBMIT
            # ------------------------------------------------

            submitted = st.form_submit_button(
                "💾 Save Patient & Analyze",
                width="stretch",
            )

        # ====================================================
        # PROCESS FORM
        # ====================================================

        if submitted:

            if not patient_id.strip():

                st.error(
                    "Patient ID is required."
                )

            elif not name.strip():

                st.error(
                    "Patient name is required."
                )

            elif get_patient(patient_id.strip()):

                st.error(
                    f"Patient ID {patient_id.strip()} "
                    "already exists."
                )

            else:

                # --------------------------------------------
                # SAVE PATIENT
                # --------------------------------------------

                save_patient(
                    patient_id=patient_id.strip(),
                    name=name.strip(),
                    age=age,
                    gender=gender,
                    diabetes_status=diabetes_status,
                    phone=phone.strip(),
                    email=email.strip(),
                    address=address.strip(),
                )

                st.success(
                    f"Patient {patient_id.strip()} "
                    "saved successfully."
                )

                # --------------------------------------------
                # IF IMAGE UPLOADED
                # --------------------------------------------

                if uploaded_file is not None:

                    st.markdown("---")

                    st.subheader(
                        "🔬 Fundus Image Analysis"
                    )

                    # Display uploaded image
                    st.image(
                        uploaded_file,
                        caption=uploaded_file.name,
                        width="stretch",
                    )

                    # Analyze
                    result = analyze_fundus_image(
                        uploaded_file
                    )

                    st.markdown(
                        "### Analysis Result"
                    )

                    r1, r2, r3, r4 = st.columns(4)

                    with r1:

                        st.metric(
                            "DR Grade",
                            result["dr_grade"],
                        )

                    with r2:

                        st.metric(
                            "Severity",
                            result["severity"],
                        )

                    with r3:

                        st.metric(
                            "Confidence",
                            f"{result['confidence']:.1f}%",
                        )

                    with r4:

                        st.metric(
                            "Priority",
                            result[
                                "referral_priority"
                            ],
                        )

                    st.write(
                        f"**Image Quality:** "
                        f"{result['quality_status']}"
                    )

                    # ----------------------------------------
                    # SAVE SCREENING
                    # ----------------------------------------

                    screening_id = (
                        generate_screening_id()
                    )

                    save_screening(
                        screening_id,
                        patient_id.strip(),
                        screening_date.isoformat(),
                        screening_eye,
                        uploaded_file.name,
                        result["dr_grade"],
                        result["severity"],
                        result["confidence"],
                        result[
                            "referral_priority"
                        ],
                        result["quality_status"],
                    )

                    st.success(
                        f"Screening {screening_id} "
                        "saved successfully."
                    )

                    st.info(
                        "The patient and fundus screening "
                        "are now linked."
                    )

                    # ----------------------------------------
                    # STORE SESSION DATA
                    # ----------------------------------------

                    st.session_state[
                        "screening_id"
                    ] = screening_id

                    st.session_state[
                        "patient_id"
                    ] = patient_id.strip()

                    st.session_state[
                        "patient_name"
                    ] = name.strip()

                    st.session_state[
                        "dr_grade"
                    ] = result["dr_grade"]

                    st.session_state[
                        "severity"
                    ] = result["severity"]

                    st.session_state[
                        "confidence"
                    ] = result["confidence"]

                    st.session_state[
                        "referral_priority"
                    ] = result[
                        "referral_priority"
                    ]

                    st.session_state[
                        "quality_status"
                    ] = result[
                        "quality_status"
                    ]

                    st.session_state[
                        "screening_result"
                    ] = True

                    # ----------------------------------------
                    # GO TO RESULT
                    # ----------------------------------------

                    if st.button(
                        "📊 View Full Analysis Result",
                        width="stretch",
                    ):

                        st.session_state[
                            "current_screen"
                        ] = "results"

                        st.rerun()

                else:

                    st.info(
                        "Patient saved. No fundus image "
                        "was uploaded, so no screening "
                        "was created."
                    )

    # ========================================================
    # TAB 3 — SEARCH PATIENT
    # ========================================================

    with tab3:

        st.subheader("🔎 Search Patient")

        st.write(
            "Search by Patient ID, name or phone number."
        )

        # ----------------------------------------------------
        # SEARCH INPUT
        # ----------------------------------------------------

        search_text = st.text_input(
            "Patient Search",
            placeholder=(
                "Type Patient ID, name or phone number..."
            ),
            key="patient_search_box",
        )

        # ----------------------------------------------------
        # SEARCH BUTTON
        # ----------------------------------------------------

        search_clicked = st.button(
            "🔍 Search",
            key="patient_search_button",
            width="stretch",
        )

        # Also search automatically when text is entered
        if search_text.strip():

            results = search_patients(
                search_text.strip()
            )

        elif search_clicked:

            results = []

        else:

            results = []

        # ----------------------------------------------------
        # DISPLAY RESULTS
        # ----------------------------------------------------

        if search_text.strip():

            if not results:

                st.warning(
                    f"No patient found for "
                    f"'{search_text.strip()}'."
                )

                # Show available patients to help debugging
                st.caption(
                    "Check the Patient ID, name or phone "
                    "number and try again."
                )

            else:

                st.success(
                    f"{len(results)} patient(s) found."
                )

                for patient in results:

                    patient_id = patient[
                        "patient_id"
                    ]

                    screenings = (
                        get_patient_screenings(
                            patient_id
                        )
                    )

                    with st.container(
                        border=True
                    ):

                        st.markdown(
                            f"### 🧑 {patient_id} — "
                            f"{patient['name']}"
                        )

                        c1, c2, c3, c4 = (
                            st.columns(4)
                        )

                        with c1:

                            st.write(
                                f"**Age:** "
                                f"{patient['age']}"
                            )

                        with c2:

                            st.write(
                                f"**Gender:** "
                                f"{patient['gender']}"
                            )

                        with c3:

                            st.write(
                                f"**Diabetes:** "
                                f"{patient['diabetes_status']}"
                            )

                        with c4:

                            st.write(
                                f"**Screenings:** "
                                f"{len(screenings)}"
                            )

                        st.markdown("---")

                        b1, b2, b3 = st.columns(3)

                        # ------------------------------------
                        # NEW SCREENING
                        # ------------------------------------

                        with b1:

                            if st.button(
                                "🩺 New Screening",
                                key=(
                                    f"search_screen_"
                                    f"{patient_id}"
                                ),
                                width="stretch",
                            ):

                                st.session_state[
                                    "patient_id"
                                ] = patient_id

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
                                    "patient_phone"
                                ] = (
                                    patient[
                                        "phone"
                                    ]
                                    or ""
                                )

                                st.session_state[
                                    "patient_email"
                                ] = (
                                    patient[
                                        "email"
                                    ]
                                    or ""
                                )

                                st.session_state[
                                    "patient_address"
                                ] = (
                                    patient[
                                        "address"
                                    ]
                                    or ""
                                )

                                st.session_state[
                                    "diabetes_status"
                                ] = patient[
                                    "diabetes_status"
                                ]

                                st.session_state[
                                    "screening_started"
                                ] = True

                                st.session_state[
                                    "current_screen"
                                ] = "screening"

                                st.rerun()

                        # ------------------------------------
                        # VIEW SCREENINGS
                        # ------------------------------------

                        with b2:

                            if st.button(
                                "📊 View Screenings",
                                key=(
                                    f"search_view_"
                                    f"{patient_id}"
                                ),
                                width="stretch",
                            ):

                                st.session_state[
                                    "patient_filter"
                                ] = patient_id

                                st.session_state[
                                    "current_screen"
                                ] = "history"

                                st.rerun()

                        # ------------------------------------
                        # EDIT PATIENT
                        # ------------------------------------

                        with b3:

                            if st.button(
                                "✏️ Edit Patient",
                                key=(
                                    f"search_edit_"
                                    f"{patient_id}"
                                ),
                                width="stretch",
                            ):

                                st.session_state[
                                    "edit_patient_id"
                                ] = patient_id

                                st.session_state[
                                    "current_screen"
                                ] = "patients"

                                st.rerun()

                        # ------------------------------------
                        # PATIENT DETAILS
                        # ------------------------------------

                        with st.expander(
                            "👤 Patient Details"
                        ):

                            st.write(
                                f"**Patient ID:** "
                                f"{patient['patient_id']}"
                            )

                            st.write(
                                f"**Name:** "
                                f"{patient['name']}"
                            )

                            st.write(
                                f"**Age:** "
                                f"{patient['age']}"
                            )

                            st.write(
                                f"**Gender:** "
                                f"{patient['gender']}"
                            )

                            st.write(
                                f"**Diabetes Status:** "
                                f"{patient['diabetes_status']}"
                            )

                            st.write(
                                f"**Phone:** "
                                f"{patient['phone'] or 'Not provided'}"
                            )

                            st.write(
                                f"**Email:** "
                                f"{patient['email'] or 'Not provided'}"
                            )

                            st.write(
                                f"**Address:** "
                                f"{patient['address'] or 'Not provided'}"
                            )

                        # ------------------------------------
                        # SCREENING HISTORY
                        # ------------------------------------

                        if screenings:

                            with st.expander(
                                "📋 Screening History"
                            ):

                                for screening in screenings:

                                    st.write(
                                        f"**{screening['screening_id']}** "
                                        f"| "
                                        f"{screening['screening_date']} "
                                        f"| "
                                        f"{screening['eye']} "
                                        f"| "
                                        f"Grade "
                                        f"{screening['dr_grade']} "
                                        f"| "
                                        f"{screening['severity']} "
                                        f"| "
                                        f"{screening['referral_priority']}"
                                    )