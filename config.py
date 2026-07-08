"""
Central configuration for the Smart Attendance System.
Keeping every path/constant in one place makes the rest of the app easy to read.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Folders -----------------------------------------------------------
DATA_DIR = os.path.join(BASE_DIR, "data")
STUDENT_IMAGES_DIR = os.path.join(BASE_DIR, "static", "student_images")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")

for folder in (DATA_DIR, STUDENT_IMAGES_DIR, EXPORTS_DIR):
    os.makedirs(folder, exist_ok=True)

# --- Files ---------------------------------------------------------------
DATABASE_PATH = os.path.join(DATA_DIR, "attendance.db")
ENCODE_FILE_PATH = os.path.join(DATA_DIR, "EncodeFile.p")   # same name/format used in the original project

# --- App settings --------------------------------------------------------
SECRET_KEY = "change-this-secret-key-before-deploying"   # used to sign session cookies

# Registration of new faculty/admin accounts requires this confirmation key,
# matching the report's "New User can register only if they have the
# confirmation key ... available to the HOD / higher authority".
ADMIN_REGISTRATION_KEY = "RMIT-IT-2024"

# Number of face samples captured per student during enrollment
IMAGES_PER_STUDENT = 5

# Recognition tuning
FACE_MATCH_TOLERANCE = 0.6          # lower = stricter match (face_recognition default is 0.6)
ATTENDANCE_COOLDOWN_SECONDS = 30    # don't re-mark the same student again within this window

# Lecture timetable used to decide which lecture slot the recognized
# attendance should be logged against (24-hour clock, HH:MM).
LECTURE_TIMETABLE = [
    {"name": "Lecture 1", "start": "09:00", "end": "10:00"},
    {"name": "Lecture 2", "start": "10:00", "end": "11:00"},
    {"name": "Break",     "start": "11:00", "end": "11:15"},
    {"name": "Lecture 3", "start": "11:15", "end": "12:15"},
    {"name": "Lecture 4", "start": "12:15", "end": "13:15"},
]
