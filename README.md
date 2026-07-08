# Face Recognition Based Smart Attendance System

This is my final year project — a web-based attendance system that uses face
recognition to automatically mark student attendance from a live camera feed,
instead of the usual manual roll call or ID-card scanning.

## What it does

- Detects and recognizes student faces from a webcam feed in real time
- Automatically marks attendance for the currently active lecture slot
- Gives faculty/admins a full web dashboard to:
  - Register new students (capture their face via webcam or upload a photo)
  - View all registered students and each student's individual profile
  - Delete a student's record
  - View attendance records by date
  - Download attendance as an Excel (`.xlsx`) sheet
  - Manage their own login (registration with a confirmation key, change password)

## Tech stack

- **Backend:** Python (Flask)
- **Face detection & recognition:** OpenCV + `face_recognition` (built on
  `dlib`), which computes a 128-measurement encoding per face and matches it
  against known students using nearest-neighbour distance comparison
- **Database:** SQLite (student records + attendance logs)
- **Frontend:** HTML/CSS with Jinja2 templates (server-rendered, no JS framework)
- **Excel export:** `openpyxl`

## Project structure

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

## Setup

```bash
git clone https://github.com/OmJagtap112/smart-attendance-system.git
cd smart-attendance-system
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**If `pip install -r requirements.txt` fails partway through** (e.g. it
downloads Flask but then errors on a later package and nothing ends up
installed), it's almost always an outdated `pip` failing to resolve one of
the versions. Upgrade pip first (as above), then re-run. You can also install
packages one at a time to see exactly which one is failing:

```bash
pip install Flask openpyxl Werkzeug
pip install opencv-python
pip install numpy
pip install face_recognition
```

`dlib` (a dependency of `face_recognition`) is the one that tends to cause
trouble, especially on Windows — see the Troubleshooting section below if you
hit any errors installing it.

## Running the app

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

A default admin account is created automatically on first run:
- **Username:** `admin`
- **Password:** `admin123`

Change this immediately from the "Change Password" page after logging in.

To register an additional faculty/admin account, you'll need the
confirmation key set in `config.py` (`ADMIN_REGISTRATION_KEY`) — change this
to something private of your own before using this for real.

## Typical workflow

1. **Add Student** — enter the student's details and either capture their
   photo via webcam or upload one. This saves the image under
   `static/student_images/<roll_no>/` and regenerates `data/EncodeFile.p`
   (the file that stores every student's face encoding).
2. **Take Attendance** — opens a live camera feed. Recognized students are
   automatically marked present for whichever lecture slot is currently
   active (edit the timetable in `config.py` to match your own schedule).
3. **Attendance Records** — browse attendance by date and download it as an
   Excel sheet.

## Customizing the lecture timetable

Edit `LECTURE_TIMETABLE` in `config.py` to match your actual class schedule.
Attendance gets tagged with whichever slot is active at the moment a face is
recognized.

## Troubleshooting (Windows)

`dlib` is the dependency that gave me the most trouble on Windows, since
`face_recognition` needs it and there usually isn't a prebuilt wheel for it.
Here's the exact sequence that fixed every issue I ran into, in the order I
hit them.

**1. `pip install -r requirements.txt` fails on `dlib` with a CMake / Visual
C++ error**

This happens because pip tries to compile `dlib` from source, which needs
Visual C++ build tools. The reliable fix is to install `dlib` via conda
instead of pip:

```bash
# Install Miniconda first: https://docs.conda.io/en/latest/miniconda.html
# Then open "Anaconda Prompt" (not a regular terminal) and run:
conda create -n attendance python=3.10 -y
conda activate attendance
conda install -c conda-forge dlib -y
pip install -r requirements.txt
```

If `conda create` fails with a `CondaToSNonInteractiveError` about Terms of
Service, accept them first:
```bash
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/msys2
```

**2. App runs, but every face-related action prints:**
```
Please install `face_recognition_models` with this command before using `face_recognition`:
pip install git+https://github.com/ageitgey/face_recognition_models
```
Install it directly (it isn't published as a normal PyPI package):
```bash
pip install git+https://github.com/ageitgey/face_recognition_models
```

**3. After that, importing it fails with `ModuleNotFoundError: No module
named 'pkg_resources'`**

`face_recognition_models` still relies on the old `pkg_resources` API, which
newer versions of `setuptools` (81+) removed. Downgrade setuptools:
```bash
pip install "setuptools<81"
```

**4. Encoding generation fails with a cuDNN error, e.g.:**
```
Error while calling ... cudnn_dlibapi.cpp:768. code: 4000, reason: A call to cuDNN failed
```
This means the conda-forge `dlib` build detected a GPU and tried to use CUDA,
but the CUDA/cuDNN setup on the machine isn't compatible with it. The
simplest fix is swapping in a prebuilt **CPU-only** `dlib` wheel instead:
```bash
pip uninstall dlib -y
pip install dlib-bin
```
Then verify both import cleanly before restarting the app:
```bash
python -c "import dlib; print('dlib OK')"
python -c "import face_recognition; print('face_recognition OK')"
```

Once those four are sorted, `python app.py` supports the full pipeline —
webcam capture in "Add Student" and live recognition in "Take Attendance".

## Notes

This project uses a local SQLite database and local Excel export so it runs
completely standalone, with no external services or API keys required —
clone it, install dependencies, and run.
