# Face Recognition Based Smart Attendance System

A Flask recreation of your final-year project, rebuilt from your project report
since the original source code was lost. It follows the same pipeline your
report documents:

- **Face detection & encoding**: `face_recognition` (dlib-based), which computes
  a 128-measurement encoding per face — this is the "CNN feature extraction"
  step described in your report.
- **Matching**: nearest-neighbour comparison using face distance + a tolerance
  threshold (`face_recognition.compare_faces`) — equivalent to the SVM-based
  classification step described in your report.
- **Storage**: your original design used Firebase Realtime Database. This
  rebuild uses a local **SQLite** database instead, so the project runs
  standalone without needing your old Firebase project/credentials. All
  attendance can still be **downloaded as an Excel (.xlsx) sheet**, exactly as
  your report describes.
- **Faculty/Admin web UI**: login, registration (gated by a confirmation key,
  as in your report), add/delete students, view all students & individual
  profiles, live camera attendance capture, attendance records, Excel
  download, and change password.

## 1. Install dependencies

```bash
cd smart_attendance_system
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**If `pip install -r requirements.txt` fails partway through** (e.g. it
downloaded Flask but then errored on a later package and nothing got
installed), it's almost always an outdated `pip` failing to resolve one of
the pinned versions. Run `python -m pip install --upgrade pip` first (as
above), then re-run the install. You can also install packages one at a time
to see exactly which one is failing:

```bash
pip install Flask openpyxl Werkzeug
pip install opencv-python
pip install numpy
pip install face_recognition
```

**Installing `dlib` / `face_recognition`** (the trickiest part):
- **Windows**: easiest via conda: `conda install -c conda-forge dlib`, then `pip install face_recognition`.
  Alternatively install "CMake" and "Visual Studio Build Tools (C++)" first, then `pip install dlib face_recognition`.
- **macOS**: `brew install cmake`, then `pip install dlib face_recognition`.
- **Linux**: `sudo apt install cmake build-essential`, then `pip install dlib face_recognition`.

The rest of the app (login, student records, Excel export) works even before
`dlib`/`face_recognition` is installed — only "Add Student" (webcam capture)
and "Take Attendance" need it.

## 2. Run the app

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

Default login (created automatically on first run):
- **Username:** `admin`
- **Password:** `admin123`

Change this immediately from the "Change Password" page.

To register an additional faculty account, use the confirmation key set in
`config.py` (`ADMIN_REGISTRATION_KEY`) — change this to something private
before you deploy the app for real use.

## 3. Typical workflow

1. **Add Student** — enter details and either upload a clear front-facing
   photo or capture one via the server's webcam. This saves the image to
   `static/student_images/<roll_no>/` and regenerates `data/EncodeFile.p`
   (the same encoding file format your original project used).
2. **Take Attendance** — opens a live camera feed; recognized students are
   automatically marked present for whichever lecture slot is currently
   active (edit the timetable in `config.py`).
3. **Attendance Records** — browse attendance by date and download it as an
   Excel sheet.

## 4. Project structure

```
smart_attendance_system/
├── app.py                # Flask routes / web app entry point
├── config.py              # paths, timetable, tunables
├── db.py                  # SQLite data access layer
├── face_utils.py           # face capture, encoding, recognition
├── timetable.py             # figures out the current lecture slot
├── excel_export.py          # builds the downloadable .xlsx sheet
├── templates/               # HTML pages (Jinja2)
├── static/
│   ├── css/style.css
│   └── student_images/      # captured/uploaded student face photos
├── data/
│   ├── attendance.db         # SQLite database (auto-created)
│   └── EncodeFile.p            # pickled face encodings (auto-created)
└── exports/                    # generated attendance .xlsx files
```

## 5. Customizing the lecture timetable

Edit `LECTURE_TIMETABLE` in `config.py` to match your actual class schedule —
attendance is tagged with whichever slot is active when a face is recognized.

## 6. Notes on fidelity to the original project

Your report's code also referenced Firebase, an IN-camera/OUT-camera pair for
duration tracking, and an XAMPP-hosted PHP front end. This rebuild keeps the
same face-recognition core but consolidates everything into a single Flask
app with one camera feed and a local database, which is simpler to run and
matches what you described wanting today (camera → attendance → Excel sheet,
plus a faculty UI for managing students). If you'd like the IN/OUT dual-camera
duration tracking or a Firebase backend added back in, let me know and I can
extend it.
