import copy
import json
import tempfile
import unittest
from pathlib import Path

from GridriffParser import get_changes, get_functions, parse_json


class GridriffParserTests(unittest.TestCase):
    """Fixtures sintéticas para el único parser; no son salidas de Ghidriff."""

    def setUp(self):
        old = {"name": "changed_fn", "address": "00101020", "code": "return 0;",
               "sig": "int changed_fn(void)", "called": ["old_callee"], "calling": ["old_caller"]}
        new = {**old, "address": "00101030", "code": "return 1;",
               "called": ["new_callee"], "calling": ["new_caller"]}
        self.report = {
            "old_meta": {"Program Name": "old-bin", "Executable SHA256": "old-sha",
                         "Executable Format": "ELF", "Language ID": "x86:LE:64",
                         "Created With Ghidra Version": "12.0.4"},
            "new_meta": {"Program Name": "new-bin", "Executable SHA256": "new-sha",
                         "Executable Format": "ELF", "Language ID": "x86:LE:64",
                         "Created With Ghidra Version": "12.0.4"},
            "functions": {
                "added": [{**new, "address": "00101000", "name": "added_fn"}],
                "deleted": [{**old, "address": "00101010", "name": "deleted_fn"}],
                "modified": [{"old": old, "new": new, "diff_type": ["code"],
                              "diff": ["-return 0;", "+return 1;"],
                              "match_types": ["FullName:Param"], "ratio": 0.5}],
            },
            "matches": {"address_matches": {"00101020": [["00101030", ["FullName:Param"]]]}},
            "stats": {"modified_funcs_len": 1},
        }

    def test_normalizes_added_deleted_and_modified(self):
        added, deleted, modified = get_changes(self.report, "SimpleDiff")
        self.assertEqual([added["type"], deleted["type"], modified["type"]],
                         ["added", "deleted", "modified"])
        self.assertIsNone(added["old_function"])
        self.assertIsNone(deleted["new_function"])
        self.assertEqual(modified["old_function"]["code"], "return 0;")
        self.assertEqual(modified["new_function"]["code"], "return 1;")
        self.assertEqual(modified["aspects"], ["code"])

    def test_preserves_provenance_and_normalizes_matching(self):
        modified = get_changes(self.report, "SimpleDiff")[2]
        self.assertEqual(modified["sources"], [{
            "analysis": "SimpleDiff", "json_path": "$.functions.modified[0]",
            "aspects": ["code"], "match_types": ["FullName:Param"],
            "diff": ["-return 0;", "+return 1;"],
        }])

    def test_preserves_original_call_relationship_names(self):
        modified = get_changes(self.report, "SimpleDiff")[2]
        self.assertEqual(modified["old_function"]["called"], ["old_callee"])
        self.assertEqual(modified["new_function"]["calling"], ["new_caller"])
        self.assertNotIn("callees", modified["new_function"])
        self.assertNotIn("callers", modified["new_function"])

    def test_output_does_not_share_mutable_values_with_input(self):
        before = copy.deepcopy(self.report)
        modified = get_changes(self.report, "SimpleDiff")[2]
        modified["new_function"]["called"].append("extra")
        modified["aspects"].append("length")
        modified["sources"][0]["diff"].append("extra")
        self.assertEqual(self.report, before)

    def test_empty_groups_are_valid(self):
        self.report["functions"] = {kind: [] for kind in ("added", "deleted", "modified")}
        self.assertEqual(get_changes(self.report, "SimpleDiff"), [])

    def test_optional_fields_can_be_absent_and_empty_code_is_kept(self):
        added = {"name": "fn", "address": "100", "code": ""}
        result = get_functions([added], "added", "SimpleDiff")[0]
        self.assertEqual(result["new_function"], added)
        self.assertEqual(result["sources"][0]["match_types"], [])

    def test_unknown_change_type_is_rejected_when_normalizing_a_record(self):
        with self.assertRaises(ValueError):
            get_functions([{"name": "fn", "address": "100", "code": ""}], "unknown", "SimpleDiff")

    def test_reads_metadata_and_reduces_function_fields(self):
        self.report["functions"]["modified"][0]["new"]["unused"] = "do not send"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(json.dumps(self.report), encoding="utf-8")
            result = parse_json(path, "SimpleDiff")
            self.assertEqual(result["analysis"]["report"], str(path.resolve()))
        self.assertEqual(result["binaries"]["old"]["sha256"], "old-sha")
        self.assertEqual(result["binaries"]["new"]["name"], "new-bin")
        self.assertEqual(result["analysis"]["stats"], self.report["stats"])
        self.assertNotIn("unused", result["changes"][2]["new_function"])


if __name__ == "__main__":
    unittest.main()
