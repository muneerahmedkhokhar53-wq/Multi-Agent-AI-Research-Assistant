import unittest

import documents


class DocumentTests(unittest.TestCase):
    def test_extracts_plain_text_and_cleans_null_bytes(self):
        self.assertEqual(documents.extract_text("notes.TXT", b"hello\x00 world"), "hello world")

    def test_rejects_unsupported_file_types(self):
        with self.assertRaisesRegex(ValueError, "aren't supported"):
            documents.extract_text("payload.exe", b"hello")

    def test_rejects_empty_text(self):
        with self.assertRaisesRegex(ValueError, "file is empty"):
            documents.extract_text("empty.md", b" \n ")

    def test_total_document_text_respects_requested_budget(self):
        files = [(f"doc-{index}.txt", (str(index) * 1000).encode()) for index in range(10)]
        material, rows = documents.build_material(files, budget=2000)

        self.assertEqual(sum(row["used"] for row in rows), 2000)
        self.assertLessEqual(sum(row["used"] for row in rows), 2000)
        self.assertTrue(all(row["truncated"] for row in rows))
        self.assertTrue(material)

    def test_rejects_non_positive_budget(self):
        with self.assertRaisesRegex(ValueError, "positive integer"):
            documents.build_material([("notes.txt", b"some text")], budget=0)


if __name__ == "__main__":
    unittest.main()
