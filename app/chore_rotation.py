from __future__ import annotations

from datetime import date


# Only these household members participate in the automatic chore rotation.
# Parent accounts stay available for approvals, reports, and administration.
PEOPLE = ("Zara", "Jasmin", "Aria")
ROTATION_ANCHOR = date(2026, 7, 27)
ROTATION_LENGTH = len(PEOPLE)
SPECIAL_ROTATION_CHORES = ("Bathrooms", "Basement")

# Each tuple is: title, emoji, points, role slot.
# Role slot 0 is the cook role and is intentionally exclusive for that day.
# Slots 1 and 2 split the rest of the household work. Basement + Laundry stay
# together, and Bathrooms + Kitchen deep clean stay together.
CHORE_ROTATION = (
    ("Cook and dishes", "🍳", 4, 0),
    ("Counters and stove", "🧽", 1, 1),
    ("Table, chairs, and floor", "🪑", 1, 2),
    ("Bathrooms", "🛁", 3, 2),
    ("Kitchen deep clean", "🧹", 3, 2),
    ("Basement", "📦", 3, 1),
    ("Laundry", "🧺", 2, 1),
)


def _people_for_day(day: date) -> tuple[str, ...]:
    """Return the role order for a day, including the weekend adjustment."""
    day_slot = (day - ROTATION_ANCHOR).days % ROTATION_LENGTH
    ordered = tuple(PEOPLE[(day_slot + offset) % ROTATION_LENGTH] for offset in range(ROTATION_LENGTH))

    # Apply the adjustment to the whole three-day cycle so fairness stays
    # intact: every rotating member still receives each role once per cycle.
    cycle_start = rotation_cycle_start(day)
    if cycle_start.weekday() == 5:
        swap = {PEOPLE[0]: PEOPLE[1], PEOPLE[1]: PEOPLE[0]}
        ordered = tuple(swap.get(person, person) for person in ordered)

    return ordered


def chore_assignments_for(day: date, *, include_emoji: bool = True) -> list[tuple[str, str, int]]:
    """Return the deterministic chore rotation for one day."""
    people_by_role = _people_for_day(day)
    assignments: list[tuple[str, str, int]] = []

    for title, emoji, points, role_slot in CHORE_ROTATION:
        display_title = f"{emoji} {title}" if include_emoji else title
        assignments.append((display_title, people_by_role[role_slot], points))

    return assignments


def rotation_cycle_start(day: date) -> date:
    """Return the first day of the three-day rotation containing ``day``."""
    position = (day - ROTATION_ANCHOR).days % ROTATION_LENGTH
    return date.fromordinal(day.toordinal() - position)


def rotation_day_number(day: date) -> int:
    """Return the human-facing day number within the current rotation."""
    return (day - rotation_cycle_start(day)).days + 1
