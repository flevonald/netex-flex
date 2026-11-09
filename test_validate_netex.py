import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import validate_netex


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.directory_path = Path(self.directory.name)
        self.schema = self.directory_path / "schema.xsd"
        self.schema.write_text(
            '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
            '<xs:element name="count" type="xs:integer"/>'
            '</xs:schema>', encoding="utf-8"
        )
        self.xml = self.directory_path / "input.xml"

    def run_validation(self, content):
        self.xml.write_text(content, encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = validate_netex.validate(self.xml, self.schema)
        return result, output.getvalue()

    def test_valid_document(self):
        result, output = self.run_validation("<count>42</count>")
        self.assertEqual(result, 0)
        self.assertIn("Valid:", output)

    def test_invalid_document_reports_location(self):
        result, output = self.run_validation("<count>wrong</count>")
        self.assertEqual(result, 1)
        self.assertIn("line 1", output)
        self.assertIn("wrong", output)

    def test_malformed_xml_returns_error(self):
        self.xml.write_text("<count>", encoding="utf-8")
        arguments = ["validate_netex.py", str(self.xml), "--schema", str(self.schema)]
        output = io.StringIO()
        with patch("sys.argv", arguments), contextlib.redirect_stderr(output):
            result = validate_netex.main()
        self.assertEqual(result, 2)
        self.assertIn("could not be completed", output.getvalue())


if __name__ == "__main__":
    unittest.main()