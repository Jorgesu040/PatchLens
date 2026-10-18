import unittest
from pathlib import Path

from GridriffParser import get_changes


class GridriffParserTests(unittest.TestCase):
    """Synthetic fixture tests; this data is not a Ghidriff output."""

    def setUp(self):
        self.json_file = Path("synthetic-ghidriff-report.json")
        self.report = {
            "old_meta": {
                "Program Name": "old-bin",
                "Executable SHA256": "old-sha",
                "Executable Format": "ELF",
                "Language ID": "x86:LE:64:default (4.6)",
                "Created With Ghidra Version": "12.0.4",
            },
            "new_meta": {
                "Program Name": "new-bin",
                "Executable SHA256": "new-sha",
                "Executable Format": "ELF",
                "Language ID": "x86:LE:64:default (4.6)",
                "Created With Ghidra Version": "12.0.4",
            },
            "functions": {
                "added": [
                    {
                        "name": "added_fn",
                        "address": "00101000",
                        "code": "return 1;",
                        "sig": "int added_fn(void)",
                        "called": ["callee"],
                        "calling": ["caller"],
                    }
                ],
                "deleted": [
                    {
                        "name": "deleted_fn",
                        "address": "00101010",
                        "code": "return 0;",
                        "sig": "int deleted_fn(void)",
                        "called": [],
                        "calling": [],
                    }
                ],
                "modified": [
                    {
                        "old": {
                            "name": "changed_fn",
                            "address": "00101020",
                            "code": "return 0;",
                            "sig": "int changed_fn(void)",
                            "called": ["old_callee"],
                            "calling": ["old_caller"],
                        },
                        "new": {
                            "name": "changed_fn",
                            "address": "00101030",
                            "code": "return 1;",
                            "sig": "int changed_fn(void)",
                            "called": ["new_callee"],
                            "calling": ["new_caller"],
                        },
                        "diff": "-return 0;\n+return 1;",
                        "match_types": "FullName:Param",
                        "ratio": 0.5,
                    }
                ],
            },
            "stats": {"modified_funcs_len": 1},
            "symbols": {"added": [{"name": "symbol"}], "deleted": []},
            "strings": {"added": [{"name": "new string"}], "deleted": []},
        }

    def test_normalizes_added_deleted_and_modified(self):
        result = get_changes(self.report, self.json_file)
        added = result["functions"]["added"][0]
        deleted = result["functions"]["deleted"][0]
        modified = result["functions"]["modified"][0]

        self.assertIsNone(added["old_function"])
        self.assertEqual(added["new_function"]["callees"], ["callee"])
        self.assertEqual(added["new_function"]["callers"], ["caller"])
        self.assertIsNone(deleted["new_function"])
        self.assertEqual(modified["change_details"], {
            "diff": "-return 0;\n+return 1;",
            "match_types": "FullName:Param",
        })
        self.assertEqual(
            modified["evidence"]["json_path"],
            '$["functions"]["modified"][0]',
        )

    def test_empty_function_lists_are_valid(self):
        report = dict(self.report)
        report["functions"] = {"added": [], "deleted": [], "modified": []}
        result = get_changes(report, self.json_file)
        self.assertEqual(result["functions"], {
            "added": [], "deleted": [], "modified": []
        })

    def test_missing_or_invalid_functions_section_fails(self):
        for report in ({}, {"functions": []}, {"functions": {"added": []}}):
            with self.subTest(report=report):
                with self.assertRaises(ValueError):
                    get_changes(report, self.json_file)

    def test_missing_address_or_code_is_preserved_as_null_with_warning(self):
        report = dict(self.report)
        report["functions"] = {
            "added": [{"name": "incomplete", "sig": "void incomplete(void)"}],
            "deleted": [],
            "modified": [],
        }
        result = get_changes(report, self.json_file)
        function = result["functions"]["added"][0]["new_function"]
        warnings = result["functions"]["added"][0]["warnings"]
        self.assertIsNone(function["address"])
        self.assertIsNone(function["code"])
        self.assertTrue(any("address" in warning for warning in warnings))
        self.assertTrue(any("code" in warning for warning in warnings))

    def test_removed_fields_are_not_normalized(self):
        function = get_changes(self.report, self.json_file)["functions"]["added"][0]["new_function"]
        self.assertEqual(
            set(function), {"name", "address", "code", "sig", "callees", "callers"}
        )
        self.assertNotIn("ratio", get_changes(self.report, self.json_file)["functions"]["modified"][0]["change_details"])
        self.assertEqual(get_changes(self.report, self.json_file)["metadata"]["old"]["program_name"], "old-bin")
        self.assertEqual(get_changes(self.report, self.json_file)["analysis"]["stats"], {"modified_funcs_len": 1})


if __name__ == "__main__":
    unittest.main()
