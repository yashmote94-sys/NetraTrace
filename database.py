import sqlite3
from datetime import datetime


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DATABASE_NAME = "netratrace.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    connection = sqlite3.connect(
        DATABASE_NAME,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database():

    connection = get_connection()
    cursor = connection.cursor()

    # ========================================================
    # PATIENTS TABLE
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS patients (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            patient_id TEXT UNIQUE NOT NULL,

            name TEXT NOT NULL,

            age INTEGER,

            gender TEXT,

            diabetes_status TEXT,

            phone TEXT,

            email TEXT,

            address TEXT,

            created_at TEXT NOT NULL,

            updated_at TEXT NOT NULL

        )
        """
    )

    # ========================================================
    # SCREENINGS TABLE
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS screenings (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            screening_id TEXT UNIQUE NOT NULL,

            patient_id TEXT NOT NULL,

            screening_date TEXT,

            eye TEXT,

            image_name TEXT,

            dr_grade INTEGER,

            severity TEXT,

            confidence REAL,

            referral_priority TEXT,

            quality_status TEXT,

            created_at TEXT NOT NULL,

            FOREIGN KEY(patient_id)
                REFERENCES patients(patient_id)
                ON DELETE CASCADE

        )
        """
    )

    # ========================================================
    # REFERRALS TABLE
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS referrals (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            referral_id TEXT UNIQUE NOT NULL,

            screening_id TEXT NOT NULL,

            patient_id TEXT NOT NULL,

            referral_date TEXT,

            priority TEXT,

            referral_type TEXT,

            doctor_name TEXT,

            facility TEXT,

            reason TEXT,

            status TEXT,

            notes TEXT,

            created_at TEXT NOT NULL,

            updated_at TEXT NOT NULL,

            FOREIGN KEY(screening_id)
                REFERENCES screenings(screening_id)
                ON DELETE CASCADE,

            FOREIGN KEY(patient_id)
                REFERENCES patients(patient_id)
                ON DELETE CASCADE

        )
        """
    )

    connection.commit()

    # ========================================================
    # REFERRAL DATABASE MIGRATION
    # ========================================================
    # Adds doctor_name to older databases if missing.
    # ========================================================

    cursor.execute(
        "PRAGMA table_info(referrals)"
    )

    referral_columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    if "doctor_name" not in referral_columns:

        cursor.execute(
            """
            ALTER TABLE referrals
            ADD COLUMN doctor_name TEXT
            """
        )

    # ========================================================
    # FOLLOW-UPS TABLE
    # ========================================================
    #
    # One referral can have one or more follow-up records.
    #
    # Patient
    #    ↓
    # Screening
    #    ↓
    # Referral
    #    ↓
    # Follow-up / Appointment
    #
    # Existing data is NOT deleted.
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS followups (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            followup_id TEXT UNIQUE NOT NULL,

            referral_id TEXT NOT NULL,

            screening_id TEXT NOT NULL,

            patient_id TEXT NOT NULL,

            doctor_name TEXT,

            facility TEXT,

            appointment_date TEXT,

            appointment_time TEXT,

            status TEXT,

            notes TEXT,

            created_at TEXT NOT NULL,

            updated_at TEXT NOT NULL,

            FOREIGN KEY(referral_id)
                REFERENCES referrals(referral_id)
                ON DELETE CASCADE,

            FOREIGN KEY(screening_id)
                REFERENCES screenings(screening_id)
                ON DELETE CASCADE,

            FOREIGN KEY(patient_id)
                REFERENCES patients(patient_id)
                ON DELETE CASCADE

        )
        """
    )

    connection.commit()
    connection.close()


# ============================================================
# PATIENT FUNCTIONS
# ============================================================


# ------------------------------------------------------------
# PATIENT EXISTS
# ------------------------------------------------------------

