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
    def test_only_rotating_members_receive_automatic_assignments(self):
        self.assertEqual(set(rotation.PEOPLE), {"Zara", "Jasmin", "Aria"})
        self.assertNotIn("Jeremy", rotation.PEOPLE)
        self.assertNotIn("Samantha", rotation.PEOPLE)

        for offset in range(90):
            day = rotation.ROTATION_ANCHOR + timedelta(days=offset)
            assignees = {person for _title, person, _points in rotation.chore_assignments_for(day)}
            self.assertTrue(assignees <= set(rotation.PEOPLE))

    def test_every_chore_reaches_every_person_once_per_cycle(self):
        for cycle in range(12):
            per_chore = defaultdict(list)
            cycle_start = rotation.ROTATION_ANCHOR + timedelta(days=cycle * rotation.ROTATION_LENGTH)

            for offset in range(rotation.ROTATION_LENGTH):
                day = cycle_start + timedelta(days=offset)
                for title, person, _points in rotation.chore_assignments_for(day, include_emoji=False):
                    per_chore[title].append(person)

            expected_titles = {title for title, _emoji, _points, _slot in rotation.CHORE_ROTATION}
            self.assertEqual(set(per_chore), expected_titles)
            self.assertTrue(all(Counter(people) == Counter(rotation.PEOPLE) for people in per_chore.values()))

    def test_cook_and_dishes_is_the_only_assignment_for_that_person(self):
        for offset in range(180):
            day = rotation.ROTATION_ANCHOR + timedelta(days=offset)
            assignments = rotation.chore_assignments_for(day, include_emoji=False)
            cook = next(person for title, person, _points in assignments if title == "Cook and dishes")
            cook_jobs = [title for title, person, _points in assignments if person == cook]
            self.assertEqual(cook_jobs, ["Cook and dishes"])

    def test_deep_clean_jobs_stay_in_their_pairs(self):
        for offset in range(180):
            day = rotation.ROTATION_ANCHOR + timedelta(days=offset)
            assigned_to = {
                title: person
                for title, person, _points in rotation.chore_assignments_for(day, include_emoji=False)
            }
            self.assertEqual(assigned_to["Basement"], assigned_to["Laundry"])
            self.assertEqual(assigned_to["Bathrooms"], assigned_to["Kitchen deep clean"])
            self.assertNotEqual(assigned_to["Basement"], assigned_to["Bathrooms"])

    def test_saturday_cook_schedule_obeys_weekend_rule(self):
        for offset in range(365 * 2):
            day = rotation.ROTATION_ANCHOR + timedelta(days=offset)
            if day.weekday() != 5:
                continue
            assignments = rotation.chore_assignments_for(day, include_emoji=False)
            cook = next(person for title, person, _points in assignments if title == "Cook and dishes")
            self.assertNotEqual(cook, "Zara")

    def test_cycle_helpers_identify_all_three_days(self):
        for offset in range(rotation.ROTATION_LENGTH * 12):
            day = rotation.ROTATION_ANCHOR + timedelta(days=offset)
            expected_start = rotation.ROTATION_ANCHOR + timedelta(
                days=(offset // rotation.ROTATION_LENGTH) * rotation.ROTATION_LENGTH
            )
            self.assertEqual(rotation.rotation_cycle_start(day), expected_start)
            self.assertEqual(rotation.rotation_day_number(day), offset % rotation.ROTATION_LENGTH + 1)

    def test_total_workload_is_equal_over_each_three_day_cycle(self):
        for cycle in range(12):
            totals = Counter()
            cycle_start = rotation.ROTATION_ANCHOR + timedelta(days=cycle * rotation.ROTATION_LENGTH)

            for offset in range(rotation.ROTATION_LENGTH):
                day = cycle_start + timedelta(days=offset)
                daily = Counter()
                for _title, person, points in rotation.chore_assignments_for(day):
                    daily[person] += points
                    totals[person] += points
                self.assertEqual(sorted(daily.values()), [4, 6, 7])

            self.assertEqual(totals, Counter({person: 17 for person in rotation.PEOPLE}))


if __name__ == "__main__":
    unittest.main()
