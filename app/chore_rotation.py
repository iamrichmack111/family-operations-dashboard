from __future__ import annotations

from datetime import date


PEOPLE = ("Zara", "Jasmin", "Aria")
ROTATION_ANCHOR = date(2026, 7, 27)
ROTATION_LENGTH = len(PEOPLE)
SPECIAL_ROTATION_CHORES = ("Bathrooms", "Basement")

# Chores are grouped into three balanced daily slots worth 5, 6, and 6 points.
# Those slots rotate among the three people each day. After three days, every
# person has performed every chore exactly once and has received 17 total points.
CHORE_ROTATION = (
    ("Cook and dishes", "🍳", 4, 0),
    ("Counters and stove", "🧽", 1, 2),
    ("Table, chairs, and floor", "🪑", 1, 0),
    ("Bathrooms", "🛁", 3, 2),
    ("Kitchen deep clean", "🧹", 3, 1),
    ("Basement", "📦", 3, 1),
    ("Laundry", "🧺", 2, 2),
)


def chore_assignments_for(day: date, *, include_emoji: bool = True) -> list[tuple[str, str, int]]:
    """Return the fair, deterministic chore rotation for one day."""
    day_slot = (day - ROTATION_ANCHOR).days % ROTATION_LENGTH
    assignments = []

    for title, emoji, points, person_slot in CHORE_ROTATION:
        display_title = f"{emoji} {title}" if include_emoji else title
        person = PEOPLE[(day_slot + person_slot) % ROTATION_LENGTH]
        assignments.append((display_title, person, points))

    return assignments


def rotation_cycle_start(day: date) -> date:
    """Return the first day of the three-day rotation containing ``day``."""
    position = (day - ROTATION_ANCHOR).days % ROTATION_LENGTH
    return date.fromordinal(day.toordinal() - position)


def rotation_day_number(day: date) -> int:
    """Return the human-facing day number within the current rotation."""
    return (day - rotation_cycle_start(day)).days + 1
