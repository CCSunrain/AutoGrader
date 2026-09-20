"""Role definitions.

Membership roles within a workspace:
- owner:   workspace & membership & all courses management
- teacher: courses, rubrics, review and publish
- ta:      review and submit for review, but cannot publish
- student: own report, own published feedback, revisions

The `demo` persona is NOT a membership role. It is implemented as a
`User.is_demo` flag plus an auto-created, isolated workspace where the demo
user holds the `owner` role (so they can exercise the full flow in isolation).
"""
from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    TEACHER = "teacher"
    TA = "ta"
    STUDENT = "student"


# Roles allowed to grade / review
REVIEW_ROLES = {Role.OWNER, Role.TEACHER, Role.TA}

# Roles allowed to publish final grades
PUBLISH_ROLES = {Role.OWNER, Role.TEACHER}
