"""
Face Recognition Based Smart Attendance System
------------------------------------------------
Flask web app for the faculty/admin side of the project:
  - Login / registration (with confirmation key) / change password
  - Add new student (captures face images via webcam, then builds encodings)
  - View all students, view one student's profile, delete a student
  - Live "Take Attendance" camera feed that recognizes faces and marks attendance
  - View attendance records and download them as an Excel (.xlsx) sheet

Run with:  python app.py
Then open: http://localhost:5000
"""
import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash,
    Response, send_file, jsonify
)
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

import config
import db
import face_utils
import excel_export
from timetable import get_current_lecture

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

db.init_db()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user():
    return {"current_user": session.get("username")}


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return redirect(url_for("dashboard") if "username" in session else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin = db.get_admin_by_username(username)
        if admin and check_password_hash(admin["password_hash"], password):
            session["username"] = username
            return redirect(url_for("dashboard"))

        return render_template("error.html",
                                message="Invalid username or password. Please try again.")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """New faculty/admin sign-up, gated by a confirmation key from the HOD (per report 5.4)."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_key = request.form.get("confirmation_key", "")

        if confirm_key != config.ADMIN_REGISTRATION_KEY:
            flash("Invalid confirmation key. Contact the HOD / higher authority for the correct key.", "error")
            return render_template("register.html")

        if db.get_admin_by_username(username):
            flash("That username is already taken.", "error")
            return render_template("register.html")

        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("register.html")

        db.create_admin(username, password)
        flash("Account created successfully. You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        admin = db.get_admin_by_username(session["username"])
        if not check_password_hash(admin["password_hash"], current_password):
            flash("Current password is incorrect.", "error")
        elif new_password != confirm_password:
            flash("New password and confirmation do not match.", "error")
        elif len(new_password) < 4:
            flash("New password should be at least 4 characters.", "error")
        else:
            db.update_admin_password(session["username"], new_password)
            flash("Password updated successfully.", "success")
            return redirect(url_for("dashboard"))

    return render_template("change_password.html")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    students = db.get_all_students()
    today = datetime.now().strftime("%Y-%m-%d")
    today_records = db.get_attendance_for_date(today)
    present_today = len(set(r["roll_no"] for r in today_records))
    return render_template(
        "dashboard.html",
        total_students=len(students),
        present_today=present_today,
        today=today,
        current_lecture=get_current_lecture() or "No lecture scheduled right now",
    )


# ---------------------------------------------------------------------------
# Student management
# ---------------------------------------------------------------------------

@app.route("/students")
@login_required
def all_students():
    return render_template("all_students.html", students=db.get_all_students())


@app.route("/students/<roll_no>")
@login_required
def student_profile(roll_no):
    student = db.get_student(roll_no)
    if not student:
        flash("No student found with that roll number.", "error")
        return redirect(url_for("all_students"))
    records = db.get_attendance_for_student(roll_no)
    return render_template("student_profile.html", student=student, records=records)


@app.route("/add_student", methods=["GET", "POST"])
@login_required
def add_student():
    if request.method == "POST":
        roll_no = request.form.get("roll_no", "").strip()
        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        year = request.form.get("year", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()

        if not roll_no or not name:
            flash("Roll number and name are required.", "error")
            return render_template("add_student.html")

        if db.get_student(roll_no):
            flash(f"A student with roll number {roll_no} already exists.", "error")
            return render_template("add_student.html")

        image_path = None
        uploaded_file = request.files.get("photo")
        capture_mode = request.form.get("capture_mode", "upload")

        try:
            if capture_mode == "webcam":
                # Opens the server's webcam and grabs several clear face crops.
                saved_paths = face_utils.capture_face_images(roll_no)
                image_path = os.path.relpath(saved_paths[0], os.path.join(config.BASE_DIR, "static"))
            elif uploaded_file and uploaded_file.filename:
                student_dir = os.path.join(config.STUDENT_IMAGES_DIR, roll_no)
                os.makedirs(student_dir, exist_ok=True)
                filename = secure_filename(uploaded_file.filename)
                save_path = os.path.join(student_dir, filename)
                uploaded_file.save(save_path)
                image_path = os.path.relpath(save_path, os.path.join(config.BASE_DIR, "static"))
            else:
                flash("Please either capture a photo via webcam or upload one.", "error")
                return render_template("add_student.html")
        except RuntimeError as exc:
            flash(str(exc), "error")
            return render_template("add_student.html")

        db.add_student(roll_no, name, department, year, email, phone, image_path)

        try:
            face_utils.generate_encodings()
            db.mark_encoding_ready(roll_no, True)
            flash(f"Student {name} ({roll_no}) added and face encoding generated successfully.", "success")
        except RuntimeError as exc:
            flash(f"Student added, but encoding generation failed: {exc}", "error")

        return redirect(url_for("all_students"))

    return render_template("add_student.html")


@app.route("/delete_student", methods=["GET", "POST"])
@login_required
def delete_student():
    if request.method == "POST":
        roll_no = request.form.get("roll_no", "").strip()
        student = db.get_student(roll_no)
        if not student:
            flash(f"No student found with roll number {roll_no}.", "error")
        else:
            db.delete_student(roll_no)
            try:
                face_utils.generate_encodings()
            except RuntimeError:
                pass
            flash(f"Student {student['name']} ({roll_no}) deleted successfully.", "success")
        return redirect(url_for("delete_student"))

    return render_template("delete_student.html")


# ---------------------------------------------------------------------------
# Attendance capture (live camera feed)
# ---------------------------------------------------------------------------

@app.route("/take_attendance")
@login_required
def take_attendance():
    return render_template("take_attendance.html")


def _generate_attendance_frames():
    """MJPEG generator: reads the server webcam, recognizes faces, marks attendance,
    and yields annotated JPEG frames for the browser <img> tag to display."""
    import cv2

    encodings_known, roll_numbers = face_utils.load_encodings()
    cap = cv2.VideoCapture(0)

    try:
        while True:
            success, frame = cap.read()
            if not success:
                break

            if encodings_known:
                matches = face_utils.recognize_face_in_frame(frame, encodings_known, roll_numbers)
                for roll_no, (top, right, bottom, left), _distance in matches:
                    color = (0, 200, 0) if roll_no else (0, 0, 200)
                    label = roll_no if roll_no else "Unknown"
                    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                    cv2.putText(frame, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                    if roll_no:
                        _mark_if_due(roll_no)

            ok, buffer = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            frame_bytes = buffer.tobytes()
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
    finally:
        cap.release()


def _mark_if_due(roll_no):
    """Respect the cooldown window so the same student isn't re-marked every frame."""
    last = db.get_last_attendance_time(roll_no)
    if last:
        elapsed = (datetime.now() - datetime.fromisoformat(last)).total_seconds()
        if elapsed < config.ATTENDANCE_COOLDOWN_SECONDS:
            return

    lecture = get_current_lecture() or "Unscheduled"
    today = datetime.now().strftime("%Y-%m-%d")
    db.mark_attendance(roll_no, today, lecture, status="p")


@app.route("/video_feed")
@login_required
def video_feed():
    return Response(_generate_attendance_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


# ---------------------------------------------------------------------------
# Attendance records + Excel export
# ---------------------------------------------------------------------------

@app.route("/attendance")
@login_required
def attendance_record():
    dates = db.get_distinct_dates()
    selected_date = request.args.get("date") or (dates[0] if dates else None)
    records = db.get_attendance_for_date(selected_date) if selected_date else []
    return render_template("attendance_record.html", dates=dates, selected_date=selected_date, records=records)


@app.route("/download_attendance")
@login_required
def download_attendance():
    date_filter = request.args.get("date")  # None -> export everything
    filepath = excel_export.build_attendance_workbook(date_filter)
    return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
