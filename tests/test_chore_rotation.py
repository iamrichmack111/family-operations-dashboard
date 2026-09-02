from collections import Counter, defaultdict
from datetime import timedelta
import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).parents[1] / "app" / "chore_rotation.py"
SPEC = importlib.util.spec_from_file_location("chore_rotation", MODULE_PATH)
rotation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rotation)


class ChoreRotationTests(unittest.TestCase):
    def test_every_chore_reaches_every_person_once_per_cycle(self):
        per_chore = defaultdict(list)

        for offset in range(len(rotation.PEOPLE)):
            day = rotation.ROTATION_ANCHOR + timedelta(days=offset)
            for title, person, _points in rotation.chore_assignments_for(day, include_emoji=False):
                per_chore[title].append(person)

        expected_titles = {title for title, _emoji, _points, _slot in rotation.CHORE_ROTATION}
        self.assertEqual(set(per_chore), expected_titles)
        self.assertTrue(all(Counter(people) == Counter(rotation.PEOPLE) for people in per_chore.values()))

    def test_basement_alternates_without_repeating_until_everyone_has_a_turn(self):
        basement_people = []

        for offset in range(len(rotation.PEOPLE) * 2):
            day = rotation.ROTATION_ANCHOR + timedelta(days=offset)
            assignments = rotation.chore_assignments_for(day, include_emoji=False)
            basement_people.append(next(person for title, person, _points in assignments if title == "Basement"))

        self.assertEqual(basement_people[:3], basement_people[3:])
        self.assertEqual(Counter(basement_people[:3]), Counter(rotation.PEOPLE))

    def test_basement_and_bathrooms_each_reach_everyone_once_per_rotation(self):
        for cycle in range(4):
            special = {"Basement": [], "Bathrooms": []}
            cycle_start = rotation.ROTATION_ANCHOR + timedelta(
                days=cycle * rotation.ROTATION_LENGTH
            )

            for offset in range(rotation.ROTATION_LENGTH):
                assignments = dict(
                    (title, person)
                    for title, person, _points in rotation.chore_assignments_for(
                        cycle_start + timedelta(days=offset),
                        include_emoji=False,
                    )
                )
                special["Basement"].append(assignments["Basement"])
                special["Bathrooms"].append(assignments["Bathrooms"])
                self.assertNotEqual(
                    assignments["Basement"],
                    assignments["Bathrooms"],
                )

            self.assertEqual(Counter(special["Basement"]), Counter(rotation.PEOPLE))
            self.assertEqual(Counter(special["Bathrooms"]), Counter(rotation.PEOPLE))

    def test_cycle_helpers_identify_all_three_days(self):
        for offset in range(rotation.ROTATION_LENGTH * 2):
            day = rotation.ROTATION_ANCHOR + timedelta(days=offset)
            expected_start = rotation.ROTATION_ANCHOR + timedelta(
                days=(offset // rotation.ROTATION_LENGTH) * rotation.ROTATION_LENGTH
            )
            self.assertEqual(rotation.rotation_cycle_start(day), expected_start)
            self.assertEqual(
                rotation.rotation_day_number(day),
                offset % rotation.ROTATION_LENGTH + 1,
            )

    def test_cook_and_counters_are_never_assigned_to_the_same_person(self):
        for offset in range(len(rotation.PEOPLE) * 2):
            day = rotation.ROTATION_ANCHOR + timedelta(days=offset)
            assignments = rotation.chore_assignments_for(day, include_emoji=False)
            assigned_to = {title: person for title, person, _points in assignments}

            self.assertNotEqual(
                assigned_to["Cook and dishes"],
                assigned_to["Counters and stove"],
            )

    def test_total_workload_is_equal_over_each_three_day_cycle(self):
        totals = Counter()

        for offset in range(len(rotation.PEOPLE)):
            day = rotation.ROTATION_ANCHOR + timedelta(days=offset)
            daily = Counter()
            for _title, person, points in rotation.chore_assignments_for(day):
                daily[person] += points
                totals[person] += points

            self.assertEqual(sorted(daily.values()), [5, 6, 6])

        self.assertEqual(totals, Counter({person: 17 for person in rotation.PEOPLE}))


if __name__ == "__main__":
    unittest.main()
