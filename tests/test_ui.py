import unittest

import ui


class UiTests(unittest.TestCase):
    def test_parse_score_extracts_and_clamps_score(self):
        score, remaining = ui.parse_score("Score: 12/10\n\nStrengths:\n- Clear")
        self.assertEqual(score, 10.0)
        self.assertIn("Strengths", remaining)
        self.assertNotIn("Score: 12/10", remaining)

    def test_parse_score_handles_missing_score(self):
        feedback = "No score was provided."
        self.assertEqual(ui.parse_score(feedback), (None, feedback))

    def test_result_heading_escapes_untrusted_topic(self):
        result = ui.result_head_html("<script>alert(1)</script>", 3.2, ["Student"])
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)

    def test_route_shows_running_step_accessibly(self):
        result = ui.route_html({"search": "running"})
        self.assertIn('aria-current="step"', result)
        self.assertIn("Working", result)
        self.assertIn("Search agent", result)


if __name__ == "__main__":
    unittest.main()
