"""Checks for bounded idle mouse orbit generation."""

import unittest

import idle_mouse


class IdleMouseTests(unittest.TestCase):
    def test_orbit_stays_inside_content(self):
        bounds = (100, 100, 500, 400)
        points = idle_mouse.orbit_points(300, 250, 30, 2600, 3000, start_x=120, start_y=120)
        idle_mouse.validate_points(points, bounds)
        self.assertGreater(len(points), 10)
        self.assertLessEqual(max(x for x, _ in points), 330)
        self.assertLessEqual(max(y for _, y in points), 280)

    def test_orbit_rejects_points_outside_content(self):
        points = idle_mouse.orbit_points(30, 30, 20, 2600, 1000)
        with self.assertRaisesRegex(ValueError, "outside content bounds"):
            idle_mouse.validate_points(points, (100, 100, 500, 400))

    def test_twenty_seconds_has_two_five_second_pulses(self):
        schedule, pulses = idle_mouse.orbit_schedule(
            300,
            250,
            30,
            2600,
            20000,
            active_ms=5000,
            rest_ms=5000,
            start_x=300,
            start_y=250,
        )
        self.assertEqual(pulses, 2)
        self.assertAlmostEqual(schedule[-1][0], 15000, delta=100)
        idle_mouse.validate_points([(x, y) for _, x, y in schedule], (100, 100, 500, 400))


if __name__ == "__main__":
    unittest.main()