def patient_exists(patient_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT patient_id
        FROM patients
        WHERE patient_id = ?
        """,
        (patient_id,)
    )

    result = cursor.fetchone()

    connection.close()

    return result is not None


# ------------------------------------------------------------
# SAVE PATIENT
# ------------------------------------------------------------

def save_patient(
    patient_id,
    name,
    age,
    gender,
    diabetes_status,
    phone="",
    email="",
    address=""
):

    connection = get_connection()
    cursor = connection.cursor()

    now = datetime.now().isoformat()

    cursor.execute(
        """
        INSERT INTO patients
        (
            patient_id,
            name,
            age,
            gender,
            diabetes_status,
            phone,
            email,
            address,
            created_at,
            updated_at
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(patient_id)

        DO UPDATE SET

            name = excluded.name,

            age = excluded.age,

            gender = excluded.gender,

            diabetes_status = excluded.diabetes_status,

            phone = excluded.phone,

            email = excluded.email,

            address = excluded.address,

            updated_at = excluded.updated_at

        """,
        (
            patient_id,
            name,
            age,
            gender,
            diabetes_status,
            phone,
            email,
            address,
            now,
            now
        )
    )

    connection.commit()
    connection.close()


# ------------------------------------------------------------
# GET ALL PATIENTS
# ------------------------------------------------------------

def get_all_patients():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM patients
        ORDER BY created_at DESC
        """
    )

    patients = cursor.fetchall()

    connection.close()

    return patients


# ------------------------------------------------------------
# GET PATIENT
# ------------------------------------------------------------

def get_patient(patient_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM patients
        WHERE patient_id = ?
        """,
        (patient_id,)
    )

    patient = cursor.fetchone()

    connection.close()

    return patient


# ------------------------------------------------------------
# UPDATE PATIENT
# ------------------------------------------------------------

def update_patient(
    patient_id,
    name,
    age,
    gender,
    diabetes_status,
    phone,
    email,
    address
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE patients

        SET

            name = ?,

            age = ?,

            gender = ?,

            diabetes_status = ?,

            phone = ?,

            email = ?,

            address = ?,

            updated_at = ?

        WHERE patient_id = ?
        """,
        (
            name,
            age,
            gender,
            diabetes_status,
            phone,
            email,
            address,
            datetime.now().isoformat(),
            patient_id
        )
    )

    connection.commit()
    connection.close()


# ------------------------------------------------------------
# DELETE PATIENT
# ------------------------------------------------------------

def delete_patient(patient_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM patients
        WHERE patient_id = ?
        """,
        (patient_id,)
    )

    connection.commit()
    connection.close()


# ------------------------------------------------------------
# SEARCH PATIENTS
# ------------------------------------------------------------

def search_patients(search_text):

    connection = get_connection()
    cursor = connection.cursor()

    search_text = str(search_text).strip()

    if not search_text:

        connection.close()

        return []

    pattern = f"%{search_text}%"

    cursor.execute(
        """
        SELECT *
        FROM patients

        WHERE

            LOWER(patient_id) LIKE LOWER(?)

            OR LOWER(name) LIKE LOWER(?)

            OR phone LIKE ?

        ORDER BY created_at DESC
        """,
        (
            pattern,
            pattern,
            pattern
        )
    )

    patients = cursor.fetchall()

    connection.close()

    return patients


# ============================================================
# SCREENING FUNCTIONS
# ============================================================


# ------------------------------------------------------------
# GENERATE SCREENING ID
# ------------------------------------------------------------

def generate_screening_id():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT MAX(id)
        FROM screenings
        """
    )

    result = cursor.fetchone()

    connection.close()

    if result is None or result[0] is None:

        number = 1

    else:

        number = result[0] + 1

    return f"SCR-{number:04d}"


# ------------------------------------------------------------
# SAVE SCREENING
# ------------------------------------------------------------

def save_screening(
    screening_id,
    patient_id,
    screening_date,
    eye,
    image_name,
    dr_grade,
    severity,
    confidence,
    referral_priority,
    quality_status
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO screenings
        (
            screening_id,
            patient_id,
            screening_date,
            eye,
            image_name,
            dr_grade,
            severity,
            confidence,
            referral_priority,
            quality_status,
            created_at
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            screening_id,
            patient_id,
            str(screening_date),
            eye,
            image_name,
            dr_grade,
            severity,
            confidence,
            referral_priority,
            quality_status,
            datetime.now().isoformat()
        )
    )

    connection.commit()
    connection.close()


# ------------------------------------------------------------
# GET SCREENING
# ------------------------------------------------------------

def get_screening(screening_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM screenings
        WHERE screening_id = ?
        """,
        (screening_id,)
    )

    screening = cursor.fetchone()

    connection.close()

    return screening


# ------------------------------------------------------------
# GET ALL SCREENINGS
# ------------------------------------------------------------

def get_all_screenings():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT

            s.*,

            p.name AS patient_name

        FROM screenings s

        JOIN patients p
            ON s.patient_id = p.patient_id

        ORDER BY s.screening_date DESC
        """
    )

    screenings = cursor.fetchall()

    connection.close()

    return screenings


# ------------------------------------------------------------
# GET PATIENT SCREENINGS
# ------------------------------------------------------------

def get_patient_screenings(patient_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *

        FROM screenings

        WHERE patient_id = ?

        ORDER BY screening_date DESC
        """,
        (patient_id,)
    )

    screenings = cursor.fetchall()

    connection.close()

    return screenings


# ============================================================
# REFERRAL FUNCTIONS
# ============================================================


# ------------------------------------------------------------
# GENERATE REFERRAL ID
# ------------------------------------------------------------

def generate_referral_id():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT MAX(id)
        FROM referrals
        """
    )

    result = cursor.fetchone()

    connection.close()

    if result is None or result[0] is None:

        number = 1

    else:

        number = result[0] + 1

    return f"REF-{number:04d}"


# ------------------------------------------------------------
# SAVE REFERRAL
# ------------------------------------------------------------

def save_referral(
    referral_id,
    screening_id,
    patient_id,
    referral_date,
    priority,
    referral_type,
    doctor_name,
    facility,
    reason,
    status,
    notes
):

    connection = get_connection()
    cursor = connection.cursor()

    now = datetime.now().isoformat()

    cursor.execute(
        """
        INSERT INTO referrals
        (
            referral_id,
            screening_id,
            patient_id,
            referral_date,
            priority,
            referral_type,
            doctor_name,
            facility,
            reason,
            status,
            notes,
            created_at,
            updated_at
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            referral_id,
            screening_id,
            patient_id,
            str(referral_date),
            priority,
            referral_type,
            doctor_name,
            facility,
            reason,
            status,
            notes,
            now,
            now
        )
    )

    connection.commit()
    connection.close()


# ------------------------------------------------------------
# GET ALL REFERRALS
# ------------------------------------------------------------

def get_all_referrals():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT

            r.*,

            p.name AS patient_name

        FROM referrals r

        JOIN patients p
            ON r.patient_id = p.patient_id

        ORDER BY r.referral_date DESC
        """
    )

    referrals = cursor.fetchall()

    connection.close()

    return referrals


# ------------------------------------------------------------
# GET SINGLE REFERRAL
# ------------------------------------------------------------

def get_referral(referral_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM referrals
        WHERE referral_id = ?
        """,
        (referral_id,)
    )

    referral = cursor.fetchone()

    connection.close()

    return referral


# ------------------------------------------------------------
# UPDATE REFERRAL
# ------------------------------------------------------------

def update_referral(
    referral_id,
    referral_date,
    priority,
    referral_type,
    doctor_name,
    facility,
    reason,
    status,
    notes
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE referrals

        SET

            referral_date = ?,

            priority = ?,

            referral_type = ?,

            doctor_name = ?,

            facility = ?,

            reason = ?,

            status = ?,

            notes = ?,

            updated_at = ?

        WHERE referral_id = ?
        """,
        (
            str(referral_date),
            priority,
            referral_type,
            doctor_name,
            facility,
            reason,
            status,
            notes,
            datetime.now().isoformat(),
            referral_id
        )
    )

    connection.commit()
    connection.close()


# ------------------------------------------------------------
# DELETE REFERRAL
# ------------------------------------------------------------

def delete_referral(referral_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM referrals
        WHERE referral_id = ?
        """,
        (referral_id,)
    )

    connection.commit()
    connection.close()


# ============================================================
# FOLLOW-UP FUNCTIONS
# ============================================================


# ------------------------------------------------------------
# GENERATE FOLLOW-UP ID
# ------------------------------------------------------------

def generate_followup_id():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT MAX(id)
        FROM followups
        """
    )

    result = cursor.fetchone()

    connection.close()

    if result is None or result[0] is None:

        number = 1

    else:

        number = result[0] + 1

    return f"FUP-{number:04d}"


# ------------------------------------------------------------
# SAVE FOLLOW-UP
# ------------------------------------------------------------

def save_followup(
    followup_id,
    referral_id,
    screening_id,
    patient_id,
    doctor_name,
    facility,
    appointment_date,
    appointment_time,
    status,
    notes
):

    connection = get_connection()
    cursor = connection.cursor()

    now = datetime.now().isoformat()

    cursor.execute(
        """
        INSERT INTO followups
        (
            followup_id,
            referral_id,
            screening_id,
            patient_id,
            doctor_name,
            facility,
            appointment_date,
            appointment_time,
            status,
            notes,
            created_at,
            updated_at
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            followup_id,
            referral_id,
            screening_id,
            patient_id,
            doctor_name,
            facility,
            str(appointment_date),
            appointment_time,
            status,
            notes,
            now,
            now
        )
    )

    connection.commit()
    connection.close()


# ------------------------------------------------------------
# GET ALL FOLLOW-UPS
# ------------------------------------------------------------

def get_all_followups():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT

            f.*,

            p.name AS patient_name,

            r.priority AS referral_priority,

            r.referral_type,

            r.reason AS referral_reason

        FROM followups f

        JOIN patients p
            ON f.patient_id = p.patient_id

        LEFT JOIN referrals r
            ON f.referral_id = r.referral_id

        ORDER BY
            f.appointment_date ASC,
            f.appointment_time ASC
        """
    )

    followups = cursor.fetchall()

    connection.close()

    return followups


# ------------------------------------------------------------
# GET SINGLE FOLLOW-UP
# ------------------------------------------------------------

def get_followup(followup_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT

            f.*,

            p.name AS patient_name,

            r.priority AS referral_priority,

            r.referral_type,

            r.reason AS referral_reason

        FROM followups f

        JOIN patients p
            ON f.patient_id = p.patient_id

        LEFT JOIN referrals r
            ON f.referral_id = r.referral_id

        WHERE f.followup_id = ?
        """,
        (followup_id,)
    )

    followup = cursor.fetchone()

    connection.close()

    return followup


# ------------------------------------------------------------
# GET FOLLOW-UPS FOR A REFERRAL
# ------------------------------------------------------------

def get_referral_followups(referral_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT

            f.*,

            p.name AS patient_name

        FROM followups f

        JOIN patients p
            ON f.patient_id = p.patient_id

        WHERE f.referral_id = ?

        ORDER BY
            f.appointment_date ASC,
            f.appointment_time ASC
        """,
        (referral_id,)
    )

    followups = cursor.fetchall()

    connection.close()

    return followups


# ------------------------------------------------------------
# GET PATIENT FOLLOW-UPS
# ------------------------------------------------------------

def get_patient_followups(patient_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT

            f.*,

            p.name AS patient_name,

            r.priority AS referral_priority

        FROM followups f

        JOIN patients p
            ON f.patient_id = p.patient_id

        LEFT JOIN referrals r
            ON f.referral_id = r.referral_id

        WHERE f.patient_id = ?

        ORDER BY
            f.appointment_date ASC,
            f.appointment_time ASC
        """,
        (patient_id,)
    )

    followups = cursor.fetchall()

    connection.close()

    return followups


# ------------------------------------------------------------
# UPDATE FOLLOW-UP
# ------------------------------------------------------------

def update_followup(
    followup_id,
    appointment_date,
    appointment_time,
    doctor_name,
    facility,
    status,
    notes
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE followups

        SET

            appointment_date = ?,

            appointment_time = ?,

            doctor_name = ?,

            facility = ?,

            status = ?,

            notes = ?,

            updated_at = ?

        WHERE followup_id = ?
        """,
        (
            str(appointment_date),
            appointment_time,
            doctor_name,
            facility,
            status,
            notes,
            datetime.now().isoformat(),
            followup_id
        )
    )

    connection.commit()
    connection.close()


# ------------------------------------------------------------
# DELETE FOLLOW-UP
# ------------------------------------------------------------

def delete_followup(followup_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM followups

        WHERE followup_id = ?
        """,
        (followup_id,)
    )

    connection.commit()
    connection.close()


# ============================================================
# INITIALIZE DATABASE
# ============================================================

initialize_database()