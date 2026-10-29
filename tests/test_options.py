import unittest

import options


class OptionsTests(unittest.TestCase):
    def test_parse_urls_deduplicates_and_limits_results(self):
        parsed = options.parse_urls(
            "https://example.com/a, https://example.com/a\n"
            "https://example.org https://example.net https://fourth.example"
        )
        self.assertEqual(
            parsed,
            ["https://example.com/a", "https://example.org", "https://example.net"],
        )

    def test_parse_urls_ignores_non_http_links(self):
        self.assertEqual(options.parse_urls("ftp://example.com file:///tmp/a javascript:alert(1)"), [])

    def test_writing_instructions_include_language_and_document_context(self):
        result = options.writing_instructions("Executive brief", "Student", "Urdu", True)
        self.assertIn("executive brief", result)
        self.assertIn("student", result)
        self.assertIn("Urdu", result)
        self.assertIn("uploaded", result)

    def test_reader_prompt_uses_user_selected_urls(self):
        result = options.reader_prompt("robotics", "ignored search", ["https://example.com/paper"])
        self.assertIn("https://example.com/paper", result)
        self.assertNotIn("ignored search", result)


if __name__ == "__main__":
    unittest.main()
