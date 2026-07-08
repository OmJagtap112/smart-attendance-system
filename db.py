"""
SQLite data-access layer for the Smart Attendance System.

Three tables:
  admins       -> faculty/admin login accounts
  students     -> student master record (mirrors the "Students" node from the
                  original Firebase design in the project report)
  attendance   -> one row per (student, date, lecture) attendance mark
"""
import sqlite3
from datetime import datetime
from contextlib import contextmanager

from werkzeug.security import generate_password_hash

import config


def get_connection():
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_cursor(commit=False):
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist yet. Safe to call on every startup."""
    with get_cursor(commit=True) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                department TEXT,
                year TEXT,
                email TEXT,
                phone TEXT,
                image_path TEXT,
                encoding_ready INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no TEXT NOT NULL,
                date TEXT NOT NULL,
                lecture TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'p',
                marked_at TEXT NOT NULL,
                FOREIGN KEY (roll_no) REFERENCES students (roll_no) ON DELETE CASCADE,
                UNIQUE(roll_no, date, lecture)
            )
        """)

    # Create a default admin account on first run so the app is usable immediately.
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM admins")
        count = cur.fetchone()["c"]

    if count == 0:
        create_admin("admin", "admin123")
        print("Default admin account created -> username: admin / password: admin123")
        print("Please change this password after logging in.")


# --------------------------------------------------------------------------
# Admin accounts
# --------------------------------------------------------------------------

def create_admin(username, password):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), datetime.now().isoformat()),
        )


def get_admin_by_username(username):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM admins WHERE username = ?", (username,))
        return cur.fetchone()


def update_admin_password(username, new_password):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE admins SET password_hash = ? WHERE username = ?",
            (generate_password_hash(new_password), username),
        )


# --------------------------------------------------------------------------
# Students
# --------------------------------------------------------------------------

def add_student(roll_no, name, department, year, email, phone, image_path):
    with get_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO students (roll_no, name, department, year, email, phone, image_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (roll_no, name, department, year, email, phone, image_path, datetime.now().isoformat()))


def mark_encoding_ready(roll_no, ready=True):
    with get_cursor(commit=True) as cur:
        cur.execute("UPDATE students SET encoding_ready = ? WHERE roll_no = ?", (1 if ready else 0, roll_no))


def get_all_students():
    with get_cursor() as cur:
        cur.execute("SELECT * FROM students ORDER BY name")
        return cur.fetchall()


def get_student(roll_no):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM students WHERE roll_no = ?", (roll_no,))
        return cur.fetchone()


def delete_student(roll_no):
    with get_cursor(commit=True) as cur:
        cur.execute("DELETE FROM students WHERE roll_no = ?", (roll_no,))
        cur.execute("DELETE FROM attendance WHERE roll_no = ?", (roll_no,))


# --------------------------------------------------------------------------
# Attendance
# --------------------------------------------------------------------------

def mark_attendance(roll_no, date_str, lecture, status="p"):
    """Insert or update today's attendance row for a student+lecture. Returns True if newly marked."""
    with get_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO attendance (roll_no, date, lecture, status, marked_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(roll_no, date, lecture) DO UPDATE SET status=excluded.status, marked_at=excluded.marked_at
        """, (roll_no, date_str, lecture, status, datetime.now().isoformat()))
        return cur.rowcount > 0


def get_last_attendance_time(roll_no):
    with get_cursor() as cur:
        cur.execute(
            "SELECT marked_at FROM attendance WHERE roll_no = ? ORDER BY marked_at DESC LIMIT 1",
            (roll_no,),
        )
        row = cur.fetchone()
        return row["marked_at"] if row else None


def get_attendance_for_date(date_str):
    with get_cursor() as cur:
        cur.execute("""
            SELECT a.*, s.name FROM attendance a
            JOIN students s ON s.roll_no = a.roll_no
            WHERE a.date = ?
            ORDER BY s.name, a.lecture
        """, (date_str,))
        return cur.fetchall()


def get_attendance_for_student(roll_no):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM attendance WHERE roll_no = ? ORDER BY date DESC, lecture", (roll_no,))
        return cur.fetchall()


def get_all_attendance():
    with get_cursor() as cur:
        cur.execute("""
            SELECT a.*, s.name FROM attendance a
            JOIN students s ON s.roll_no = a.roll_no
            ORDER BY a.date DESC, s.name, a.lecture
        """)
        return cur.fetchall()


def get_distinct_dates():
    with get_cursor() as cur:
        cur.execute("SELECT DISTINCT date FROM attendance ORDER BY date DESC")
        return [row["date"] for row in cur.fetchall()]
