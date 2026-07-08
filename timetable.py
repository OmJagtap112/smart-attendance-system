"""
Small helper that figures out which lecture slot "now" falls into, based on
config.LECTURE_TIMETABLE. This is the equivalent of the DetectAttendance
module referenced in the original project report.
"""
from datetime import datetime

import config


def get_current_lecture(now=None):
    """
    Returns the name of the lecture slot the current time falls in
    (e.g. "Lecture 2" or "Break"), or None if it's outside all scheduled slots.
    """
    now = now or datetime.now()
    current_time = now.strftime("%H:%M")

    for slot in config.LECTURE_TIMETABLE:
        if slot["start"] <= current_time < slot["end"]:
            return slot["name"]

    return None
