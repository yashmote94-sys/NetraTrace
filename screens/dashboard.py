import streamlit as st


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="NetraTrace | Dashboard",
    page_icon="👁️",
    layout="wide"
)


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown(
    """
<style>

.main-title {
    font-size: 32px;
    font-weight: 700;
    color: #12304a;
}

.subtitle {
    color: #64748b;
    font-size: 16px;
    margin-bottom: 25px;
}

.section-title {
    font-size: 22px;
    font-weight: 650;
    color: #172b3a;
}

.card {
    padding: 22px;
    border-radius: 15px;
    background-color: white;
    border: 1px solid #e5eaf0;
}

</style>
""",
    unsafe_allow_html=True
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title("👁️ NetraTrace")

    st.caption(
        "AI-Assisted Retinal Screening"
    )

    st.divider()

    st.subheader("Navigation")

    st.page_link(
        "dashboard.py",
        label="Dashboard",
        icon="🏠"
    )

    st.page_link(
        "screening.py",
        label="New Screening",
        icon="➕"
    )

    st.page_link(
        "patients.py",
        label="Patients",
        icon="👥"
    )

    st.page_link(
        "history.py",
        label="Screening History",
        icon="📋"
    )

    st.page_link(
        "referrals.py",
        label="Referrals",
        icon="⚠️"
    )

    st.divider()

    st.success("● Offline Mode")

    st.caption(
        "System ready for screening"
    )


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">Screening Dashboard</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'AI-assisted diabetic retinopathy screening '
    'and referral support'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# WELCOME
# =========================================================

col1, col2 = st.columns([3, 1])

with col1:

    st.markdown(
        "### Welcome to NetraTrace"
    )

    st.write(
        "Start a new retinal screening or review "
        "previous screening activity."
    )

with col2:

    if st.button(
        "➕ New Screening",
        type="primary",
        use_container_width=True
    ):

        st.switch_page(
            "pages/screening.py"
        )


# =========================================================
# STATISTICS
# =========================================================

st.divider()

st.subheader("Screening Overview")

col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "Total Screenings",
        "124",
        "+12 this week"
    )


with col2:

    st.metric(
        "High Priority",
        "18",
        "Requires review"
    )


with col3:

    st.metric(
        "Completed",
        "106",
        "85.5%"
    )


with col4:

    st.metric(
        "Follow-ups",
        "27",
        "Pending"
    )


# =========================================================
# RECENT SCREENINGS
# =========================================================

st.divider()

st.subheader("Recent Screenings")

screenings = {

    "Patient ID": [
        "NT-1024",
        "NT-1023",
        "NT-1022",
        "NT-1021",
        "NT-1020"
    ],

    "DR Grade": [
        "Moderate NPDR",
        "No DR",
        "Severe NPDR",
        "Mild NPDR",
        "No DR"
    ],

    "Confidence": [
        "91.4%",
        "97.8%",
        "88.6%",
        "94.2%",
        "98.1%"
    ],

    "Priority": [
        "HIGH",
        "LOW",
        "HIGH",
        "MEDIUM",
        "LOW"
    ],

    "Status": [
        "Completed",
        "Completed",
        "Referral",
        "Completed",
        "Completed"
    ],

    "Date": [
        "Today",
        "Today",
        "Yesterday",
        "Yesterday",
        "08 Sep 2026"
    ]
}


st.dataframe(
    screenings,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# QUICK ACTIONS
# =========================================================

st.divider()

st.subheader("Quick Actions")

col1, col2, col3 = st.columns(3)


with col1:

    if st.button(
        "📷 Start Screening",
        use_container_width=True
    ):

        st.switch_page(
            "pages/screening.py"
        )


with col2:

    if st.button(
        "📋 View History",
        use_container_width=True
    ):

        st.switch_page(
            "pages/history.py"
        )


with col3:

    if st.button(
        "⚠️ View Referrals",
        use_container_width=True
    ):

        st.switch_page(
            "pages/referrals.py"
        )


# =========================================================
# SAFETY MESSAGE
# =========================================================

st.divider()

st.info(
    "NetraTrace is an AI-assisted screening aid. "
    "It does not replace clinical diagnosis. "
    "Final clinical decisions remain with qualified "
    "healthcare professionals."
)