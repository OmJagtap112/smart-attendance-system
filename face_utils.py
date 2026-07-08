"""
Face recognition helpers.

This mirrors the pipeline described in the project report:
  1. Detect the face and compute a 128-measurement encoding for it
     (the report calls this the CNN feature-extraction step).
  2. Compare an unknown encoding against every known encoding using
     Euclidean distance and pick the closest match within a tolerance
     (the report refers to this comparison step as the SVM/classifier step;
     `face_recognition.compare_faces` implements the equivalent nearest-
     neighbour decision using face distance + tolerance threshold).
  3. Persist all known encodings to a single pickle file, EncodeFile.p,
     exactly like the original project, so it can be reloaded instantly
     without re-processing every student image on every run.

`face_recognition` (and its dlib dependency) is imported lazily inside each
function so the rest of the web app (login, student CRUD, Excel export)
still works even before that heavier dependency is installed.
"""
import os
import pickle

import cv2
import numpy as np

import config


def _face_recognition():
    try:
        import face_recognition
        return face_recognition
    except ImportError as exc:
        raise RuntimeError(
            "The 'face_recognition' package (and its 'dlib' dependency) is not installed.\n"
            "Install it with:  pip install dlib face_recognition\n"
            "See README.md for platform-specific install notes."
        ) from exc


def capture_face_images(roll_no, num_images=None, camera_index=0):
    """
    Open the webcam and save `num_images` clear frontal face crops for a
    student to static/student_images/<roll_no>/.
    Returns the list of saved file paths.
    """
    fr = _face_recognition()
    num_images = num_images or config.IMAGES_PER_STUDENT

    student_dir = os.path.join(config.STUDENT_IMAGES_DIR, roll_no)
    os.makedirs(student_dir, exist_ok=True)

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError("Could not access the webcam (camera index %d)." % camera_index)

    saved_paths = []
    try:
        while len(saved_paths) < num_images:
            success, frame = cap.read()
            if not success:
                continue

            rgb_small = cv2.resize(frame, (0, 0), None, 0.5, 0.5)
            rgb_small = cv2.cvtColor(rgb_small, cv2.COLOR_BGR2RGB)
            face_locations = fr.face_locations(rgb_small)

            if len(face_locations) == 1:
                path = os.path.join(student_dir, f"{roll_no}_{len(saved_paths) + 1}.jpg")
                cv2.imwrite(path, frame)
                saved_paths.append(path)
    finally:
        cap.release()

    return saved_paths


def generate_encodings():
    """
    Walk every student's image folder, compute a face encoding for each
    image, average them per student, and write the result to EncodeFile.p
    as (list_of_encodings, list_of_roll_numbers) - same structure the
    original project used.
    """
    fr = _face_recognition()

    encodings_known = []
    roll_numbers = []

    if not os.path.isdir(config.STUDENT_IMAGES_DIR):
        raise RuntimeError("No student images folder found yet.")

    for roll_no in sorted(os.listdir(config.STUDENT_IMAGES_DIR)):
        student_dir = os.path.join(config.STUDENT_IMAGES_DIR, roll_no)
        if not os.path.isdir(student_dir):
            continue

        per_image_encodings = []
        for filename in os.listdir(student_dir):
            if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            image_path = os.path.join(student_dir, filename)
            image = fr.load_image_file(image_path)
            encodings = fr.face_encodings(image)
            if encodings:
                per_image_encodings.append(encodings[0])

        if per_image_encodings:
            averaged = np.mean(per_image_encodings, axis=0)
            encodings_known.append(averaged)
            roll_numbers.append(roll_no)

    with open(config.ENCODE_FILE_PATH, "wb") as f:
        pickle.dump((encodings_known, roll_numbers), f)

    return roll_numbers


def load_encodings():
    if not os.path.exists(config.ENCODE_FILE_PATH):
        return [], []
    with open(config.ENCODE_FILE_PATH, "rb") as f:
        return pickle.load(f)


def recognize_face_in_frame(frame, encodings_known, roll_numbers, tolerance=None):
    """
    Given a single BGR camera frame, return the roll number of the best
    matching known student, or None if no confident match was found.
    """
    fr = _face_recognition()
    tolerance = tolerance if tolerance is not None else config.FACE_MATCH_TOLERANCE

    small = cv2.resize(frame, (0, 0), None, 0.25, 0.25)
    small_rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

    face_locations = fr.face_locations(small_rgb)
    face_encodings = fr.face_encodings(small_rgb, face_locations)

    matches_found = []
    for encode_face, face_loc in zip(face_encodings, face_locations):
        if not encodings_known:
            continue
        matches = fr.compare_faces(encodings_known, encode_face, tolerance=tolerance)
        face_distances = fr.face_distance(encodings_known, encode_face)
        best_index = int(np.argmin(face_distances))

        # Scale face location back up (it was detected on a 0.25x resized frame)
        top, right, bottom, left = [v * 4 for v in face_loc]

        if matches[best_index]:
            matches_found.append((roll_numbers[best_index], (top, right, bottom, left), face_distances[best_index]))
        else:
            matches_found.append((None, (top, right, bottom, left), face_distances[best_index]))

    return matches_found
